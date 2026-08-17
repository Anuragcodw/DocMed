// Firebase Cloud Messaging Service Worker for DocMed Doctor Appointment System
// Serves background push notifications and handles notification clicks.

importScripts('https://www.gstatic.com/firebasejs/9.23.0/firebase-app-compat.js');
importScripts('https://www.gstatic.com/firebasejs/9.23.0/firebase-messaging-compat.js');

// Read configuration parameters passed from query string if available
const urlParams = new URLSearchParams(self.location.search);
const apiKey = urlParams.get('apiKey') || "AIzaSy_DOCMED_DEFAULT_KEY";
const projectId = urlParams.get('projectId') || "docmed-app";
const messagingSenderId = urlParams.get('messagingSenderId') || "1234567890";
const appId = urlParams.get('appId') || "1:1234567890:web:abcdef";

firebase.initializeApp({
  apiKey: apiKey,
  projectId: projectId,
  messagingSenderId: messagingSenderId,
  appId: appId
});

const messaging = firebase.messaging();

// Handle background notifications
messaging.onBackgroundMessage(function(payload) {
  console.log('[firebase-messaging-sw.js] Received background push message:', payload);

  const title = (payload.notification && payload.notification.title) || (payload.data && payload.data.title) || 'DocMed Notification';
  const options = {
    body: (payload.notification && payload.notification.body) || (payload.data && payload.data.body) || '',
    icon: (payload.notification && payload.notification.icon) || '/static/img/logo.png',
    badge: '/static/img/badge.png',
    data: payload.data || {},
    actions: [
      { action: 'view', title: 'Open DocMed' }
    ]
  };

  return self.registration.showNotification(title, options);
});

// Route user to relevant DocMed page on notification click
self.addEventListener('notificationclick', function(event) {
  event.notification.close();
  var clickUrl = '/patient/dashboard/';
  
  if (event.notification.data) {
    var data = event.notification.data;
    if (data.link) {
      clickUrl = data.link;
    } else if (data.type === 'payment_received' || data.type === 'new_booking') {
      clickUrl = '/doctor/dashboard/';
    } else if (data.booking_id) {
      clickUrl = '/patient/bookings/';
    }
  }

  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then(function(clientList) {
      for (var i = 0; i < clientList.length; i++) {
        var client = clientList[i];
        if (client.url.includes(clickUrl) && 'focus' in client) {
          return client.focus();
        }
      }
      if (clients.openWindow) {
        return clients.openWindow(clickUrl);
      }
    })
  );
});
