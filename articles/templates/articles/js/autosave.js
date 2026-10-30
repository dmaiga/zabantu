// articles/static/articles/js/autosave.js
document.addEventListener('DOMContentLoaded', function() {
  const form = document.querySelector('form');
  const inputs = form.querySelectorAll('input, textarea, select');
  
  inputs.forEach(input => {
    input.addEventListener('change', function() {
      const formData = new FormData(form);
      fetch(window.location.href, {
        method: 'POST',
        body: formData,
        headers: {
          'X-Requested-With': 'XMLHttpRequest',
        }
      });
    });
  });
});