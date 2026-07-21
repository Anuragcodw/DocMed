// static/js/chatbot.js
// Handles opening, closing, interaction, voice STT/TTS, and AJAX for the AI chat widget.

document.addEventListener('DOMContentLoaded', function () {
  const toggleBtn = document.getElementById('aiChatToggle');
  const chatWindow = document.getElementById('aiChatWindow');
  const closeBtn = document.getElementById('aiChatClose');
  const sendBtn = document.getElementById('aiChatSend');
  const voiceBtn = document.getElementById('aiChatVoice');
  const inputField = document.getElementById('aiChatInput');
  const messagesContainer = document.getElementById('aiChatMessages');

  if (!toggleBtn || !chatWindow) return; // safety

  let recognition = null;
  let isListening = false;

  // Initialize Speech Recognition if supported
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (SpeechRecognition) {
    recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = 'en-US'; // Default to English, speech service works multi-lingual

    recognition.onstart = () => {
      isListening = true;
      if (voiceBtn) {
        voiceBtn.style.color = '#ef4444'; // Red color while listening
        voiceBtn.innerHTML = '<i class="fa fa-microphone-slash"></i>';
      }
      if (inputField) inputField.placeholder = "Listening...";
    };

    recognition.onend = () => {
      isListening = false;
      if (voiceBtn) {
        voiceBtn.style.color = 'var(--color-primary)';
        voiceBtn.innerHTML = '<i class="fa fa-microphone"></i>';
      }
      if (inputField) inputField.placeholder = "Type your message...";
    };

    recognition.onresult = (event) => {
      const speechToText = event.results[0][0].transcript;
      if (inputField) {
        inputField.value = speechToText;
        sendMessage();
      }
    };

    recognition.onerror = (event) => {
      console.error('Speech recognition error:', event.error);
    };
  }

  // Open/close functions
  const openChat = () => {
    chatWindow.classList.add('open');
    if (inputField) inputField.focus();
  };
  const closeChat = () => {
    chatWindow.classList.remove('open');
    if (recognition && isListening) recognition.stop();
  };

  toggleBtn.addEventListener('click', () => {
    if (chatWindow.classList.contains('open')) {
      closeChat();
    } else {
      openChat();
    }
  });

  if (closeBtn) closeBtn.addEventListener('click', closeChat);

  // Helper to get CSRF cookie
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

  // Helper to append a message bubble
  const appendMessage = (text, fromBot) => {
    // Remove any existing suggested-questions block from messages list
    const suggest = messagesContainer.querySelector('.suggested-questions');
    if (suggest) {
      messagesContainer.removeChild(suggest);
    }

    const msgDiv = document.createElement('div');
    msgDiv.className = fromBot ? 'chat-msg bot' : 'chat-msg user';
    msgDiv.textContent = text;
    messagesContainer.appendChild(msgDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;

    // Optional Speech Synthesis for bot replies
    if (fromBot && 'speechSynthesis' in window) {
      // Basic sanitizer to remove markdown or HTML elements
      const speechText = text.replace(/Disclaimer:.*$/i, '').replace(/[\*\#\_]/g, '');
      const utterance = new SpeechSynthesisUtterance(speechText);
      // Auto-detect language context (e.g. Hindi, English)
      if (/[\u0900-\u097F]/.test(text)) {
        utterance.lang = 'hi-IN'; // Hindi voice
      } else {
        utterance.lang = 'en-US';
      }
      window.speechSynthesis.speak(utterance);
    }
  };

  // Send handling via API
  const sendMessage = (customMsg = null) => {
    const msg = customMsg || (inputField ? inputField.value.trim() : '');
    if (!msg) return;
    
    appendMessage(msg, false);
    if (inputField) inputField.value = '';

    // Create typing indicator
    const typingDiv = document.createElement('div');
    typingDiv.className = 'chat-msg bot typing';
    typingDiv.innerHTML = '<span class="dot"></span><span class="dot"></span><span class="dot"></span>';
    messagesContainer.appendChild(typingDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;

    const csrftoken = getCookie('csrftoken');

    fetch('/api/ai/chat/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrftoken || ''
      },
      body: JSON.stringify({ message: msg })
    })
    .then(response => {
      return response.json().then(data => {
        if (!response.ok) {
          throw new Error(data.error || "An error occurred. Please log in to access the AI.");
        }
        return data;
      });
    })
    .then(data => {
      if (typingDiv.parentNode) {
        typingDiv.parentNode.removeChild(typingDiv);
      }
      appendMessage(data.reply, true);
    })
    .catch(error => {
      if (typingDiv.parentNode) {
        typingDiv.parentNode.removeChild(typingDiv);
      }
      appendMessage(error.message || "Something went wrong.", true);
    });
  };

  // Setup event listeners for suggestion chips
  messagesContainer.addEventListener('click', (e) => {
    const chip = e.target.closest('.suggestion-chip');
    if (chip) {
      const msg = chip.getAttribute('data-msg');
      if (msg) sendMessage(msg);
    }
  });

  if (sendBtn && inputField) {
    sendBtn.addEventListener('click', () => sendMessage());
    inputField.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        sendMessage();
      }
    });
  }

  // Voice button handling
  if (voiceBtn && recognition) {
    voiceBtn.addEventListener('click', () => {
      if (isListening) {
        recognition.stop();
      } else {
        recognition.start();
      }
    });
  } else if (voiceBtn) {
    voiceBtn.style.display = 'none';
  }
});
