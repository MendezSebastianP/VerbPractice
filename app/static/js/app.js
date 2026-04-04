function getCsrfToken() {
  const meta = document.querySelector('meta[name="csrf-token"]');
  return meta ? meta.getAttribute('content') : '';
}

function focusPrimaryInput(root = document) {
  const field = root.querySelector('[data-autofocus]');
  if (field) {
    field.focus();
  }
}

function removeChatEmptyState() {
  const empty = document.getElementById('chat-empty');
  if (empty) {
    empty.remove();
  }
}

function closestPanelRoot(element) {
  if (!element || !element.closest) {
    return null;
  }
  return element.closest('.training-stage, .chat-single, .admin-monitor-shell');
}

function setPanelLoadingState(element, isLoading) {
  const root = closestPanelRoot(element);
  if (root) {
    root.classList.toggle('is-loading', isLoading);
  }
}

document.addEventListener('DOMContentLoaded', () => {
  focusPrimaryInput();
});

document.body.addEventListener('htmx:beforeRequest', (event) => {
  setPanelLoadingState(event.detail?.elt || event.target, true);
});

document.body.addEventListener('htmx:afterRequest', (event) => {
  setPanelLoadingState(event.detail?.elt || event.target, false);
});

document.body.addEventListener('htmx:responseError', (event) => {
  setPanelLoadingState(event.detail?.elt || event.target, false);
});

document.body.addEventListener('htmx:sendError', (event) => {
  setPanelLoadingState(event.detail?.elt || event.target, false);
});

document.body.addEventListener('htmx:afterSwap', (event) => {
  setPanelLoadingState(event.detail?.elt || event.target, false);
  focusPrimaryInput(event.detail?.target || document);
});

window.themeSwitcher = function themeSwitcher() {
  return {
    current: 'light',
    init() {
      const saved = localStorage.getItem('theme');
      const docTheme = document.documentElement.getAttribute('data-theme') || 'light';
      if (saved) {
        this.current = saved;
      } else if (
        docTheme === 'light' &&
        window.matchMedia &&
        window.matchMedia('(prefers-color-scheme: dark)').matches
      ) {
        this.current = 'dark';
      } else {
        this.current = docTheme;
      }
      this.apply(this.current, false);
    },
    set(theme) {
      this.current = theme;
      this.apply(theme, true);
    },
    apply(theme, persist) {
      document.documentElement.setAttribute('data-theme', theme);
      if (!persist) {
        return;
      }

      localStorage.setItem('theme', theme);
      const csrfToken = getCsrfToken();
      if (!csrfToken) {
        return;
      }

      const body = new URLSearchParams();
      body.append('theme', theme);
      body.append('csrf_token', csrfToken);
      fetch('/preferences/theme', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: body.toString(),
      }).catch(() => {});
    },
  };
};

window.conjugationSetup = function conjugationSetup() {
  return {
    languages: [],
    language: 'FR',
    level: 'easy',
    selectedTenses: [],
    visibleTenses: [],
    init(rawLanguages) {
      this.languages = rawLanguages || [];
      if (this.languages.length > 0) {
        this.language = this.languages[0].code;
      }
      this.syncTenses();
    },
    syncTenses() {
      const current = this.languages.find((lang) => lang.code === this.language);
      if (!current) {
        this.visibleTenses = [];
        this.selectedTenses = [];
        return;
      }

      const tiers = current.difficulty_tiers || {};
      const easy = tiers.easy || [];
      const medium = tiers.medium || [];
      const hard = tiers.hard || [];

      if (this.level === 'easy') {
        this.visibleTenses = easy;
        this.selectedTenses = [...easy];
      } else if (this.level === 'medium') {
        this.visibleTenses = [...easy, ...medium];
        this.selectedTenses = [...easy, ...medium];
      } else if (this.level === 'hard') {
        this.visibleTenses = [...easy, ...medium, ...hard];
        this.selectedTenses = [...easy, ...medium, ...hard];
      } else {
        this.visibleTenses = [...easy, ...medium, ...hard];
        this.selectedTenses = this.selectedTenses.filter((tense) => this.visibleTenses.includes(tense));
      }
    },
  };
};

window.chatClient = function chatClient() {
  return {
    message: '',
    isSending: false,
    fillPrompt(prompt) {
      this.message = prompt;
    },
    send() {
      const content = this.message.trim();
      if (!content || this.isSending) {
        return;
      }

      this.addBubble(content, 'user');
      this.message = '';
      this.isSending = true;

      const assistantBody = this.addBubble('', 'assistant');
      const body = new URLSearchParams();
      body.append('message', content);
      body.append('csrf_token', getCsrfToken());

      fetch('/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: body.toString(),
      })
        .then((response) => {
          if (!response.ok || !response.body) {
            throw new Error('No stream body');
          }

          const reader = response.body.getReader();
          const decoder = new TextDecoder();
          let buffer = '';

          const pump = () =>
            reader.read().then(({ done, value }) => {
              if (done) {
                this.isSending = false;
                return;
              }

              buffer += decoder.decode(value, { stream: true });
              const events = buffer.split('\n\n');
              buffer = events.pop() || '';

              events.forEach((eventBlock) => {
                const lines = eventBlock.split('\n');
                lines.forEach((line) => {
                  if (line.startsWith('event: done')) {
                    this.isSending = false;
                  }
                  if (!line.startsWith('data: ')) {
                    return;
                  }
                  const payload = line.slice(6);
                  if (payload === '[DONE]') {
                    this.isSending = false;
                    return;
                  }

                  try {
                    const parsed = JSON.parse(payload);
                    assistantBody.textContent += parsed.chunk || '';
                  } catch {
                    assistantBody.textContent += payload;
                  }
                });
              });

              this.scrollToEnd();
              return pump();
            });

          return pump();
        })
        .catch(() => {
          assistantBody.textContent = 'Streaming failed. Please try again.';
          this.isSending = false;
        });
    },
    addBubble(text, role) {
      removeChatEmptyState();
      const log = document.getElementById('chat-log');
      const article = document.createElement('article');
      article.className = `chat-bubble ${role}`;

      const badge = document.createElement('span');
      badge.className = 'bubble-role';
      badge.textContent = role === 'user' ? 'You' : 'Tutor';

      const body = document.createElement('p');
      body.className = 'bubble-body';
      body.textContent = text;

      article.appendChild(badge);
      article.appendChild(body);
      log.appendChild(article);
      this.scrollToEnd();
      return body;
    },
    scrollToEnd() {
      const log = document.getElementById('chat-log');
      if (log) {
        log.scrollTop = log.scrollHeight;
      }
    },
  };
};
