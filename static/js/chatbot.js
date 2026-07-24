/**
 * chatbot.js — DocMed AI Chat Widget
 *
 * Guaranteed DOM-ready initialization, smooth toggle opening/closing,
 * CSRF-authenticated fetch API calls, client-side fallback engine for guest visitors,
 * markdown rendering, session history, auto-scroll, and error retry support.
 */

(function () {
  'use strict';

  var CHAT_API_URL = '/api/ai/chat/';
  var ALT_API_URL  = '/api/chatbot/';
  var SESSION_KEY  = 'docmed_chat_history';
  var MAX_INPUT_LEN = 2000;

  function initChatbot() {
    var toggleBtn         = document.getElementById('aiChatToggle');
    var chatWindow        = document.getElementById('aiChatWindow');
    var closeBtn          = document.getElementById('aiChatClose');
    var sendBtn           = document.getElementById('aiChatSend');
    var voiceBtn          = document.getElementById('aiChatVoice');
    var inputField        = document.getElementById('aiChatInput');
    var messagesContainer = document.getElementById('aiChatMessages');

    if (!toggleBtn || !chatWindow || !messagesContainer) {
      console.warn('[DocMed Chatbot] Widget elements not found in DOM.');
      return;
    }

    var isOpen = false;
    var isWaiting = false;

    var metaAuth = document.querySelector('meta[name="user-authenticated"]');
    var isAuthenticated = metaAuth ? metaAuth.getAttribute('content') === 'true' : false;

    /* ── Open / Close Logic ── */
    function openChat() {
      isOpen = true;
      chatWindow.classList.add('open');
      if (inputField) inputField.focus();
    }

    function closeChat() {
      isOpen = false;
      chatWindow.classList.remove('open');
      if (recognition && isListening) recognition.stop();
    }

    toggleBtn.addEventListener('click', function (e) {
      e.preventDefault();
      e.stopPropagation();
      if (isOpen) { closeChat(); } else { openChat(); }
    });

    if (closeBtn) {
      closeBtn.addEventListener('click', function (e) {
        e.preventDefault();
        closeChat();
      });
    }

    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && isOpen) closeChat();
    });

    /* ── Session History ── */
    function loadHistory() {
      try {
        return JSON.parse(sessionStorage.getItem(SESSION_KEY) || '[]');
      } catch (e) { return []; }
    }

    function saveHistory(history) {
      try {
        sessionStorage.setItem(SESSION_KEY, JSON.stringify(history.slice(-30)));
      } catch (e) {}
    }

    (function restoreMessages() {
      var history = loadHistory();
      if (history.length === 0) return;
      var defaultMsg = messagesContainer.querySelector('.chat-msg.bot');
      var suggestBox = messagesContainer.querySelector('.suggested-questions');
      if (defaultMsg) defaultMsg.remove();
      if (suggestBox) suggestBox.remove();
      history.forEach(function (item) {
        appendBubble(item.text, item.fromBot, false);
      });
    })();

    /* ── Markdown Renderer ── */
    function renderMarkdown(text) {
      if (!text) return '';
      var escaped = text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');

      var formatted = escaped.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
      formatted = formatted.replace(/^[\s]*[•\-]\s+(.*)$/gm, '• $1');
      return formatted.replace(/\n/g, '<br>');
    }

    /* ── Message Bubble ── */
    function appendBubble(text, fromBot, persist) {
      if (!fromBot) {
        var suggest = messagesContainer.querySelector('.suggested-questions');
        if (suggest) suggest.remove();
      }

      var msgDiv = document.createElement('div');
      msgDiv.className = fromBot ? 'chat-msg bot' : 'chat-msg user';

      if (fromBot) {
        msgDiv.innerHTML = renderMarkdown(text);
      } else {
        msgDiv.textContent = text;
      }

      messagesContainer.appendChild(msgDiv);
      scrollToBottom();

      /* TTS for bot replies */
      if (fromBot && 'speechSynthesis' in window) {
        var cleanText = text.replace(/Disclaimer:[\s\S]*$/i, '').replace(/[*#_]/g, '').trim();
        if (cleanText) {
          var utterance = new SpeechSynthesisUtterance(cleanText);
          utterance.lang = /[\u0900-\u097F]/.test(text) ? 'hi-IN' : 'en-US';
          utterance.rate = 0.95;
          window.speechSynthesis.speak(utterance);
        }
      }

      if (persist !== false) {
        var history = loadHistory();
        history.push({ text: text, fromBot: fromBot });
        saveHistory(history);
      }
    }

    function scrollToBottom() {
      messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    /* ── Typing Indicator ── */
    function showTyping() {
      var typingDiv = document.createElement('div');
      typingDiv.className = 'chat-msg bot typing-indicator';
      typingDiv.id = 'chatTypingIndicator';
      typingDiv.innerHTML = '<span></span><span></span><span></span>';
      messagesContainer.appendChild(typingDiv);
      scrollToBottom();
      return typingDiv;
    }

    function hideTyping() {
      var indicator = document.getElementById('chatTypingIndicator');
      if (indicator && indicator.parentNode) indicator.parentNode.removeChild(indicator);
    }

    /* ── CSRF Helper ── */
    function getCookie(name) {
      var cookieValue = null;
      if (document.cookie && document.cookie !== '') {
        var cookies = document.cookie.split(';');
        for (var i = 0; i < cookies.length; i++) {
          var cookie = cookies[i].trim();
          if (cookie.substring(0, name.length + 1) === (name + '=')) {
            cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
            break;
          }
        }
      }
      return cookieValue;
    }

    /* ── Client-Side Rule-Based Fallback ── */
    var INTENTS = [
      {
        patterns: ['hello', 'hi', 'hey', 'greetings', 'namaste', 'good morning', 'good evening', 'good afternoon', 'नमस्ते', 'हेलो'],
        response: "Hello! 👋 Welcome to DocMed.\n\nHow can I assist you today? I can help you with:\n• Finding doctors & specialists\n• Appointment booking\n• Symptom guidance\n• Working hours & contact info\n\nDisclaimer: This information is for educational purposes and does not replace professional medical advice."
      },
      {
        patterns: ['who are you', 'your name', 'what are you', 'what is docmed', 'about you', 'तुम कौन हो'],
        response: "I'm the DocMed AI Health Assistant! 🏥\n\nDocMed is a premium healthcare portal connecting patients with top-rated specialists for:\n• Online appointment booking\n• Medical report analysis\n• AI-powered symptom checking\n• Video consultations\n\nDisclaimer: This information is for educational purposes and does not replace professional medical advice."
      },
      {
        patterns: ['book', 'appointment', 'schedule', 'visit', 'consult', 'reserve', 'अपॉइंटमेंट', 'बुकिंग'],
        response: "To book an appointment on DocMed: 📅\n\n1. Click 'Book Appointment' or go to the Doctors page\n2. Search by doctor name, specialty, or department\n3. Select an available time slot\n4. Choose your payment method\n5. Confirm your booking\n\nYou can manage all your appointments from your Patient Dashboard.\n\nDisclaimer: This information is for educational purposes and does not replace professional medical advice."
      },
      {
        patterns: ['doctor', 'specialist', 'find doctor', 'search doctor', 'डॉक्टर'],
        response: "DocMed has specialists across all major departments: 👨‍⚕️\n\n• Cardiology\n• Neurology\n• Orthopedics\n• Pediatrics\n• Dentistry\n• General Medicine\n• Surgery\n• Ophthalmology\n\nUse the search bar or 'Find Your Specialist' section to filter by specialty, location, or name.\n\nDisclaimer: This information is for educational purposes and does not replace professional medical advice."
      },
      {
        patterns: ['working hours', 'opening hours', 'open time', 'close time', 'timing', 'schedule', 'समय'],
        response: "DocMed Working Hours: 🕐\n\n• Monday – Saturday: 8:00 AM – 10:00 PM\n• Sunday: 8:00 AM – 10:00 PM\n• Holidays: Closed\n\nFor urgent care, please contact us directly at: info.docmed@gmail.com\n\nDisclaimer: This information is for educational purposes and does not replace professional medical advice."
      },
      {
        patterns: ['contact', 'email', 'phone', 'address', 'location', 'reach', 'संपर्क'],
        response: "DocMed Contact Information: 📞\n\n📍 Address: Dhaka, Bangladesh\n📧 Email: info.docmed@gmail.com\n📱 Phone: +880 1798 128...\n\n🌐 Social Media:\n• Facebook\n• Twitter\n• LinkedIn\n• Instagram\n\nDisclaimer: This information is for educational purposes and does not replace professional medical advice."
      },
      {
        patterns: ['chest pain', 'heart attack', 'chest', 'सीने में दर्द'],
        response: "⚠️ Chest Pain — Seek Emergency Help!\n\nChest pain can indicate a serious cardiac event (Angina or Heart Attack).\n\n🚨 Call emergency services (999 / 112) immediately if:\n• Pain spreads to arm, jaw, or back\n• Accompanied by breathlessness\n• Sudden and severe\n\nAvoid exertion. Stay calm.\n\nDisclaimer: This information is for educational purposes and does not replace professional medical advice."
      },
      {
        patterns: ['fever', 'temperature', 'pyrexia', 'बुखार'],
        response: "Fever Guidance: 🌡️\n\n• Stay hydrated — drink plenty of fluids\n• Rest and avoid physical strain\n• Use paracetamol/ibuprofen for relief\n• Monitor temperature regularly\n\n⚠️ Seek medical attention if:\n• Fever exceeds 103°F (39.4°C)\n• Lasts more than 3 days\n• Accompanied by rash, confusion, or stiff neck\n\nDisclaimer: This information is for educational purposes and does not replace professional medical advice."
      },
      {
        patterns: ['headache', 'migraine', 'head pain', 'सिरदर्द'],
        response: "Headache Guidance: 🤕\n\n• Rest in a quiet, dark room\n• Stay hydrated\n• Apply cold or warm compress\n• Avoid bright screens\n\n⚠️ See a doctor immediately if:\n• Sudden, severe headache (\"thunderclap\")\n• With vision changes or speech problems\n• After head injury\n\nConsult a Neurologist for recurring migraines.\n\nDisclaimer: This information is for educational purposes and does not replace professional medical advice."
      },
      {
        patterns: ['cough', 'cold', 'flu', 'sore throat', 'खांसी', 'जुकाम'],
        response: "Cold & Cough Guidance: 🤧\n\n• Drink warm fluids and honey-lemon water\n• Use throat lozenges and steam inhalation\n• Rest and avoid cold exposure\n• Gargle with warm salt water\n\n⚠️ Consult a doctor if:\n• Cough persists more than 2 weeks\n• With fever or breathing difficulty\n• Coughing up blood\n\nConsult: ENT Specialist or General Physician.\n\nDisclaimer: This information is for educational purposes and does not replace professional medical advice."
      },
      {
        patterns: ['medicine', 'medication', 'drug', 'tablet', 'pill', 'दवा', 'औषधि'],
        response: "Medicine Information Guidance: 💊\n\n• Always take medications strictly as prescribed by your doctor.\n• Check expiry dates before consumption.\n• Do not stop or alter dosages without consulting your physician.\n• Store medicines in a cool, dry place away from direct sunlight.\n\nFor prescription management, visit your Patient Dashboard.\n\nDisclaimer: This information is for educational purposes and does not replace professional medical advice."
      },
      {
        patterns: ['thank', 'thanks', 'great', 'awesome', 'perfect', 'good', 'धन्यवाद', 'शुक्रिया'],
        response: "You're welcome! 😊\n\nIs there anything else I can help you with? Feel free to ask about:\n• Symptoms or health advice\n• Finding doctors\n• Appointment booking\n• DocMed features\n\nStay healthy! 💚\n\nDisclaimer: This information is for educational purposes and does not replace professional medical advice."
      }
    ];

    function clientFallbackReply(userMessage) {
      var msg = userMessage.toLowerCase().trim();

      for (var i = 0; i < INTENTS.length; i++) {
        var intent = INTENTS[i];
        for (var j = 0; j < intent.patterns.length; j++) {
          if (msg.indexOf(intent.patterns[j]) !== -1) {
            return intent.response;
          }
        }
      }

      return "I understand you have a question. 🏥\n\nHindi / English supported:\n• 📅 Appointment booking (अपॉइंटमेंट)\n• 👨‍⚕️ Finding doctors (डॉक्टर)\n• 💊 Symptom & Medicine guidance (दवा एवं लक्षण)\n• 🕐 Working hours & contact (समय व संपर्क)\n\nFor personalized medical advice, please log in or consult a certified doctor on DocMed.\n\nDisclaimer: This information is for educational purposes and does not replace professional medical advice.";
    }

    /* ── Send Message ── */
    function sendMessage(customMsg) {
      var rawMsg = customMsg || (inputField ? inputField.value : '');
      var msg = rawMsg ? rawMsg.trim() : '';

      if (!msg || isWaiting) return;

      if (msg.length > MAX_INPUT_LEN) {
        msg = msg.substring(0, MAX_INPUT_LEN);
      }

      appendBubble(msg, false);
      if (inputField) inputField.value = '';
      isWaiting = true;

      var typingDiv = showTyping();

      if (!isAuthenticated) {
        setTimeout(function () {
          hideTyping();
          isWaiting = false;
          appendBubble(clientFallbackReply(msg), true);
        }, 500 + Math.random() * 300);
        return;
      }

      var csrftoken = getCookie('csrftoken');

      function makeApiCall(url) {
        return fetch(url, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrftoken || ''
          },
          credentials: 'same-origin',
          body: JSON.stringify({ message: msg })
        });
      }

      makeApiCall(CHAT_API_URL)
        .then(function (response) {
          if (!response.ok && response.status === 404) {
            return makeApiCall(ALT_API_URL);
          }
          return response;
        })
        .then(function (response) {
          return response.json().then(function (data) {
            if (!response.ok) {
              if (response.status === 401) {
                isAuthenticated = false;
                return { reply: clientFallbackReply(msg) };
              }
              throw new Error(data.error || 'AI service is temporarily unavailable. Please try again later.');
            }
            return data;
          });
        })
        .then(function (data) {
          hideTyping();
          isWaiting = false;
          appendBubble(data.reply || clientFallbackReply(msg), true);
        })
        .catch(function (error) {
          hideTyping();
          isWaiting = false;
          console.warn('[DocMed Chatbot] API error — using fallback:', error.message);
          appendBubble(
            'AI service is temporarily unavailable. Please try again later.\n\n' + clientFallbackReply(msg),
            true
          );
        });
    }

    /* ── Suggestion Chips ── */
    messagesContainer.addEventListener('click', function (e) {
      var chip = e.target.closest('.suggestion-chip');
      if (chip) {
        var msg = chip.getAttribute('data-msg');
        if (msg) sendMessage(msg);
      }
    });

    if (sendBtn) {
      sendBtn.addEventListener('click', function () { sendMessage(); });
    }

    if (inputField) {
      inputField.addEventListener('keydown', function (e) {
        if (e.key === 'Enter') {
          e.preventDefault();
          sendMessage();
        }
      });
    }

    /* ── Voice Input (STT) ── */
    var recognition = null;
    var isListening = false;
    var SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

    if (SpeechRecognition) {
      recognition = new SpeechRecognition();
      recognition.continuous = false;
      recognition.interimResults = false;
      recognition.lang = 'en-US';

      recognition.onstart = function () {
        isListening = true;
        if (voiceBtn) {
          voiceBtn.style.color = '#ef4444';
          voiceBtn.innerHTML = '<i class="fa fa-microphone-slash"></i>';
        }
        if (inputField) inputField.placeholder = 'Listening...';
      };

      recognition.onend = function () {
        isListening = false;
        if (voiceBtn) {
          voiceBtn.style.color = 'var(--color-primary, #4f46e5)';
          voiceBtn.innerHTML = '<i class="fa fa-microphone"></i>';
        }
        if (inputField) inputField.placeholder = 'Type your message...';
      };

      recognition.onresult = function (event) {
        var transcript = event.results[0][0].transcript;
        if (inputField) inputField.value = transcript;
        sendMessage();
      };

      recognition.onerror = function (event) {
        console.warn('[DocMed Chatbot] STT error:', event.error);
        isListening = false;
        if (voiceBtn) {
          voiceBtn.style.color = 'var(--color-primary, #4f46e5)';
          voiceBtn.innerHTML = '<i class="fa fa-microphone"></i>';
        }
      };
    }

    if (voiceBtn) {
      if (recognition) {
        voiceBtn.addEventListener('click', function () {
          if (isListening) {
            recognition.stop();
          } else {
            try { recognition.start(); } catch (e) { console.warn('STT start error:', e); }
          }
        });
      } else {
        voiceBtn.style.display = 'none';
      }
    }
  }

  /* Safely initialize once DOM is ready */
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initChatbot);
  } else {
    initChatbot();
  }

})();
