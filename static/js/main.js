/* -------------------------------------------------------------
 * MAIN.JS - AOS, Page Loader, AI Chat, Toast Messages
 * ------------------------------------------------------------- */

document.addEventListener('DOMContentLoaded', function() {

  /* ---- Initialize AOS ---- */
  if (typeof AOS !== 'undefined') {
    AOS.init({ duration: 800, once: true, easing: 'ease-out-cubic' });
  }

  /* ---- Hide Page Loader ---- */
  window.addEventListener('load', function() {
    var loader = document.getElementById('pageLoader');
    if (loader) loader.classList.add('hidden');
  });

  /* ---- Toast / Alert Auto-Dismiss ---- */
  var alertContainer = document.getElementById('alertMessages');
  if (alertContainer) {
    setTimeout(function() {
      alertContainer.style.transition = 'opacity 0.5s ease';
      alertContainer.style.opacity = '0';
      setTimeout(function() { alertContainer.remove(); }, 500);
    }, 4000);
  }

  /* ---- AI Chat Widget ---- */
  var chatToggle = document.getElementById('aiChatToggle');
  var chatClose  = document.getElementById('aiChatClose');
  var chatWindow = document.getElementById('aiChatWindow');
  var chatInput  = document.getElementById('aiChatInput');
  var chatSend   = document.getElementById('aiChatSend');
  var chatMsgs   = document.getElementById('aiChatMessages');

  if (chatToggle && chatWindow) {
    chatToggle.addEventListener('click', function() {
      chatWindow.classList.toggle('open');
    });
  }
  if (chatClose && chatWindow) {
    chatClose.addEventListener('click', function() {
      chatWindow.classList.remove('open');
    });
  }

  // Suggestion chips
  document.querySelectorAll('.suggestion-chip').forEach(function(chip) {
    chip.addEventListener('click', function() {
      if (chatInput) {
        chatInput.value = chip.getAttribute('data-msg');
        sendChat();
      }
    });
  });

  // Send on Enter
  if (chatInput) {
    chatInput.addEventListener('keypress', function(e) {
      if (e.key === 'Enter') sendChat();
    });
  }
  if (chatSend) {
    chatSend.addEventListener('click', sendChat);
  }

  function sendChat() {
    var text = chatInput.value.trim();
    if (!text) return;

    appendMsg(text, 'user');
    chatInput.value = '';

    // Typing indicator
    var typingEl = document.createElement('div');
    typingEl.className = 'chat-msg bot typing-indicator';
    typingEl.innerHTML = '<span></span><span></span><span></span>';
    chatMsgs.appendChild(typingEl);
    chatMsgs.scrollTop = chatMsgs.scrollHeight;

    fetch('/api/ai/chat/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrftoken')
      },
      body: JSON.stringify({ message: text })
    })
    .then(res => res.json())
    .then(data => {
      typingEl.remove();
      if(data.reply) {
        // Strip markdown if necessary, but basic markdown is fine as text for now
        appendMsg(data.reply, 'bot');
      } else if(data.error) {
        appendMsg('Error: ' + data.error, 'bot');
      } else {
        appendMsg('Sorry, something went wrong. Are you logged in?', 'bot');
      }
    })
    .catch(err => {
      typingEl.remove();
      appendMsg('Network error. Please try again later.', 'bot');
    });
  }

  function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
  }

  function appendMsg(text, sender) {
    var el = document.createElement('div');
    el.className = 'chat-msg ' + sender;
    
    var span = document.createElement('span');
    span.textContent = text;
    el.appendChild(span);
    
    if (sender === 'bot') {
      var ttsBtn = document.createElement('button');
      ttsBtn.innerHTML = '<i class="fa fa-volume-up"></i>';
      ttsBtn.className = 'tts-btn';
      ttsBtn.style.border = 'none';
      ttsBtn.style.background = 'none';
      ttsBtn.style.color = '#fff';
      ttsBtn.style.marginLeft = '10px';
      ttsBtn.style.cursor = 'pointer';
      ttsBtn.title = "Listen";
      ttsBtn.onclick = function() {
        if('speechSynthesis' in window) {
           window.speechSynthesis.cancel();
           var utterance = new SpeechSynthesisUtterance(text);
           window.speechSynthesis.speak(utterance);
        }
      };
      el.appendChild(ttsBtn);
    }
    
    chatMsgs.appendChild(el);
    chatMsgs.scrollTop = chatMsgs.scrollHeight;
  }

  var aiChatVoice = document.getElementById('aiChatVoice');
  if (aiChatVoice && ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window)) {
      var SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      var recognition = new SpeechRecognition();
      recognition.continuous = false;
      recognition.interimResults = false;
      
      aiChatVoice.addEventListener('click', function() {
          aiChatVoice.style.color = 'red';
          recognition.start();
      });
      
      recognition.onresult = function(event) {
          aiChatVoice.style.color = 'var(--color-primary)';
          var transcript = event.results[0][0].transcript;
          if (chatInput) {
             chatInput.value = transcript;
             sendChat();
          }
      };
      
      recognition.onerror = function(event) {
          aiChatVoice.style.color = 'var(--color-primary)';
          console.error("Speech recognition error", event.error);
      };
      
      recognition.onend = function() {
          aiChatVoice.style.color = 'var(--color-primary)';
      };
  }

  /* ---- Smooth Scroll for Anchor Links ---- */
  document.querySelectorAll('a[href^="#"]').forEach(function(anchor) {
    anchor.addEventListener('click', function(e) {
      var target = document.querySelector(this.getAttribute('href'));
      if (target) {
        e.preventDefault();
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    });
  });

  /* ---- HTML5 Push Notifications ---- */
  function initBrowserNotifications() {
    if ("Notification" in window) {
      if (Notification.permission === "default") {
        Notification.requestPermission();
      }
    }
  }
  
  window.showBrowserNotification = function(title, body, iconUrl) {
    if ("Notification" in window && Notification.permission === "granted") {
      var options = {
        body: body || "",
        icon: iconUrl || "/static/img/core-img/favicon.ico",
        silent: false
      };
      try {
        new Notification(title, options);
      } catch (e) {
        console.warn("Desktop notifications failed: ", e);
      }
    }
  };

  // Auto-trigger notifications from HTML flash messages if present
  var alertMsgs = document.querySelectorAll('.alert-glass');
  if (alertMsgs.length > 0) {
    initBrowserNotifications();
    alertMsgs.forEach(function(msgEl) {
      var text = msgEl.textContent.trim();
      // Show notification after 800ms delay for better UX
      setTimeout(function() {
        window.showBrowserNotification("DocMed Portal", text);
      }, 800);
    });
  } else {
    // Lazy request permission on click or interactive action
    document.addEventListener('click', function requestHandler() {
      initBrowserNotifications();
      document.removeEventListener('click', requestHandler);
    }, { once: true });
  }

});

