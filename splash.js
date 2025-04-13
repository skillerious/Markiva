// splash.js
window.addEventListener('DOMContentLoaded', () => {
  const progressFill   = document.getElementById('progress-fill');
  const loadingDetails = document.getElementById('loading-details');

  let progress = 0;

  // A list of short messages to rotate through under the progress bar
  const loadingMessages = [
    "Initializing user settings...",
    "Loading renderer modules...",
    "Reticulating splines...",
    "Configuring CodeMirror...",
    "Scanning project files...",
    "Almost ready!"
  ];
  let msgIndex = 0;

  // Cycle messages every 700 ms
  const messageInterval = setInterval(() => {
    loadingDetails.textContent = loadingMessages[msgIndex % loadingMessages.length];
    msgIndex++;
  }, 700);

  // Increment the progress bar every 120 ms
  const progressInterval = setInterval(() => {
    progress += 3;
    if (progress > 100) progress = 100;
    progressFill.style.width = progress + '%';

    if (progress === 100) {
      clearInterval(progressInterval);
      // Optionally stop the message cycle if you wish:
      // clearInterval(messageInterval);

      // The main process (main.js) will close the splashWindow
      // after creating and showing the main window.
    }
  }, 120);
});
