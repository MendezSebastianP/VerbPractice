console.log('This is the  console')

// Chat helpers (single_chat): Shift+Enter inserts newline and auto-scroll message list
function pasteIntoInput(el, text) {
  if (!el) return;
  const start = el.selectionStart ?? el.value.length;
  const end = el.selectionEnd ?? el.value.length;
  const before = el.value.slice(0, start);
  const after = el.value.slice(end);
  el.value = before + text + after;
  const pos = start + text.length;
  if (typeof el.setSelectionRange === 'function') {
    el.setSelectionRange(pos, pos);
  }
  el.dispatchEvent(new Event('input', { bubbles: true }));
}

function handleEnter(evt) {
  if (evt.key === 'Enter' || evt.keyCode === 13) {
    const field = evt.target;
    const form = field.closest('form');
    if (evt.shiftKey) {
      // Shift+Enter -> newline, do not submit
      evt.preventDefault();
      pasteIntoInput(field, '\n');
    } else {
      // Enter -> submit form (htmx will send over WS)
      evt.preventDefault();
      if (form && typeof form.requestSubmit === 'function') {
        form.requestSubmit();
      } else if (form) {
        form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
      }
    }
  }
}

function autoSizeTextarea(el){
  if (!el || el.tagName !== 'TEXTAREA') return;
  const styles = window.getComputedStyle(el);
  const lineHeight = parseFloat(styles.lineHeight) || 20; // px
  const paddingTop = parseFloat(styles.paddingTop) || 0;
  const paddingBottom = parseFloat(styles.paddingBottom) || 0;
  const minLines = 1;
  const maxLines = 3;
  const minHeight = Math.round(lineHeight * minLines + paddingTop + paddingBottom);
  const maxHeight = Math.round(lineHeight * maxLines + paddingTop + paddingBottom);

  // Measure target height using auto to get true content height
  const prevHeight = el.offsetHeight;              // current rendered px height
  const prevStyleHeight = el.style.height;         // remember inline value
  el.style.height = 'auto';                        // let it expand to measure
  const contentHeight = el.scrollHeight;           // includes padding
  const targetHeight = Math.max(minHeight, Math.min(contentHeight, maxHeight));

  // Revert to previous height to create a pixel -> pixel transition
  el.style.height = prevHeight + 'px';
  // Force reflow so the browser acknowledges the starting height
  void el.offsetHeight;
  // Now set to the target height -> triggers transition
  el.style.height = targetHeight + 'px';

  // Toggle overflow only when exceeding max
  el.style.overflowY = contentHeight > maxHeight ? 'auto' : 'hidden';
}

function initChatInput(root) {
  const scope = root || document;
  const form = scope.querySelector('#chat-input-bar');
  if (!form) return;
  const field = form.querySelector('textarea[name="message"], input[name="message"]');
  if (!field) return;
  if (field.dataset.enterHandlerAttached === 'true') return;
  field.addEventListener('keydown', handleEnter);
  // Auto-size textarea to content (1..3 lines with animation)
  if (field.tagName === 'TEXTAREA') {
    field.addEventListener('input', () => autoSizeTextarea(field));
    // initialize size once after render
    setTimeout(() => autoSizeTextarea(field), 0);
  }
  field.dataset.enterHandlerAttached = 'true';
}

function scrollMessagesToBottom() {
  const messageList = document.getElementById('message-list');
  if (!messageList) return;
  messageList.scrollTop = messageList.scrollHeight;
}

// Helper: set placeholders on auth forms (register/login)
function applyAuthPlaceholders(root) {
	const scope = root || document;
	const username = scope.querySelector('#id_username') || document.getElementById('id_username');
	const pw1 = scope.querySelector('#id_password1') || document.getElementById('id_password1');
	const pw2 = scope.querySelector('#id_password2') || document.getElementById('id_password2');
	const pw = scope.querySelector('#id_password') || document.getElementById('id_password');
	if (username && !username.getAttribute('placeholder')) username.setAttribute('placeholder', 'Username');
	if (pw1 && !pw1.getAttribute('placeholder')) pw1.setAttribute('placeholder', 'Password');
	if (pw2 && !pw2.getAttribute('placeholder')) pw2.setAttribute('placeholder', 'Confirm Password');
	if (pw && !pw.getAttribute('placeholder')) pw.setAttribute('placeholder', 'Password');
}

function initDropdowns(root){
  const scope = root || document;
  const dropdowns = scope.querySelectorAll('.dropdown');
  
  dropdowns.forEach(dropdown => {
    const toggle = dropdown.querySelector('.dropdown-toggle');
    const menu = dropdown.querySelector('.dropdown-menu');
    if(!toggle || !menu) return;

    // Remove any existing event listeners
    const newToggle = toggle.cloneNode(true);
    toggle.parentNode.replaceChild(newToggle, toggle);

    // Ensure closed initially
    dropdown.classList.remove('open');
    newToggle.setAttribute('aria-expanded','false');

    function close(){
      dropdown.classList.remove('open');
      newToggle.setAttribute('aria-expanded','false');
    }
    function open(){
      dropdown.classList.add('open');
      newToggle.setAttribute('aria-expanded','true');
    }
    function toggleMenu(e){
      e.preventDefault();
      e.stopPropagation();
      dropdown.classList.contains('open') ? close() : open();
    }

    newToggle.addEventListener('click', toggleMenu);

    // Close on outside click
    document.addEventListener('click', (e)=>{
      if(!dropdown.contains(e.target)) close();
    });
    // Close on Escape
    document.addEventListener('keydown', (e)=>{
      if(e.key === 'Escape') close();
    });
  });
}

// Initial page load
window.addEventListener('DOMContentLoaded', () => {
	applyAuthPlaceholders(document);
  initDropdowns(document);
  initChatInput(document);
  scrollMessagesToBottom();
});

// Handle HTMX navigations (hx-boost) where content is swapped dynamically
// Fires for newly swapped-in content
document.body.addEventListener('htmx:load', (evt) => {
	applyAuthPlaceholders(evt.target);
  initDropdowns(evt.target);
  initChatInput(evt.target);
});
// Fallback: after any swap completes
document.body.addEventListener('htmx:afterSwap', (evt) => {
	applyAuthPlaceholders(evt.target);
  initDropdowns(evt.target);
  initChatInput(evt.target);
});

// Scroll to bottom after each WebSocket message (from htmx ws extension)
document.body.addEventListener('htmx:wsAfterMessage', () => {
  scrollMessagesToBottom();
});

// === VERB CONJUGATION FUNCTIONS ===
let verbConjugationData = {
    availableTenses: {},
    currentLevel: 'easy',
    initialized: false
};

function initVerbConjugation() {
    const sessionForm = document.getElementById('sessionForm');
    if (!sessionForm) {
        // Not on conjugation page, reset initialization flag
        verbConjugationData.initialized = false;
        return;
    }
    
    // Prevent multiple initializations on the same page
    if (verbConjugationData.initialized) return;
    verbConjugationData.initialized = true;
    
    loadTenses('fr'); // Load French tenses by default
    selectLevel('easy'); // Select easy by default
    
    // Remove existing event listeners to prevent duplicates
    const languageRadios = document.querySelectorAll('input[name="language"]');
    const difficultyRadios = document.querySelectorAll('input[name="difficulty_level"]');
    
    // Language change handler
    languageRadios.forEach(radio => {
        radio.removeEventListener('change', handleLanguageChange);
        radio.addEventListener('change', handleLanguageChange);
    });
    
    // Level radio button handlers
    difficultyRadios.forEach(radio => {
        radio.removeEventListener('change', handleDifficultyChange);
        radio.addEventListener('change', handleDifficultyChange);
    });
    
    // Form validation before submit
    sessionForm.removeEventListener('submit', handleFormSubmit);
    sessionForm.addEventListener('submit', handleFormSubmit);
}

function handleLanguageChange() {
    loadTenses(this.value);
    selectLevel(verbConjugationData.currentLevel);
}

function handleDifficultyChange() {
    if (this.checked) {
        const level = this.dataset.level;
        selectLevel(level);
    }
}

function handleFormSubmit(e) {
    const checkedTenses = document.querySelectorAll('input[name="selected_tenses"]:checked');
    if (checkedTenses.length === 0) {
        e.preventDefault();
        alert('Please select at least one tense to practice.');
        return false;
    }
}

function loadTenses(language) {
    const tensesUrl = document.querySelector('[data-tenses-url]')?.dataset.tensesUrl;
    if (!tensesUrl) return;
    
    fetch(`${tensesUrl}?language=${language}`)
        .then(response => response.json())
        .then(data => {
            verbConjugationData.availableTenses = data.tenses;
            renderTenseTable();
            if (verbConjugationData.currentLevel) {
                selectLevel(verbConjugationData.currentLevel);
            }
        })
        .catch(error => {
            console.error('Error loading tenses:', error);
        });
}

function renderTenseTable() {
    const tableContainer = document.getElementById('tenseCheckboxes');
    if (!tableContainer) return;
    
    tableContainer.innerHTML = '<table><tbody id="tense-table-body"></tbody></table>';
    const tableBody = document.getElementById('tense-table-body');

    const difficultyLevels = {
        'easy': { tenses: [], color: '#22c55e' },
        'medium': { tenses: [], color: '#eab308' },
        'hard': { tenses: [], color: '#ef4444' },
        'extreme': { tenses: [], color: '#000000' }
    };

    Object.keys(verbConjugationData.availableTenses).forEach(difficulty => {
        if (difficultyLevels[difficulty]) {
            difficultyLevels[difficulty].tenses = verbConjugationData.availableTenses[difficulty];
        }
    });

    Object.keys(difficultyLevels).forEach(level => {
        const levelData = difficultyLevels[level];
        
        if (levelData.tenses && levelData.tenses.length > 0) {
            levelData.tenses.forEach(tense => {
                const row = tableBody.insertRow();
                row.className = 'tense-checkbox-item';
                row.style.borderLeftColor = levelData.color;
                
                row.innerHTML = `
                    <label class="tense-checkbox-label">
                        <input type="checkbox" name="selected_tenses" value="${tense}" class="tense-checkbox" onchange="handleManualTenseSelection()">
                        <span class="tense-name">${tense}</span>
                    </label>
                `;
            });
        }
    });
}

function selectLevel(level) {
    verbConjugationData.currentLevel = level;
    
    const levelRadio = document.querySelector(`input[name="difficulty_level"][value="${level}"]`);
    if (levelRadio) {
        levelRadio.checked = true;
    }
    
    const checkboxes = document.querySelectorAll('input[name="selected_tenses"]');
    checkboxes.forEach(checkbox => {
        const tense = checkbox.value;
        let shouldCheck = false;
        
        if (level === 'easy') {
            shouldCheck = verbConjugationData.availableTenses.easy && verbConjugationData.availableTenses.easy.includes(tense);
        } else if (level === 'medium') {
            shouldCheck = (verbConjugationData.availableTenses.easy && verbConjugationData.availableTenses.easy.includes(tense)) ||
                         (verbConjugationData.availableTenses.medium && verbConjugationData.availableTenses.medium.includes(tense));
        } else if (level === 'hard') {
            shouldCheck = (verbConjugationData.availableTenses.easy && verbConjugationData.availableTenses.easy.includes(tense)) ||
                         (verbConjugationData.availableTenses.medium && verbConjugationData.availableTenses.medium.includes(tense)) ||
                         (verbConjugationData.availableTenses.hard && verbConjugationData.availableTenses.hard.includes(tense));
        }
        
        checkbox.checked = shouldCheck;
    });
    
    updateConjugationLevelInput(level);
}

function handleManualTenseSelection() {
    const checkedTenses = Array.from(document.querySelectorAll('input[name="selected_tenses"]:checked'))
                              .map(cb => cb.value);
    
    const easyTenses = verbConjugationData.availableTenses.easy || [];
    const mediumTenses = [...easyTenses, ...(verbConjugationData.availableTenses.medium || [])];
    const hardTenses = [...mediumTenses, ...(verbConjugationData.availableTenses.hard || [])];
    
    if (arraysEqual(checkedTenses.sort(), easyTenses.slice().sort())) {
        verbConjugationData.currentLevel = 'easy';
    } else if (arraysEqual(checkedTenses.sort(), mediumTenses.slice().sort())) {
        verbConjugationData.currentLevel = 'medium';
    } else if (arraysEqual(checkedTenses.sort(), hardTenses.slice().sort())) {
        verbConjugationData.currentLevel = 'hard';
    } else {
        verbConjugationData.currentLevel = 'custom';
    }
    
    if (verbConjugationData.currentLevel !== 'custom') {
        const levelRadio = document.querySelector(`input[name="difficulty_level"][value="${verbConjugationData.currentLevel}"]`);
        if (levelRadio) {
            levelRadio.checked = true;
        }
    } else {
        document.querySelectorAll('input[name="difficulty_level"]').forEach(radio => {
            radio.checked = false;
        });
    }
    
    updateConjugationLevelInput(verbConjugationData.currentLevel);
}

function updateConjugationLevelInput(level) {
    const existingInput = document.getElementById('conjugation_level_input');
    if (existingInput) {
        existingInput.remove();
    }
    
    const hiddenInput = document.createElement('input');
    hiddenInput.type = 'hidden';
    hiddenInput.name = 'conjugation_level';
    hiddenInput.value = level;
    hiddenInput.id = 'conjugation_level_input';
    
    const form = document.getElementById('sessionForm');
    if (form) {
        form.appendChild(hiddenInput);
    }
}

function arraysEqual(a, b) {
    if (a.length !== b.length) return false;
    return a.every((val, index) => val === b[index]);
}

// Initialize verb conjugation when page loads
document.addEventListener('DOMContentLoaded', function() {
    initVerbConjugation();
});

// Also initialize when navigating to the page (for SPA-like behavior)
document.body.addEventListener('htmx:afterSettle', function() {
    initVerbConjugation();
});

// Fallback: initialize immediately if DOM is already ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initVerbConjugation);
} else {
    initVerbConjugation();
}