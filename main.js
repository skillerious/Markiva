/***********************
 * main.js
 ***********************/
const { app, BrowserWindow, ipcMain, dialog } = require('electron');
const path = require('path');
const fs = require('fs');

let mainWindow = null;
let aboutWindow = null;
let splashWindow = null;
let settingsWindow = null;
let githubWindow = null; // Added for GitHub modal

/**
 * Utility: get the path to settings.json in userData
 */
function getSettingsFilePath() {
  return path.join(app.getPath('userData'), 'settings.json');
}

/**
 * Load the settings from settings.json (if it exists)
 */
function loadAppSettings() {
  const filePath = getSettingsFilePath();
  if (fs.existsSync(filePath)) {
    try {
      const data = fs.readFileSync(filePath, 'utf8');
      return JSON.parse(data);
    } catch (err) {
      console.error('[MAIN] Failed to parse settings.json:', err);
      return {};
    }
  }
  return {};
}

/**
 * Save the given settings object to settings.json
 */
function saveAppSettings(newSettings) {
  const filePath = getSettingsFilePath();
  try {
    fs.writeFileSync(filePath, JSON.stringify(newSettings, null, 2), 'utf8');
    console.log('[MAIN] Settings saved to', filePath);
  } catch (err) {
    console.error('[MAIN] Failed to save settings:', err);
  }
}

/**
 * Create a splash screen if you have one (optional).
 */
function createSplashWindow() {
  splashWindow = new BrowserWindow({
    width: 600,
    height: 300,
    frame: false,
    resizable: false,
    alwaysOnTop: true,
    center: true,
    skipTaskbar: true,
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false
    }
  });
  splashWindow.loadFile('splash.html');
  splashWindow.setMenuBarVisibility(false);
}

/**
 * Create the main window.
 */
function createMainWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    frame: false, // custom title bar
    show: false,  // hide until ready
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false
    }
  });

  mainWindow.loadFile('index.html');

  // Example: close splash & show main after some loading time
  setTimeout(() => {
    if (splashWindow) {
      splashWindow.close();
      splashWindow = null;
    }
    mainWindow.show();
    mainWindow.maximize();
  }, 3000);

  // Intercept the window "close" event to check for dirty file
  mainWindow.on('close', async (e) => {
    e.preventDefault(); // keep the window open until user decides
    try {
      const result = await mainWindow.webContents.executeJavaScript('window.attemptAppCloseFromMain()');
      if (result === 'proceed') {
        mainWindow.destroy();
      }
    } catch (err) {
      console.error('[MAIN] Error while prompting to close:', err);
      mainWindow.destroy();
    }
  });

  // Window controls from renderer
  ipcMain.on('minimize-window', () => mainWindow.minimize());
  ipcMain.on('maximize-window', () => {
    if (mainWindow.isMaximized()) {
      mainWindow.unmaximize();
    } else {
      mainWindow.maximize();
    }
  });
  ipcMain.on('close-window', () => mainWindow.close());
}

/**
 * Provide open-file dialog for .md or folder if requested
 */
ipcMain.handle('open-file-dialog', async (event, options) => {
  let dialogProps = {};
  if (options && options.isFolder) {
    dialogProps = { properties: ['openDirectory'] };
  } else {
    dialogProps = {
      properties: ['openFile'],
      filters: [
        { name: 'Markdown Files', extensions: ['md'] },
        { name: 'All Files', extensions: ['*'] }
      ]
    };
  }
  const result = await dialog.showOpenDialog(dialogProps);
  if (!result.canceled && result.filePaths.length > 0) {
    return result.filePaths[0];
  }
  return null;
});

/**
 * Provide a path for notes.json storage
 */
ipcMain.handle('get-user-data-path', () => {
  return app.getPath('userData');
});

/**
 * Open about.html in a frameless window with no flicker
 */
ipcMain.handle('open-about-window', () => {
  if (aboutWindow) {
    aboutWindow.focus();
    return;
  }
  aboutWindow = new BrowserWindow({
    width: 600,
    height: 550,
    resizable: false,
    frame: false,
    transparent: false,
    alwaysOnTop: true,
    show: false, // hide until ready
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false
    }
  });
  aboutWindow.setMenuBarVisibility(false);
  aboutWindow.loadFile('about.html');

  aboutWindow.once('ready-to-show', () => {
    aboutWindow.show();
  });

  aboutWindow.on('closed', () => {
    aboutWindow = null;
  });
});

/**
 * Open settings.html as a modal dialog on top of mainWindow
 */
ipcMain.handle('open-settings-window', () => {
  if (settingsWindow) {
    settingsWindow.focus();
    return;
  }
  settingsWindow = new BrowserWindow({
    width: 700,
    height: 550,
    useContentSize: true,
    resizable: true,
    frame: false,
    show: false,
    transparent: false,
    modal: true,
    parent: mainWindow,
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false
    }
  });
  settingsWindow.setMenuBarVisibility(false);
  settingsWindow.loadFile('settings.html');

  settingsWindow.once('ready-to-show', () => {
    settingsWindow.show();
  });

  settingsWindow.on('closed', () => {
    settingsWindow = null;
  });
});

/**
 * IPC to load the current settings from userData
 */
ipcMain.handle('load-app-settings', () => {
  const currentSettings = loadAppSettings();
  return currentSettings;
});

/**
 * IPC to save updated settings to userData
 */
ipcMain.handle('save-app-settings', (event, newSettings) => {
  saveAppSettings(newSettings);
  return 'ok';
});

/**
 * IPC handler for GitHub modal.
 * Opens a modal window to load github.html with GitHub markdown features,
 * with "show: false" and a dark background to minimize flicker.
 */
ipcMain.handle('open-github-window', () => {
  if (githubWindow) {
    githubWindow.focus();
    return;
  }
  githubWindow = new BrowserWindow({
    width: 1000,
    height: 725,
    modal: true,
    parent: mainWindow,
    frame: false,
    show: false, // Hide initially
    backgroundColor: '#0f1722', // Dark background to reduce white flicker
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false
    }
  });

  githubWindow.loadFile('github.html');

  // Show once ready, minimizing flicker
  githubWindow.once('ready-to-show', () => {
    githubWindow.show();
  });

  githubWindow.on('closed', () => {
    githubWindow = null;
  });
});

/**
 * IPC handler for inserting GitHub markdown.
 * Receives markdown from the GitHub modal and sends it to the main window.
 */
ipcMain.on('insert-markdown', (event, markdown) => {
  if (mainWindow && mainWindow.webContents) {
    mainWindow.webContents.send('insert-github-markdown', markdown);
  }
});

/**
 * App lifecycle
 */
app.whenReady().then(() => {
  createSplashWindow();
  createMainWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createSplashWindow();
      createMainWindow();
    }
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});
