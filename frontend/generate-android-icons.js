const sharp = require('sharp');
const fs = require('fs');
const path = require('path');

// Android launcher icon sizes for different densities
const iconSizes = {
  'mipmap-mdpi': 48,
  'mipmap-hdpi': 72,
  'mipmap-xhdpi': 96,
  'mipmap-xxhdpi': 144,
  'mipmap-xxxhdpi': 192
};

const sourceIcon = path.join(__dirname, 'build', 'logo512.png');
const androidResDir = path.join(__dirname, 'android', 'app', 'src', 'main', 'res');

async function generateIcons() {
  if (!fs.existsSync(sourceIcon)) {
    console.error(`Source icon not found: ${sourceIcon}`);
    process.exit(1);
  }

  console.log('Generating Android launcher icons from logo512.png...\n');

  for (const [mipmapDir, size] of Object.entries(iconSizes)) {
    const targetDir = path.join(androidResDir, mipmapDir);

    // Create directory if it doesn't exist
    if (!fs.existsSync(targetDir)) {
      fs.mkdirSync(targetDir, { recursive: true });
    }

    // Generate square icon
    const squareIconPath = path.join(targetDir, 'ic_launcher.png');
    await sharp(sourceIcon)
      .resize(size, size, {
        fit: 'contain',
        background: { r: 255, g: 255, b: 255, alpha: 0 }
      })
      .png()
      .toFile(squareIconPath);
    console.log(`✓ Generated ${mipmapDir}/ic_launcher.png (${size}x${size})`);

    // Generate round icon (same as square for now, or you can add rounding)
    const roundIconPath = path.join(targetDir, 'ic_launcher_round.png');
    await sharp(sourceIcon)
      .resize(size, size, {
        fit: 'contain',
        background: { r: 255, g: 255, b: 255, alpha: 0 }
      })
      .png()
      .toFile(roundIconPath);
    console.log(`✓ Generated ${mipmapDir}/ic_launcher_round.png (${size}x${size})`);
  }

  console.log('\n✅ All Android launcher icons generated successfully!');
  console.log('Icons are located in: android/app/src/main/res/mipmap-*/');
}

generateIcons().catch(err => {
  console.error('Error generating icons:', err);
  process.exit(1);
});
