console.log('This is the  console')

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
  const dropdown = scope.querySelector('.dropdown');
  if(!dropdown) return;
  const toggle = dropdown.querySelector('.dropdown-toggle');
  const menu = dropdown.querySelector('.dropdown-menu');
  if(!toggle || !menu) return;

  // Ensure closed initially
  dropdown.classList.remove('open');
  toggle.setAttribute('aria-expanded','false');

  function close(){
    dropdown.classList.remove('open');
    toggle.setAttribute('aria-expanded','false');
  }
  function open(){
    dropdown.classList.add('open');
    toggle.setAttribute('aria-expanded','true');
  }
  function toggleMenu(e){
    e.preventDefault();
    dropdown.classList.contains('open') ? close() : open();
  }

  toggle.addEventListener('click', toggleMenu);

  // Close on outside click
  document.addEventListener('click', (e)=>{
    if(!dropdown.contains(e.target)) close();
  });
  // Close on Escape
  document.addEventListener('keydown', (e)=>{
    if(e.key === 'Escape') close();
  });
}

// Initial page load
window.addEventListener('DOMContentLoaded', () => {
	applyAuthPlaceholders(document);
  initDropdowns(document);
});

// Handle HTMX navigations (hx-boost) where content is swapped dynamically
// Fires for newly swapped-in content
document.body.addEventListener('htmx:load', (evt) => {
	applyAuthPlaceholders(evt.target);
  initDropdowns(evt.target);
});
// Fallback: after any swap completes
document.body.addEventListener('htmx:afterSwap', (evt) => {
	applyAuthPlaceholders(evt.target);
  initDropdowns(evt.target);
});