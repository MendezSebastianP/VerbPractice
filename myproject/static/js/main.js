console.log('This is the  console')

// Toggle popovers for help buttons on register/login forms
	window.addEventListener('DOMContentLoaded', () => {
	// Add placeholders to built-in auth form fields without creating a custom form
	const username = document.getElementById('id_username');
	const pw1 = document.getElementById('id_password1');
	const pw2 = document.getElementById('id_password2');
	const pw = document.getElementById('id_password');
	if (username) username.setAttribute('placeholder', 'Username');
	if (pw1) pw1.setAttribute('placeholder', 'Password');
	if (pw2) pw2.setAttribute('placeholder', 'Confirm Password');
	if (pw) pw.setAttribute('placeholder', 'Password');
});