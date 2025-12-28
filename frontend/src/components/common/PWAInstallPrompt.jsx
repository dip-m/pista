import React, { useState, useEffect } from 'react';

/**
 * PWA Install Prompt Component
 * Shows install button for Android/iOS when PWA is installable
 */
function PWAInstallPrompt() {
  const [deferredPrompt, setDeferredPrompt] = useState(null);
  const [showPrompt, setShowPrompt] = useState(false);
  const [isIOS, setIsIOS] = useState(false);
  const [isStandalone, setIsStandalone] = useState(false);

  useEffect(() => {
    // Check if already installed
    const standalone = window.matchMedia('(display-mode: standalone)').matches ||
      (window.navigator.standalone) ||
      document.referrer.includes('android-app://');

    setIsStandalone(standalone);

    // Detect iOS
    const iOS = /iPad|iPhone|iPod/.test(navigator.userAgent) && !window.MSStream;
    setIsIOS(iOS);

    // Listen for beforeinstallprompt event (Android Chrome)
    const handleBeforeInstallPrompt = (e) => {
      e.preventDefault();
      setDeferredPrompt(e);
      // Show prompt after a delay (don't be too aggressive)
      const dismissed = localStorage.getItem('pwa-install-dismissed');
      if (!dismissed) {
        setTimeout(() => setShowPrompt(true), 3000);
      }
    };

    window.addEventListener('beforeinstallprompt', handleBeforeInstallPrompt);

    return () => {
      window.removeEventListener('beforeinstallprompt', handleBeforeInstallPrompt);
    };
  }, []);

  const handleInstallClick = async () => {
    if (deferredPrompt) {
      // Show the install prompt
      deferredPrompt.prompt();
      const { outcome } = await deferredPrompt.userChoice;

      if (outcome === 'accepted') {
        console.log('User accepted the install prompt');
      } else {
        console.log('User dismissed the install prompt');
      }

      setDeferredPrompt(null);
      setShowPrompt(false);
    }
  };

  const handleDismiss = () => {
    setShowPrompt(false);
    localStorage.setItem('pwa-install-dismissed', 'true');
    // Reset after 7 days
    setTimeout(() => {
      localStorage.removeItem('pwa-install-dismissed');
    }, 7 * 24 * 60 * 60 * 1000);
  };

  // Don't show if already installed or if prompt was dismissed
  if (isStandalone || !showPrompt) {
    return null;
  }

  // iOS instructions
  if (isIOS && !isStandalone) {
    return (
      <div className="pwa-install-prompt ios-prompt">
        <div className="pwa-install-content">
          <h3>Install Pista</h3>
          <p>Tap the share button <span className="ios-icon">⎋</span> and select "Add to Home Screen"</p>
          <button onClick={handleDismiss} className="pwa-dismiss-btn">
            Dismiss
          </button>
        </div>
      </div>
    );
  }

  // Android install prompt
  if (deferredPrompt && !isStandalone) {
    return (
      <div className="pwa-install-prompt">
        <div className="pwa-install-content">
          <h3>Install Pista</h3>
          <p>Install our app for a better experience</p>
          <div className="pwa-install-buttons">
            <button onClick={handleInstallClick} className="pwa-install-btn">
              Install
            </button>
            <button onClick={handleDismiss} className="pwa-dismiss-btn">
              Not Now
            </button>
          </div>
        </div>
      </div>
    );
  }

  return null;
}

export default PWAInstallPrompt;
