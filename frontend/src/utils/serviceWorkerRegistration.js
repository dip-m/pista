// Service Worker Registration
// This is a custom implementation since create-react-app removed SW support
import { debugLog, debugError } from './debugLog';

const isLocalhost = Boolean(
  window.location.hostname === 'localhost' ||
    window.location.hostname === '[::1]' ||
    window.location.hostname.match(/^127(?:\.(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)){3}$/)
);

export function register(config) {
  // #region agent log
  debugLog('serviceWorkerRegistration.js:12','register function entry',{hasServiceWorker:'serviceWorker' in navigator,publicUrl:process.env.PUBLIC_URL||'undefined',windowLocation:window.location.href},'B');
  // #endregion
  if ('serviceWorker' in navigator) {
    try {
      const publicUrl = new URL(process.env.PUBLIC_URL || '', window.location.href);
      // #region agent log
      debugLog('serviceWorkerRegistration.js:17','publicUrl created',{publicUrlOrigin:publicUrl.origin,windowOrigin:window.location.origin,originsMatch:publicUrl.origin===window.location.origin},'B');
      // #endregion
      if (publicUrl.origin !== window.location.origin) {
        // Service worker won't work if PUBLIC_URL is on a different origin
        // #region agent log
        debugLog('serviceWorkerRegistration.js:21','Service worker skipped - origin mismatch',{},'B');
        // #endregion
        return;
      }
    } catch(e) {
      // #region agent log
      debugError('serviceWorkerRegistration.js:25','publicUrl creation error',e,'B');
      // #endregion
      return;
    }

    window.addEventListener('load', () => {
      // #region agent log
      debugLog('serviceWorkerRegistration.js:30','Window load event fired',{isLocalhost},'B');
      // #endregion
      const swUrl = `${process.env.PUBLIC_URL || ''}/service-worker.js`;
      // #region agent log
      debugLog('serviceWorkerRegistration.js:33','Service worker URL constructed',{swUrl},'B');
      // #endregion

      if (isLocalhost) {
        // Running on localhost - check if service worker still exists
        checkValidServiceWorker(swUrl, config);
      } else {
        // Not localhost - register service worker
        registerValidSW(swUrl, config);
      }
    });
  } else {
    // #region agent log
    debugLog('serviceWorkerRegistration.js:45','Service worker not supported',{},'B');
    // #endregion
  }
}

function registerValidSW(swUrl, config) {
  // #region agent log
  debugLog('serviceWorkerRegistration.js:50','registerValidSW called',{swUrl},'B');
  // #endregion
  navigator.serviceWorker
    .register(swUrl)
    .then((registration) => {
      // #region agent log
      debugLog('serviceWorkerRegistration.js:54','Service worker registration promise resolved',{hasRegistration:!!registration},'B');
      // #endregion
      registration.onupdatefound = () => {
        const installingWorker = registration.installing;
        if (installingWorker == null) {
          return;
        }
        installingWorker.onstatechange = () => {
          if (installingWorker.state === 'installed') {
            if (navigator.serviceWorker.controller) {
              // New content available, notify user
              if (config && config.onUpdate) {
                config.onUpdate(registration);
              }
            } else {
              // Content cached for offline use
              if (config && config.onSuccess) {
                config.onSuccess(registration);
              }
            }
          }
        };
      };
    })
    .catch((error) => {
      console.error('Error during service worker registration:', error);
      // #region agent log
      debugError('serviceWorkerRegistration.js:78','Service worker registration error',error,'B');
      // #endregion
    });
}

function checkValidServiceWorker(swUrl, config) {
  fetch(swUrl, {
    headers: { 'Service-Worker': 'script' },
  })
    .then((response) => {
      const contentType = response.headers.get('content-type');
      if (
        response.status === 404 ||
        (contentType != null && contentType.indexOf('javascript') === -1)
      ) {
        // No service worker found
        navigator.serviceWorker.ready.then((registration) => {
          registration.unregister().then(() => {
            window.location.reload();
          });
        });
      } else {
        // Service worker found, proceed with registration
        registerValidSW(swUrl, config);
      }
    })
    .catch(() => {
      console.log('No internet connection found. App is running in offline mode.');
    });
}

export function unregister() {
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.ready
      .then((registration) => {
        registration.unregister();
      })
      .catch((error) => {
        console.error(error.message);
      });
  }
}
