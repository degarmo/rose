// Close the Settings menu when clicking elsewhere or pressing Escape.
(function () {
  function menus() {
    return document.querySelectorAll('details.ig-settings[open]');
  }
  document.addEventListener('click', function (event) {
    menus().forEach(function (menu) {
      if (!menu.contains(event.target)) menu.open = false;
    });
  });
  document.addEventListener('keydown', function (event) {
    if (event.key !== 'Escape') return;
    menus().forEach(function (menu) {
      menu.open = false;
      menu.querySelector('summary').focus();
    });
  });
})();
