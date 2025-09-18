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