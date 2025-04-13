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
let githubWindow = null; // For GitHub modal

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
 * Open about.html in a frameless window
 */
ipcMain.handle('open-about-window', () => {
  if (aboutWindow) {
    aboutWindow.focus();
    return;
  }
  aboutWindow = new BrowserWindow({
    width: 540,
    height: 700,
    resizable: false,
    frame: false,
    transparent: false,
    alwaysOnTop: true,
    show: false, 
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
    show: false,
    backgroundColor: '#0f1722',
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false
    }
  });

  githubWindow.loadFile('github.html');
  githubWindow.once('ready-to-show', () => {
    githubWindow.show();
  });
  githubWindow.on('closed', () => {
    githubWindow = null;
  });
});

ipcMain.on('insert-markdown', (event, markdown) => {
  if (mainWindow && mainWindow.webContents) {
    mainWindow.webContents.send('insert-github-markdown', markdown);
  }
});

/**
 * Example: print-document
 */
ipcMain.handle('print-document', async () => {
  if (!mainWindow) {
    return 'no-main-window';
  }
  try {
    mainWindow.webContents.print({ silent: false, printBackground: true });
    return 'ok';
  } catch (err) {
    console.error('[MAIN] print-document error:', err);
    return `error: ${err.message}`;
  }
});

/**
 * Export PDF:
 * 1) Show a "Save As" dialog for the user to pick a path
 * 2) Create a hidden window
 * 3) Load the provided "renderedHTML" into that window
 * 4) printToPDF
 * 5) Write the PDF to the chosen path
 */
ipcMain.handle('export-pdf', async (event, renderedHTML) => {
  try {
    const { canceled, filePath } = await dialog.showSaveDialog({
      title: 'Save PDF',
      buttonLabel: 'Export',
      filters: [{ name: 'PDF Files', extensions: ['pdf'] }]
    });
    if (canceled || !filePath) {
      return 'error: user canceled save dialog';
    }
    const hiddenWin = new BrowserWindow({
      show: false,
      webPreferences: {
        nodeIntegration: true,
        contextIsolation: false
      }
    });
    const dataURL = 'data:text/html;charset=utf-8,' + encodeURIComponent(renderedHTML);
    await hiddenWin.loadURL(dataURL);
    const pdfData = await hiddenWin.webContents.printToPDF({
      marginsType: 0,
      pageSize: 'A4',
      printBackground: true,
      landscape: false
    });
    fs.writeFileSync(filePath, pdfData);
    hiddenWin.close();
    console.log('[MAIN] PDF exported to =>', filePath);
    return 'ok';
  } catch (err) {
    console.error('[MAIN] export-pdf error:', err);
    return `error: ${err.message}`;
  }
});

/**
 * Spellcheck toggle
 */
ipcMain.handle('toggle-spellcheck', () => {
  try {
    const current = loadAppSettings();
    const newVal = !current.spellCheck;
    current.spellCheck = newVal;
    saveAppSettings(current);
    console.log('[MAIN] Toggled spellCheck =>', newVal);
    return newVal;
  } catch (err) {
    console.error('[MAIN] toggle-spellcheck failed:', err);
    return false;
  }
});

/**
 * Switch theme
 */
ipcMain.handle('switch-theme', () => {
  try {
    const current = loadAppSettings();
    let newTheme = 'dark';
    if (!current.theme || current.theme === 'dark') {
      newTheme = 'light';
    }
    current.theme = newTheme;
    saveAppSettings(current);
    console.log('[MAIN] Switched theme =>', newTheme);
    return newTheme;
  } catch (err) {
    console.error('[MAIN] switch-theme failed:', err);
    return 'dark';
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
