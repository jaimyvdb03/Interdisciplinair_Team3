document.addEventListener('DOMContentLoaded', function() {
  const header = document.querySelector('.top-header');

  if (!header) {
    return;
  }

  function getScrollTop() {
    return window.scrollY || window.pageYOffset || document.documentElement.scrollTop || document.body.scrollTop || 0;
  }

  function updateHeaderScrollState() {
    if (getScrollTop() > 30) {
      header.classList.add('scrolled');
    } else {
      header.classList.remove('scrolled');
    }
  }

  window.addEventListener('scroll', updateHeaderScrollState, { passive: true });
  document.addEventListener('scroll', updateHeaderScrollState, { passive: true, capture: true });
  updateHeaderScrollState();
});
