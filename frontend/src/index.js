import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import App from './App';
import reportWebVitals from './reportWebVitals';
import * as serviceWorkerRegistration from './utils/serviceWorkerRegistration';
import { debugLog, debugError } from './utils/debugLog';

// #region agent log
try {
  debugLog('index.js:12','App entry point - checking root element',{rootExists:!!document.getElementById('root'),userAgent:navigator.userAgent,envPublicUrl:process.env.PUBLIC_URL||'undefined',envGoogleClientId:!!process.env.REACT_APP_GOOGLE_CLIENT_ID},'A');
} catch(e) {
  console.error('[DEBUG] Entry point error:', e);
}
// #endregion

// #region agent log
try {
  const hasLocalStorage = (() => { try { localStorage.setItem('test','test'); localStorage.removeItem('test'); return true; } catch(e) { return false; } })();
  debugLog('index.js:20','localStorage availability check',{hasLocalStorage,error:hasLocalStorage?'none':'localStorage unavailable'},'D');
} catch(e) {
  debugLog('index.js:22','localStorage check exception',{error:e.message,stack:e.stack},'D');
}
// #endregion

let root;
try {
  root = ReactDOM.createRoot(document.getElementById('root'));
  // #region agent log
  debugLog('index.js:28','React root created successfully',{rootCreated:!!root},'A');
  // #endregion
} catch(e) {
  // #region agent log
  debugError('index.js:31','React root creation failed',e,'A');
  // #endregion
  throw e;
}

try {
  root.render(
    <React.StrictMode>
      <App />
    </React.StrictMode>
  );
  // #region agent log
  debugLog('index.js:41','React render completed',{rendered:true},'A');
  // #endregion
} catch(e) {
  // #region agent log
  debugError('index.js:45','React render failed',e,'A');
  // #endregion
  throw e;
}

// Register service worker for PWA
// #region agent log
debugLog('index.js:50','Before service worker registration',{hasServiceWorker:'serviceWorker' in navigator,publicUrl:process.env.PUBLIC_URL||'undefined'},'B');
// #endregion
try {
  serviceWorkerRegistration.register({
    onUpdate: (registration) => {
      // New content available, notify user
      if (window.confirm('New version available! Reload to update?')) {
        registration.waiting?.postMessage({ type: 'SKIP_WAITING' });
        window.location.reload();
      }
    },
    onSuccess: () => {
      console.log('PWA: Content cached for offline use');
      // #region agent log
      debugLog('index.js:62','Service worker registered successfully',{success:true},'B');
      // #endregion
    },
  });
  // #region agent log
  debugLog('index.js:66','Service worker registration call completed',{callCompleted:true},'B');
  // #endregion
} catch(e) {
  // #region agent log
  debugError('index.js:69','Service worker registration exception',e,'B');
  // #endregion
}

// Global error handlers
// #region agent log
window.addEventListener('error', (e) => {
  debugLog('index.js:75','Global error caught',{message:e.message,filename:e.filename,lineno:e.lineno,colno:e.colno,error:e.error?.stack},'A');
});
window.addEventListener('unhandledrejection', (e) => {
  debugLog('index.js:78','Unhandled promise rejection',{reason:e.reason?.message||e.reason,stack:e.reason?.stack},'E');
});
// #endregion

// If you want to start measuring performance in your app, pass a function
// to log results (for example: reportWebVitals(console.log))
// or send to an analytics endpoint. Learn more: https://bit.ly/CRA-vitals
reportWebVitals();
