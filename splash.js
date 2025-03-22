// splash.js
window.addEventListener('DOMContentLoaded', () => {
  const progressFill = document.getElementById('progress-fill');
  let progress = 0;

  // Simple interval to fill progress bar from 0 to 100%.
  const interval = setInterval(() => {
    progress += 3;
    if (progress > 100) progress = 100;
    progressFill.style.width = progress + '%';

    if (progress === 100) {
      clearInterval(interval);
      // The main process (main.js) closes this splash once it's ready.
    }
  }, 120);
});
