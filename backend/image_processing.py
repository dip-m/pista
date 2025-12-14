# backend/image_processing.py
import base64
import io
from typing import Dict, Any, Optional, List
from PIL import Image
import numpy as np
from backend.logger_config import logger

# Try to import CV libraries (optional dependencies)
try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    logger.warning("OpenCV not available, using basic image processing")

try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False
    logger.warning("YOLO not available, using basic object detection")

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    logger.warning("Tesseract OCR not available, skipping text detection")

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

def analyze_image(image_data: bytes) -> Dict[str, Any]:
    """
    Analyze uploaded image using CV models (YOLO for objects, OCR for text).
    Returns analysis including:
    - Component positions and sizes
    - Card numbers/suits if detected
    - Color information
    """
    logger.info("Starting image analysis")
    
    try:
        # Load image
        image = Image.open(io.BytesIO(image_data))
        width, height = image.size
        
        # Convert to RGB if needed
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Convert to numpy array for analysis
        img_array = np.array(image)
        
        analysis = {
            "image_size": {"width": width, "height": height},
            "components": [],
            "cards": [],
            "colors": {
                "dominant": "unknown",
                "palette": []
            },
            "text": []
        }
        
        # Object detection with YOLO if available
        if YOLO_AVAILABLE:
            try:
                # Load YOLO model (you would have a trained model for board game components)
                # For now, using a general object detection model
                model = YOLO('yolov8n.pt')  # Use nano model for speed
                results = model(image)
                
                for result in results:
                    for box in result.boxes:
                        cls = int(box.cls[0])
                        conf = float(box.conf[0])
                        x1, y1, x2, y2 = box.xyxy[0].tolist()
                        
                        # Filter for relevant objects (cards, dice, tokens, etc.)
                        class_name = model.names[cls]
                        if conf > 0.5:  # Confidence threshold
                            analysis["components"].append({
                                "type": class_name,
                                "confidence": conf,
                                "position": {"x1": x1, "y1": y1, "x2": x2, "y2": y2},
                                "size": {"width": x2 - x1, "height": y2 - y1}
                            })
                            logger.debug(f"Detected {class_name} with confidence {conf:.2f}")
            except Exception as e:
                logger.warning(f"YOLO detection failed: {e}")
        
        # OCR for text/card detection if available
        if TESSERACT_AVAILABLE:
            try:
                text = pytesseract.image_to_string(image)
                if text.strip():
                    analysis["text"] = [line.strip() for line in text.split('\n') if line.strip()]
                    logger.debug(f"OCR detected {len(analysis['text'])} text lines")
            except Exception as e:
                logger.warning(f"OCR failed: {e}")
        
        # Color analysis
        if CV2_AVAILABLE:
            try:
                img_cv = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
                # K-means clustering for dominant colors
                pixels = img_cv.reshape(-1, 3)
                pixels = np.float32(pixels)
                criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1.0)
                k = 5
                _, labels, centers = cv2.kmeans(pixels, k, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS)
                centers = np.uint8(centers)
                # Get most common color
                unique, counts = np.unique(labels, return_counts=True)
                dominant_idx = unique[np.argmax(counts)]
                dominant_color = centers[dominant_idx]
                analysis["colors"]["dominant"] = f"rgb({dominant_color[2]}, {dominant_color[1]}, {dominant_color[0]})"
                analysis["colors"]["palette"] = [f"rgb({c[2]}, {c[1]}, {c[0]})" for c in centers]
            except Exception as e:
                logger.warning(f"Color analysis failed: {e}")
        else:
            # Basic color analysis
            analysis["colors"]["dominant"] = "mixed"
        
        logger.info(f"Image analysis complete: {width}x{height}, {len(analysis['components'])} components, {len(analysis['text'])} text lines")
        return analysis
        
    except Exception as e:
        logger.error(f"Error analyzing image: {e}", exc_info=True)
        raise


def generate_prompt_from_analysis(analysis: Dict[str, Any]) -> str:
    """
    Generate a prompt for image generation based on CV analysis.
    """
    logger.debug("Generating prompt from analysis")
    
    prompt_parts = []
    
    # Add component information
    if analysis.get("components"):
        prompt_parts.append("board game components")
    
    # Add card information
    if analysis.get("cards"):
        cards_info = ", ".join([f"{c.get('number', '')} of {c.get('suit', '')}" for c in analysis["cards"]])
        prompt_parts.append(f"cards: {cards_info}")
    
    # Add color information
    if analysis.get("colors", {}).get("dominant"):
        prompt_parts.append(f"dominant colors: {analysis['colors']['dominant']}")
    
    # Add text if detected
    if analysis.get("text"):
        prompt_parts.append(f"text: {', '.join(analysis['text'])}")
    
    # Base prompt
    base_prompt = "A high-quality board game image"
    
    if prompt_parts:
        full_prompt = f"{base_prompt} with {', '.join(prompt_parts)}"
    else:
        full_prompt = f"{base_prompt} with game components and cards"
    
    logger.debug(f"Generated prompt: {full_prompt}")
    return full_prompt


def generate_image(prompt: str, api_type: str = "stable_diffusion") -> bytes:
    """
    Generate an image from a prompt using image generation APIs.
    Supports:
    - Stable Diffusion (via Replicate/Stability AI)
    - DALL-E (via OpenAI)
    """
    logger.info(f"Generating image from prompt: {prompt[:50]}...")
    
    try:
        if api_type == "dalle" and REQUESTS_AVAILABLE:
            # DALL-E API integration
            import os
            openai_api_key = os.getenv("OPENAI_API_KEY")
            if openai_api_key:
                try:
                    import openai
                    client = openai.OpenAI(api_key=openai_api_key)
                    response = client.images.generate(
                        model="dall-e-3",
                        prompt=prompt,
                        size="1024x1024",
                        quality="standard",
                        n=1,
                    )
                    image_url = response.data[0].url
                    # Download image
                    img_response = requests.get(image_url, timeout=30)
                    logger.info("Image generated via DALL-E")
                    return img_response.content
                except Exception as e:
                    logger.warning(f"DALL-E generation failed: {e}, falling back to placeholder")
        
        elif api_type == "stable_diffusion" and REQUESTS_AVAILABLE:
            # Stable Diffusion via Replicate or Stability AI
            import os
            replicate_api_token = os.getenv("REPLICATE_API_TOKEN")
            stability_api_key = os.getenv("STABILITY_API_KEY")
            
            if replicate_api_token:
                try:
                    import replicate
                    output = replicate.run(
                        "stability-ai/stable-diffusion:db21e45d3f7023abc2a46ee38a23973f6dce16bb082a930b0c49861f96d1e5bf",
                        input={"prompt": prompt}
                    )
                    if output:
                        image_url = output[0] if isinstance(output, list) else output
                        img_response = requests.get(image_url, timeout=30)
                        logger.info("Image generated via Stable Diffusion (Replicate)")
                        return img_response.content
                except Exception as e:
                    logger.warning(f"Replicate generation failed: {e}")
            
            if stability_api_key:
                try:
                    response = requests.post(
                        "https://api.stability.ai/v2beta/stable-image/generate/core",
                        headers={
                            "Authorization": f"Bearer {stability_api_key}",
                            "Accept": "image/*"
                        },
                        files={"none": ""},
                        data={
                            "prompt": prompt,
                            "output_format": "png",
                        },
                        timeout=60
                    )
                    if response.status_code == 200:
                        logger.info("Image generated via Stable Diffusion (Stability AI)")
                        return response.content
                except Exception as e:
                    logger.warning(f"Stability AI generation failed: {e}")
        
        # Fallback: create placeholder image
        logger.info("Using placeholder image (no API keys configured)")
        img = Image.new('RGB', (512, 512), color='lightblue')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        return img_bytes.read()
        
    except Exception as e:
        logger.error(f"Error generating image: {e}", exc_info=True)
        raise

