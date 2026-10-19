// Buttons marked data-print open the browser's print dialog. A static file,
// because the admin's content security policy allows no inline scripts.
document.addEventListener('click', (event) => {
  const button = event.target.closest('[data-print]')
  if (button) window.print()
})
