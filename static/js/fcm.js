/**
 * DocMed Firebase Cloud Messaging (FCM) Web Push Client
 * 
 * Initialises Firebase Web Push, registers Service Worker at /firebase-messaging-sw.js,
 * requests browser notification permission on user action, and sends FCM registration tokens to Django.
 */

(function () {
  'use strict';

  // Read Firebase config from window global or environment variables
  var firebaseConfig = window.FIREBASE_CONFIG || {
    apiKey: "AIzaSy_DOCMED_FALLBACK",
    authDomain: "docmed-app.firebaseapp.com",
    projectId: "docmed-app",
    storageBucket: "docmed-app.appspot.com",
    messagingSenderId: "1234567890",
    appId: "1:1234567890:web:abcdef",
    vapidKey: window.FIREBASE_VAPID_KEY || ""
  };

  var messaging = null;

  function initFCM() {
    if (!('Notification' in window) || !('serviceWorker' in navigator)) {
      console.log('[FCM] Push notifications not supported in this browser environment.');
      return;
    }

    try {
      if (typeof firebase !== 'undefined' && firebase.initializeApp) {
        if (!firebase.apps.length) {
          firebase.initializeApp(firebaseConfig);
        }
        messaging = firebase.messaging();
        registerServiceWorker();
        checkExistingPermission();
      } else {
        console.warn('[FCM] Firebase JS SDK not loaded. Push notifications standing by.');
      }
    } catch (err) {
      console.error('[FCM] Error initializing Firebase:', err);
    }
  }

  function registerServiceWorker() {
    var swUrl = '/firebase-messaging-sw.js?apiKey=' + encodeURIComponent(firebaseConfig.apiKey) +
      '&projectId=' + encodeURIComponent(firebaseConfig.projectId) +
      '&messagingSenderId=' + encodeURIComponent(firebaseConfig.messagingSenderId) +
      '&appId=' + encodeURIComponent(firebaseConfig.appId);

    navigator.serviceWorker.register(swUrl)
      .then(function (registration) {
        console.log('[FCM] Service worker registered at scope:', registration.scope);
        if (messaging && typeof messaging.useServiceWorker === 'function') {
          messaging.useServiceWorker(registration);
        }
      })
      .catch(function (err) {
        console.error('[FCM] Service worker registration failed:', err);
      });
  }

  function checkExistingPermission() {
    if (Notification.permission === 'granted') {
      requestAndSendToken(false);
    } else if (Notification.permission === 'default') {
      showEnableNotificationPrompt();
    }
  }

  function showEnableNotificationPrompt() {
    var btn = document.getElementById('enableFcmNotificationsBtn');
    if (btn) {
      btn.style.display = 'inline-flex';
      btn.addEventListener('click', function () {
        requestAndSendToken(true);
      });
    }
  }

  function requestAndSendToken(userInitiated) {
    if (!messaging) return;

    Notification.requestPermission().then(function (permission) {
      if (permission === 'granted') {
        console.log('[FCM] Notification permission granted.');
        var btn = document.getElementById('enableFcmNotificationsBtn');
        if (btn) btn.style.display = 'none';

        var getTokenOptions = {};
        if (firebaseConfig.vapidKey) {
          getTokenOptions.vapidKey = firebaseConfig.vapidKey;
        }

        messaging.getToken(getTokenOptions).then(function (currentToken) {
          if (currentToken) {
            sendTokenToBackend(currentToken);
          } else {
            console.warn('[FCM] No registration token available. Request permission to generate one.');
          }
        }).catch(function (err) {
          console.error('[FCM] An error occurred while retrieving token:', err);
        });
      } else {
        console.log('[FCM] Notification permission denied.');
      }
    });
  }

  function sendTokenToBackend(fcmToken) {
    var csrfToken = getCsrfToken();
    fetch('/api/save-fcm-token/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken
      },
      credentials: 'include',
      body: JSON.stringify({
        fcm_token: fcmToken,
        device_info: navigator.userAgent
      })
    })
    .then(function (res) { return res.json(); })
    .then(function (data) {
      console.log('[FCM] Token registered with backend:', data);
    })
    .catch(function (err) {
      console.error('[FCM] Failed to send token to backend:', err);
    });
  }

  function getCsrfToken() {
    var cookie = document.cookie.split(';').find(function (c) { return c.trim().startsWith('csrftoken='); });
    return cookie ? cookie.split('=')[1].trim() : '';
  }

  // Handle incoming messages when browser tab is open in foreground
  if (typeof window !== 'undefined') {
    window.requestFcmPermission = function () {
      requestAndSendToken(true);
    };

    document.addEventListener('DOMContentLoaded', function () {
      initFCM();
    });
  }
})();
