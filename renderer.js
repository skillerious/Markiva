/***********************
 * renderer.js
 ***********************/
const { ipcRenderer } = require('electron');
const fs = require('fs');
const fsp = fs.promises;
const path = require('path');
const marked = require('marked');
const hljs = require('highlight.js');

// Require CodeMirror hint addons from local node_modules
require('codemirror/addon/hint/show-hint.js');
require('codemirror/addon/hint/anyword-hint.js');

// Dynamically import markdownlint since it is now an ES Module
let markdownlintModule = null;
(async () => {
  try {
    markdownlintModule = await import('markdownlint');
    markdownlintModule = markdownlintModule.default || markdownlintModule;
  } catch (err) {
    console.error("Failed to load markdownlint module:", err);
    markdownlintModule = null;
  }
})();

// Define a set of snippet completions for Markdown
const markdownSnippets = [
  { text: '**Bold Text**', displayText: 'Bold Text' },
  { text: '*Italic Text*', displayText: 'Italic Text' },
  { text: '~~Strikethrough~~', displayText: 'Strikethrough' },
  { text: 'Inline Code', displayText: 'Inline Code' },
  { text: '```language\nCode Block\n```', displayText: 'Code Block' },
  { text: '> Blockquote', displayText: 'Blockquote' },
  { text: '- List Item', displayText: 'List Item' },
  { text: '1. Numbered List Item', displayText: 'Numbered List' },
  { text: '[Link Text](https://)', displayText: 'Link' },
  { text: '![Alt Text](image.jpg)', displayText: 'Image' },
  { text: '| Header1 | Header2 |\n| --- | --- |\n| Data1 | Data2 |', displayText: 'Table' }
];

function provideHint(cm) {
  const cur = cm.getCursor();
  const token = cm.getTokenAt(cur);
  const start = token.start;
  const end = cur.ch;
  const currentWord = token.string.slice(0, end - start).toLowerCase();

  const list = markdownSnippets.filter(snippet =>
    snippet.displayText.toLowerCase().startsWith(currentWord)
  );

  return {
    list: list,
    from: CodeMirror.Pos(cur.line, start),
    to: CodeMirror.Pos(cur.line, end)
  };
}

// Setup Marked with Highlight.js for code blocks
marked.setOptions({
  highlight: (code, lang) => {
    if (lang && hljs.getLanguage(lang)) {
      return hljs.highlight(code, { language: lang }).value;
    }
    return hljs.highlightAuto(code).value;
  },
  mangle: false,
  headerIds: false
});

// --- Global State ---
let userDataPath = '';
let notes = [];
let tabs = [];
let activeTab = null;
let cmEditor = null;

// For searching
let searchMarks = [];
let currentSearchCursor = null;
let currentSearchMatch = null;

// We'll store user settings in this object
let userSettings = {};

// --- Markdownlint function ---
function markdownLinter(text) {
  if (!markdownlintModule) return [];
  const options = {
    strings: { content: text },
    config: { "default": true }
  };
  const result = markdownlintModule.sync(options);
  const errors = result.content || [];
  const annotations = [];
  errors.forEach(error => {
    const line = error.lineNumber - 1;
    const lineText = cmEditor ? cmEditor.getLine(line) : "";
    annotations.push({
      from: CodeMirror.Pos(line, 0),
      to: CodeMirror.Pos(line, lineText.length),
      message: `${error.ruleNames[0]}: ${error.ruleDescription}`,
      severity: 'warning'
    });
  });
  return annotations;
}

// --- Debounce Utility ---
function debounce(func, delay) {
  let timeout;
  return function(...args) {
    clearTimeout(timeout);
    timeout = setTimeout(() => func.apply(this, args), delay);
  };
}

/**
 * Helper to display AI results in bullet-list format with customAlert.
 */
function displayAiResults(title, lines) {
  if (!lines || lines.length === 0) {
    window.customAlert(`${title}\n\n(No results)`);
    return;
  }
  const bulletList = lines.map(item => `• ${item}`).join('\n');
  const final = `${title}\n\n${bulletList}`;
  window.customAlert(final);
}

// --- AI Tool Functions ---
async function summarizeText(text) {
  if (!text.trim()) return [];
  const paragraphs = text.split(/\n\s*\n/).filter(p => p.trim());
  const summaryLines = [];
  paragraphs.forEach(par => {
    const sentences = par.split(/[.?!]\s+/).filter(s => s.trim());
    const excerpt = sentences.slice(0, 2).join('. ');
    if (excerpt) {
      summaryLines.push(excerpt.trim() + (sentences.length > 2 ? '...' : ''));
    }
  });
  if (summaryLines.length === 0) {
    summaryLines.push(text.trim().slice(0, 100) + '...');
  }
  return summaryLines;
}

async function suggestHeadings(text) {
  if (!text.trim()) return [];
  const lines = text.split('\n');
  const suggestions = [];
  const existingHeadings = lines.filter(line => line.trim().match(/^#+\s+/));
  existingHeadings.forEach(h => {
    suggestions.push(`${h.trim()} (Already a heading)`);
  });
  const paragraphs = text.split(/\n\s*\n/).filter(p => p.trim());
  paragraphs.forEach(par => {
    const isHeading = par.trim().match(/^#+\s+/);
    if (!isHeading && par.trim().length > 80) {
      const words = par.trim().split(/\s+/).slice(0, 5).join(' ');
      suggestions.push(`Suggested Heading: ${words}...`);
    }
  });
  if (suggestions.length === 0) {
    suggestions.push("No headings or suggestions found.");
  }
  return suggestions;
}

async function simplifyText(text) {
  if (!text.trim()) return [];
  const fillerWords = ['the','very','just','actually','really','that','so','basically','kind','of'];
  const paragraphs = text.split(/\n\s*\n/).filter(p => p.trim());
  const simplifiedLines = [];
  paragraphs.forEach(par => {
    let simplified = par.toLowerCase();
    fillerWords.forEach(word => {
      const re = new RegExp(`\\b${word}\\b`, 'gi');
      simplified = simplified.replace(re, '');
    });
    simplified = simplified.replace(/\s{2,}/g, ' ').trim();
    if (simplified) {
      simplifiedLines.push(simplified);
    }
  });
  if (simplifiedLines.length === 0) {
    simplifiedLines.push(text.toLowerCase().slice(0, 200) + '...');
  }
  return simplifiedLines;
}

// --- Export Functions ---
async function exportCurrentTabToPDF() {
  if (!activeTab) return;
  const previewEl = document.getElementById('preview-content');
  if (!previewEl) {
    console.error("No preview-content => cannot export PDF");
    return;
  }
  const renderedHTML = `
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="UTF-8">
      <title>Exported PDF - Markiva</title>
      <link rel="stylesheet" href="style.css">
    </head>
    <body>
      ${previewEl.innerHTML}
    </body>
    </html>
  `;
  const result = await ipcRenderer.invoke('export-pdf', renderedHTML);
  if (result.startsWith('error:')) {
    console.error("PDF export failed =>", result);
  } else {
    console.log("PDF exported successfully (no popup).");
  }
}

async function exportCurrentTabToHTML() {
  if (!activeTab) return;
  const content = cmEditor.getValue();
  const htmlContent = `
  <!DOCTYPE html>
  <html>
  <head>
    <meta charset="UTF-8">
    <title>Exported Markiva Document</title>
    <link rel="stylesheet" href="style.css">
  </head>
  <body>
    ${marked.parse(content)}
  </body>
  </html>
  `;
  const result = await ipcRenderer.invoke('export-html', htmlContent);
  if(result.startsWith('error:')) {
    console.error("HTML export failed =>", result);
  } else {
    console.log("HTML exported successfully (no popup).");
  }
}

// --- Revised Alignment Function ---
function alignSelection(alignment) {
  if (!cmEditor) return;
  cmEditor.operation(() => {
    const selections = cmEditor.listSelections();
    selections.forEach(sel => {
      let rawText = cmEditor.getRange(sel.anchor, sel.head);
      if (!rawText.trim()) {
        const curLine = cmEditor.getCursor().line;
        rawText = cmEditor.getLine(curLine);
        sel = {
          anchor: { line: curLine, ch: 0 },
          head: { line: curLine, ch: rawText.length }
        };
      }
      const wrapperRegex = /<(?:div|p)\s+(?:style="text-align:\s*[^"]+"\s*|align="[^"]+"\s*)(?:[^>]*)>([\s\S]*?)<\/(?:div|p)>/gi;
      let cleaned = rawText.replace(wrapperRegex, '$1');
      cleaned = cleaned.replace(/^\s+|\s+$/g, '');
      cleaned = cleaned.replace(/\r?\n\s*/g, ' ');
      const finalText = `<div style="text-align: ${alignment};">\n\n${cleaned}\n</div>`;
      cmEditor.replaceRange(finalText, sel.anchor, sel.head);
    });
  });
  cmEditor.focus();
}

// --- View Mode Button Helper ---
function setViewModeActive(mode) {
  console.log("Setting view mode active:", mode);
  const buttons = document.querySelectorAll('.view-mode-btn');
  buttons.forEach(btn => btn.classList.remove('active'));
  if (mode === 'editor') {
    document.getElementById('btn-editor-only')?.classList.add('active');
  } else if (mode === 'split') {
    document.getElementById('btn-split-view')?.classList.add('active');
  } else if (mode === 'preview') {
    document.getElementById('btn-preview-only')?.classList.add('active');
  }
}


// --- Custom Prompts ---
window.customAlert = function(message) {
  return new Promise((resolve) => {
    const customPromptEl = document.getElementById('custom-prompt');
    const promptMessageEl = customPromptEl.querySelector('.prompt-message');
    const promptInputEl = document.getElementById('prompt-input');
    const promptOkBtn = document.getElementById('prompt-ok');
    const promptCancelBtn = document.getElementById('prompt-cancel');
    promptMessageEl.textContent = message;
    promptInputEl.style.display = 'none';
    customPromptEl.style.display = 'flex';
    function cleanup() {
      customPromptEl.style.display = 'none';
      promptOkBtn.removeEventListener('click', onOk);
      promptCancelBtn.removeEventListener('click', onOk);
      promptInputEl.style.display = '';
    }
    function onOk() {
      cleanup();
      resolve();
    }
    promptOkBtn.addEventListener('click', onOk);
    promptCancelBtn.addEventListener('click', onOk);
  });
};

function customPrompt(message, defaultValue = '') {
  return new Promise((resolve) => {
    const customPromptEl = document.getElementById('custom-prompt');
    const promptMessageEl = customPromptEl.querySelector('.prompt-message');
    const promptInputEl = document.getElementById('prompt-input');
    const promptOkBtn = document.getElementById('prompt-ok');
    const promptCancelBtn = document.getElementById('prompt-cancel');
    promptMessageEl.textContent = message;
    promptInputEl.value = defaultValue;
    promptInputEl.style.display = '';
    customPromptEl.style.display = 'flex';
    function cleanup() {
      customPromptEl.style.display = 'none';
      promptOkBtn.removeEventListener('click', onOk);
      promptCancelBtn.removeEventListener('click', onCancel);
    }
    function onOk() {
      cleanup();
      resolve(promptInputEl.value);
    }
    function onCancel() {
      cleanup();
      resolve(null);
    }
    promptOkBtn.addEventListener('click', onOk);
    promptCancelBtn.addEventListener('click', onCancel);
  });
};

// --- DOMContentLoaded and Event Handlers ---
window.addEventListener('DOMContentLoaded', () => {
  console.log("[DEBUG] DOM loaded, hooking up events...");

  // Basic references
  const glassTabs = document.getElementById('glass-tabs');
  const previewContent = document.getElementById('preview-content');
  const fileSearch = document.getElementById('file-search');
  const fileList = document.getElementById('file-list');
  const notesList = document.getElementById('notes-list');
  const newNoteInput = document.getElementById('new-note-input');
  const statusWordCount = document.getElementById('word-count');
  const statusReadTime = document.getElementById('read-time');

  const customPromptEl = document.getElementById('custom-prompt');
  const promptMessageEl = customPromptEl.querySelector('.prompt-message');
  const promptInputEl = document.getElementById('prompt-input');
  const promptOkBtn = document.getElementById('prompt-ok');
  const promptCancelBtn = document.getElementById('prompt-cancel');

  const tableDialog = document.getElementById('table-dialog');
  const tableRowsInput = document.getElementById('table-rows');
  const tableColsInput = document.getElementById('table-cols');
  const tableHeaderCheck = document.getElementById('table-header');
  const tableOkBtn = document.getElementById('table-ok');
  const tableCancelBtn = document.getElementById('table-cancel');

  const mediaDialog = document.getElementById('media-dialog');
  const mediaAlt = document.getElementById('media-alt');
  const mediaUrl = document.getElementById('media-url');
  const mediaOk = document.getElementById('media-ok');
  const mediaCancel = document.getElementById('media-cancel');
  const mediaBrowse = document.getElementById('media-browse');

  const tableEditorPanel = document.getElementById('table-editor-panel');
  const addRowBtn = document.getElementById('table-add-row');
  const removeRowBtn = document.getElementById('table-remove-row');
  const addColBtn = document.getElementById('table-add-col');
  const removeColBtn = document.getElementById('table-remove-col');

  const saveChangesDialog = document.getElementById('save-changes-dialog');
  const saveChangesFilename = document.getElementById('save-changes-filename');
  const saveChangesSaveBtn = document.getElementById('save-changes-save-btn');
  const saveChangesDontBtn = document.getElementById('save-changes-dontsave-btn');
  const saveChangesCancelBtn = document.getElementById('save-changes-cancel-btn');

  const minButton = document.getElementById('min-button');
  const maxButton = document.getElementById('max-button');
  const closeButton = document.getElementById('close-button');
  const newFileBtn = document.getElementById('new-file-btn');
  const openFileBtn = document.getElementById('open-file-btn');
  const saveFileBtn = document.getElementById('save-file-btn');
  const renameFileBtn = document.getElementById('rename-file-btn');
  const refreshFilesBtn = document.getElementById('refresh-files-btn');
  const copyPreviewBtn = document.getElementById('copy-preview-btn');
  const aboutBtn = document.getElementById('about-btn');
  const settingsBtn = document.getElementById('settings-btn');

  const btnBold = document.getElementById('btn-bold');
  const btnItalic = document.getElementById('btn-italic');
  const btnCode = document.getElementById('btn-code');
  const btnLink = document.getElementById('btn-link');
  const btnHeading = document.getElementById('btn-heading');
  const btnTable = document.getElementById('btn-table');
  const btnMedia = document.getElementById('btn-media');
  const btnSearch = document.getElementById('btn-search');

  const alignLeftBtn = document.getElementById('align-left');
  const alignCenterBtn = document.getElementById('align-center');
  const alignRightBtn = document.getElementById('align-right');

  const githubMenuBtn = document.getElementById('github-menu');
  const editorContainer = document.getElementById('editor-container');
  const previewContainer = document.getElementById('preview-container');
  const btnEditorOnly = document.getElementById('btn-editor-only');
  const btnSplitView = document.getElementById('btn-split-view');
  const btnPreviewOnly = document.getElementById('btn-preview-only');

  const fileContextMenu = document.getElementById('file-context-menu');
  let fileContextMenuTargetPath = null;

  // Additional new Buttons
  const btnPrint = document.getElementById('btn-print');
  const btnExportPDF = document.getElementById('btn-export-pdf');
  const btnToggleSpellcheck = document.getElementById('btn-toggle-spellcheck');
  const btnThemeSwitch = document.getElementById('btn-theme-switch');

  // set the default view mode to split
  setViewModeActive('split');
  // Hide context menu on any left-click

  document.addEventListener('click', () => {
    fileContextMenu.style.display = 'none';
  });

  // Right-click file list => context menu
  fileList.addEventListener('contextmenu', async (e) => {
    e.preventDefault();
    const li = e.target.closest('li');
    if (!li) return;
    const anchor = li.querySelector('a');
    if (!anchor) return;
    const folder = userSettings.defaultFolder || process.cwd();
    const filename = anchor.textContent.trim();
    const filePath = path.join(folder, filename);
    fileContextMenuTargetPath = filePath;
    fileContextMenu.style.display = 'block';
    fileContextMenu.style.left = `${e.pageX}px`;
    fileContextMenu.style.top = `${e.pageY}px`;
  });

  fileContextMenu.addEventListener('click', async (e) => {
    e.stopPropagation();
    fileContextMenu.style.display = 'none';
    const li = e.target.closest('li');
    if (!li || !fileContextMenuTargetPath) return;
    const action = li.getAttribute('data-action');
    if (!action) return;
    if (action === 'open') {
      loadFile(fileContextMenuTargetPath);
    } else if (action === 'rename') {
      const base = path.basename(fileContextMenuTargetPath);
      const newName = await customPrompt('Rename file:', base);
      if (!newName || newName === base) return;
      let finalName = newName;
      if (!/\.[Mm][Dd]$/.test(finalName)) {
        finalName += '.md';
      }
      const dir = path.dirname(fileContextMenuTargetPath);
      const newPath = path.join(dir, finalName);
      try {
        await fsp.rename(fileContextMenuTargetPath, newPath);
        refreshFileList();
        const tabObj = tabs.find(t => t.filePath === fileContextMenuTargetPath);
        if (tabObj) {
          tabObj.filePath = newPath;
          tabObj.fileName = finalName;
          tabObj.originalContent = tabObj.content;
          tabObj.isDirty = false;
          if (tabObj.tabEl) {
            tabObj.tabEl.querySelector('.tab-text').textContent = finalName;
          }
        }
      } catch (err) {
        customAlert(`Failed to rename file.\n${err.message}`);
      }
    } else if (action === 'delete') {
      const base = path.basename(fileContextMenuTargetPath);
      const confirmDel = await showYesCancelDialog(`Are you sure you want to delete "${base}"?`);
      if (confirmDel === 'yes') {
        try {
          await fsp.unlink(fileContextMenuTargetPath);
          refreshFileList();
          const tabObj = tabs.find(t => t.filePath === fileContextMenuTargetPath);
          if (tabObj) {
            closeTab(fileContextMenuTargetPath);
          }
        } catch (err) {
          customAlert(`Failed to delete file.\n${err.message}`);
        }
      }
    }
  });

  ipcRenderer.on('insert-github-markdown', (event, markdown) => {
    if (typeof window.insertGitHubMarkdown === 'function') {
      window.insertGitHubMarkdown(markdown);
    } else {
      console.error("insert-github-markdown is not defined.");
    }
  });

  async function showYesCancelDialog(message) {
    return new Promise((resolve) => {
      promptMessageEl.textContent = message;
      promptInputEl.style.display = 'none';
      customPromptEl.style.display = 'flex';
      const oldOkText = promptOkBtn.textContent;
      const oldCancelText = promptCancelBtn.textContent;
      promptOkBtn.textContent = 'Yes';
      promptCancelBtn.textContent = 'Cancel';
      function cleanup(result) {
        customPromptEl.style.display = 'none';
        promptOkBtn.removeEventListener('click', onYes);
        promptCancelBtn.removeEventListener('click', onCancel);
        promptOkBtn.textContent = oldOkText;
        promptCancelBtn.textContent = oldCancelText;
        resolve(result);
      }
      function onYes() { cleanup('yes'); }
      function onCancel() { cleanup('cancel'); }
      promptOkBtn.addEventListener('click', onYes);
      promptCancelBtn.addEventListener('click', onCancel);
    });
  }

  // View Mode Buttons – set active state and adjust display
  btnEditorOnly?.addEventListener('click', () => {
    editorContainer.style.display = 'flex';
    previewContainer.style.display = 'none';
    setViewModeActive('editor');
  });
  btnSplitView?.addEventListener('click', () => {
    editorContainer.style.display = 'flex';
    previewContainer.style.display = 'flex';
    setViewModeActive('split');
  });
  btnPreviewOnly?.addEventListener('click', () => {
    editorContainer.style.display = 'none';
    previewContainer.style.display = 'flex';
    setViewModeActive('preview');
  });

  window.attemptAppCloseFromMain = async function() {
    const dirtyTab = tabs.find(t => t.isDirty);
    if (!dirtyTab) return 'proceed';
    const active = tabs.find(t => t.filePath === activeTab);
    if (!active) return 'proceed';
    const fileName = active.fileName || 'Untitled';
    const choice = await showSaveChangesDialog(fileName);
    if (choice === 'save') {
      if (cmEditor && activeTab === active.filePath) {
        active.content = cmEditor.getValue();
      }
      await saveSpecificTab(active.filePath);
      return 'proceed';
    } else if (choice === 'dontsave') {
      return 'proceed';
    } else {
      return 'cancel';
    }
  };

  function showSaveChangesDialog(filename) {
    return new Promise((resolve) => {
      saveChangesFilename.textContent = filename || 'Untitled';
      saveChangesDialog.style.display = 'flex';
      function cleanup(result) {
        saveChangesDialog.style.display = 'none';
        saveChangesSaveBtn.removeEventListener('click', onSave);
        saveChangesDontBtn.removeEventListener('click', onDont);
        saveChangesCancelBtn.removeEventListener('click', onCancel);
        resolve(result);
      }
      function onSave() { cleanup('save'); }
      function onDont() { cleanup('dontsave'); }
      function onCancel() { cleanup('cancel'); }
      saveChangesSaveBtn.addEventListener('click', onSave);
      saveChangesDontBtn.addEventListener('click', onDont);
      saveChangesCancelBtn.addEventListener('click', onCancel);
    });
  }

  function customPrompt(message, defaultValue = '') {
    return new Promise((resolve) => {
      promptMessageEl.textContent = message;
      promptInputEl.value = defaultValue;
      promptInputEl.style.display = '';
      customPromptEl.style.display = 'flex';
      function cleanup() {
        customPromptEl.style.display = 'none';
        promptOkBtn.removeEventListener('click', onOk);
        promptCancelBtn.removeEventListener('click', onCancel);
      }
      function onOk() {
        cleanup();
        resolve(promptInputEl.value);
      }
      function onCancel() {
        cleanup();
        resolve(null);
      }
      promptOkBtn.addEventListener('click', onOk);
      promptCancelBtn.addEventListener('click', onCancel);
    });
  }

  function customAlert(message) {
    return new Promise((resolve) => {
      promptMessageEl.textContent = message;
      promptInputEl.style.display = 'none';
      customPromptEl.style.display = 'flex';
      function cleanup() {
        customPromptEl.style.display = 'none';
        promptOkBtn.removeEventListener('click', onOk);
        promptCancelBtn.removeEventListener('click', onOk);
        promptInputEl.style.display = '';
      }
      function onOk() {
        cleanup();
        resolve();
      }
      promptOkBtn.addEventListener('click', onOk);
      promptCancelBtn.addEventListener('click', onOk);
    });
  }

  // NOTES
  let notes = [];
  function loadNotes() {
    if (!userDataPath) {
      console.log("No userDataPath yet—can't load notes.");
      return;
    }
    const notesFile = path.join(userDataPath, 'notes.json');
    try {
      if (fs.existsSync(notesFile)) {
        const data = fs.readFileSync(notesFile, 'utf8');
        notes = JSON.parse(data);
      } else {
        notes = [];
      }
    } catch (err) {
      console.error('Error loading notes:', err);
      notes = [];
    }
    renderNotes();
  }
  function saveNotes() {
    if (!userDataPath) return;
    const notesFile = path.join(userDataPath, 'notes.json');
    try {
      fs.writeFileSync(notesFile, JSON.stringify(notes), 'utf8');
    } catch (err) {
      console.error('Error saving notes:', err);
    }
  }
  function renderNotes() {
    if (notes.length === 0) {
      notesList.innerHTML = '';
      notesList.classList.add('notes-empty');
      const wrapper = document.createElement('div');
      wrapper.className = 'notes-empty-wrapper';
      const emptyImg = document.createElement('img');
      emptyImg.src = 'assets/empty.png';
      emptyImg.alt = 'No notes';
      emptyImg.classList.add('notes-empty-image');
      const emptyText = document.createElement('p');
      emptyText.textContent = 'Add a note';
      emptyText.classList.add('notes-empty-text');
      wrapper.appendChild(emptyImg);
      wrapper.appendChild(emptyText);
      notesList.appendChild(wrapper);
      return;
    }
    notesList.classList.remove('notes-empty');
    notesList.innerHTML = '';
    const sorted = notes.slice().sort((a, b) => {
      if (a.pinned && !b.pinned) return -1;
      if (!a.pinned && b.pinned) return 1;
      if (a.completed && !b.completed) return 1;
      if (!a.completed && b.completed) return -1;
      return b.id - a.id;
    });
    sorted.forEach(note => {
      const li = document.createElement('li');
      if (note.completed) li.classList.add('completed');
      const leftDiv = document.createElement('div');
      leftDiv.className = 'note-left';
      const pinIcon = document.createElement('i');
      pinIcon.className = 'pin-icon fas fa-thumbt';
      if (note.pinned) pinIcon.classList.add('active');
      pinIcon.addEventListener('click', (e) => {
        e.stopPropagation();
        note.pinned = !note.pinned;
        saveNotes();
        renderNotes();
      });
      const textSpan = document.createElement('span');
      textSpan.textContent = note.text;
      leftDiv.appendChild(pinIcon);
      leftDiv.appendChild(textSpan);
      li.appendChild(leftDiv);
      const removeBtn = document.createElement('button');
      removeBtn.textContent = '✖';
      removeBtn.classList.add('remove-note-btn');
      removeBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        notes = notes.filter(n => n.id !== note.id);
        saveNotes();
        renderNotes();
      });
      li.appendChild(removeBtn);
      li.addEventListener('click', () => {
        note.completed = !note.completed;
        saveNotes();
        renderNotes();
      });
      notesList.appendChild(li);
    });
  }
  const addNoteButton = document.getElementById('add-note-button');
  if (addNoteButton) {
    addNoteButton.addEventListener('click', () => {
      const noteText = newNoteInput.value.trim();
      if (noteText) {
        const newNote = { id: Date.now(), text: noteText, pinned: false, completed: false };
        notes.push(newNote);
        saveNotes();
        renderNotes();
        newNoteInput.value = '';
      }
    });
  }

  async function rememberLastFile(filePath) {
    userSettings.lastFile = filePath;
    try {
      await ipcRenderer.invoke('save-app-settings', userSettings);
      console.log("[DEBUG] rememberLastFile => saved lastFile:", filePath);
    } catch (err) {
      console.error("[DEBUG] Failed to save lastFile:", err);
    }
  }

  async function refreshFileList() {
    fileList.innerHTML = '';
    const folder = userSettings.defaultFolder || process.cwd();
    let all = [];
    try {
      all = await fsp.readdir(folder);
    } catch (err) {
      console.error('Error reading directory:', err);
      return;
    }
    const filter = fileSearch.value.trim().toLowerCase();
    const mdFiles = all.filter(f =>
      f.toLowerCase().endsWith('.md') && f.toLowerCase().includes(filter)
    ).sort();
    if (mdFiles.length === 0) {
      const li = document.createElement('li');
      li.textContent = 'No markdown files found.';
      li.style.color = '#aaa';
      fileList.appendChild(li);
    } else {
      mdFiles.forEach(filename => {
        const li = document.createElement('li');
        const link = document.createElement('a');
        const icon = document.createElement('i');
        icon.className = 'fas fa-file-alt file-icon';
        link.appendChild(icon);
        link.appendChild(document.createTextNode(filename));
        link.href = '#';
        link.addEventListener('click', () => {
          const fullPath = path.join(folder, filename);
          loadFile(fullPath);
        });
        li.appendChild(link);
        fileList.appendChild(li);
      });
    }
  }
  fileSearch.addEventListener('input', refreshFileList);

  async function loadFile(filePath) {
    try {
      const content = await fsp.readFile(filePath, 'utf8');
      createOrActivateTab(filePath, path.basename(filePath), content);
    } catch (err) {
      console.error('Error loading file:', err);
      await customAlert(`Failed to load file.\n${err.message}`);
    }
  }

  function createOrActivateTab(filePath, fileName, content) {
    const existing = tabs.find(t => t.filePath === filePath);
    if (existing) {
      switchTab(filePath);
      return;
    }
    const newTab = {
      filePath,
      fileName,
      content,
      originalContent: content,
      isDirty: false,
      tabEl: null
    };
    tabs.push(newTab);
    const tabEl = document.createElement('div');
    tabEl.className = 'glass-tab';
    tabEl.innerHTML = `<span class="tab-text">${fileName}</span><span class="close-tab">×</span>`;
    glassTabs.appendChild(tabEl);
    tabEl.addEventListener('click', (e) => {
      if (e.target.classList.contains('close-tab')) return;
      switchTab(filePath);
    });
    const closeBtn = tabEl.querySelector('.close-tab');
    closeBtn.addEventListener('click', async (e) => {
      e.stopPropagation();
      await attemptCloseTab(filePath);
    });
    newTab.tabEl = tabEl;
    switchTab(filePath);
  }

  async function switchTab(filePath) {
    if (activeTab) {
      const oldTab = tabs.find(t => t.filePath === activeTab);
      if (oldTab && cmEditor) {
        oldTab.content = cmEditor.getValue();
        oldTab.isDirty = (cmEditor.getValue() !== oldTab.originalContent);
      }
    }
    activeTab = filePath;
    tabs.forEach(t => {
      if (t.tabEl) {
        t.tabEl.classList.toggle('active', t.filePath === filePath);
      }
    });
    const activeObj = tabs.find(t => t.filePath === filePath);
    if (activeObj && cmEditor) {
      cmEditor.setValue(activeObj.content || '');
      cmEditor.clearHistory();
      updatePreview();
    }
    if (filePath) {
      await rememberLastFile(filePath);
    }
  }

  async function attemptCloseTab(filePath) {
    const tabObj = tabs.find(t => t.filePath === filePath);
    if (!tabObj) return;
    if (activeTab === filePath && cmEditor) {
      tabObj.content = cmEditor.getValue();
      tabObj.isDirty = (tabObj.content !== tabObj.originalContent);
    }
    if (tabObj.isDirty) {
      const choice = await showSaveChangesDialog(tabObj.fileName || 'Untitled');
      if (choice === 'save') {
        await saveSpecificTab(filePath);
        closeTab(filePath);
      } else if (choice === 'dontsave') {
        closeTab(filePath);
      } else {
        return;
      }
    } else {
      closeTab(filePath);
    }
  }

  function closeTab(filePath) {
    const idx = tabs.findIndex(t => t.filePath === filePath);
    if (idx === -1) return;
    const tabObj = tabs[idx];
    if (tabObj.tabEl) {
      glassTabs.removeChild(tabObj.tabEl);
    }
    tabs.splice(idx, 1);
    if (activeTab === filePath) {
      if (tabs.length > 0) {
        switchTab(tabs[tabs.length - 1].filePath);
      } else {
        activeTab = null;
        if (cmEditor) cmEditor.setValue('');
        previewContent.innerHTML = '';
        updateStatusBar();
      }
    }
  }

  async function saveSpecificTab(filePath) {
    const obj = tabs.find(t => t.filePath === filePath);
    if (!obj) return;
    try {
      await fsp.writeFile(filePath, obj.content, 'utf8');
      obj.originalContent = obj.content;
      obj.isDirty = false;
    } catch (err) {
      console.error('Error saving file:', err);
      await customAlert(`Failed to save file.\n${err.message}`);
    }
  }

  // Initialize CodeMirror
  function initCodeMirror() {
    const cmOptions = {
      mode: 'markdown',
      theme: 'material-darker',
      lineNumbers: true,
      lineWrapping: true,
      inputStyle: 'contenteditable',
      spellcheck: true,
      gutters: ["CodeMirror-linenumbers", "CodeMirror-lint-markers"]
    };
    if (markdownlintModule) {
      cmOptions.lint = { getAnnotations: markdownLinter, async: false };
    }
    cmEditor = CodeMirror(document.getElementById('editor-wrapper'), cmOptions);
    cmEditor.on('change', () => {
      updatePreview();
      if (activeTab) {
        const tab = tabs.find(t => t.filePath === activeTab);
        if (tab) {
          tab.isDirty = (cmEditor.getValue() !== tab.originalContent);
        }
      }
    });
    
    cmEditor.on('scroll', () => {
      const info = cmEditor.getScrollInfo();
      const ratio = info.top / (info.height - info.clientHeight);
      const previewMax = previewContent.scrollHeight - previewContent.clientHeight;
      previewContent.scrollTop = ratio * previewMax;
    });
    cmEditor.on('cursorActivity', updateTableEditorVisibility);
    cmEditor.on('keyup', (cm, event) => {
      if ((event.ctrlKey || event.metaKey) && event.keyCode === 32) {
        if (cm.showHint) {
          cm.showHint({ hint: provideHint, completeSingle: false });
        }
      }
    });
  }

  // Updated Preview
  function updatePreview() {
    if (!cmEditor) return;
    const markdownText = cmEditor.getValue();
    let html = marked.parse(markdownText);
    previewContent.innerHTML = html;
    updateStatusBar();
    if (window.MathJax) {
      MathJax.typesetPromise([previewContent]).catch(err => {
        console.error('MathJax typeset failed: ', err);
      });
    }
  }

  function updateStatusBar() {
    if (!cmEditor) {
      statusWordCount.textContent = 'Words: 0';
      statusReadTime.textContent = 'Read Time: 0 min';
      return;
    }
    const text = cmEditor.getValue().trim();
    const words = text.split(/\s+/).filter(w => w.length > 0).length;
    const readTime = Math.ceil(words / 200);
    statusWordCount.textContent = `Words: ${words}`;
    statusReadTime.textContent = `Read Time: ${readTime} min`;
  }

  function updateTableEditorVisibility() {
    if (!cmEditor) return;
    const lineText = cmEditor.getLine(cmEditor.getCursor().line);
    tableEditorPanel.style.display = lineText.includes('|') ? 'flex' : 'none';
  }

  function getCurrentTableBlock() {
    if (!cmEditor) return null;
    const cursor = cmEditor.getCursor();
    let startLine = cursor.line;
    let endLine = cursor.line;
    const lineCount = cmEditor.lineCount();
    while (startLine > 0 && cmEditor.getLine(startLine - 1).includes('|')) {
      startLine--;
    }
    while (endLine < lineCount - 1 && cmEditor.getLine(endLine + 1).includes('|')) {
      endLine++;
    }
    const tableText = cmEditor.getRange({ line: startLine, ch: 0 }, { line: endLine + 1, ch: 0 });
    return { startLine, endLine, tableText };
  }

  function parseTable(tableText) {
    const lines = tableText.trim().split('\n').map(line => line.trim());
    return lines.map(line => {
      if (line.startsWith('|')) line = line.slice(1);
      if (line.endsWith('|')) line = line.slice(0, -1);
      return line.split('|').map(cell => cell.trim());
    });
  }

  function formatTable(rows) {
    return rows.map(row => '| ' + row.join(' | ') + ' |').join('\n') + '\n';
  }

  function tableAddRow() {
    const block = getCurrentTableBlock();
    if (!block) return;
    const { startLine, endLine } = block;
    let rows = parseTable(block.tableText);
    const colCount = rows[0].length;
    const newRow = Array(colCount).fill('data');
    const cursor = cmEditor.getCursor();
    let relativeLine = cursor.line - startLine;
    let insertIndex = relativeLine + 1;
    const isSepRow = row => row.every(cell => /^-+(:)?$/.test(cell));
    if (relativeLine === 0 && rows.length > 1 && isSepRow(rows[1])) {
      insertIndex = 2;
    }
    rows.splice(insertIndex, 0, newRow);
    const newText = formatTable(rows);
    cmEditor.replaceRange(newText, { line: startLine, ch: 0 }, { line: endLine + 1, ch: 0 });
  }

  function tableRemoveRow() {
    const block = getCurrentTableBlock();
    if (!block) return;
    const { startLine, endLine } = block;
    let rows = parseTable(block.tableText);
    const cursor = cmEditor.getCursor();
    let relativeLine = cursor.line - startLine;
    if (relativeLine < 2) {
      if (rows.length > 2) {
        relativeLine = 2;
      } else {
        return;
      }
    }
    if (rows.length <= 3) return;
    rows.splice(relativeLine, 1);
    const newText = formatTable(rows);
    cmEditor.replaceRange(newText, { line: startLine, ch: 0 }, { line: endLine + 1, ch: 0 });
  }

  function tableAddColumn() {
    const block = getCurrentTableBlock();
    if (!block) return;
    const { startLine, endLine } = block;
    let rows = parseTable(block.tableText);
    const colCount = rows[0].length;
    const isSepRow = row => row.every(cell => /^-+(:)?$/.test(cell));
    if (rows.length >= 2 && isSepRow(rows[1])) {
      rows[0].push(`Header${colCount + 1}`);
      rows[1].push('---');
      for (let i = 2; i < rows.length; i++) {
        rows[i].push('data');
      }
    } else {
      rows = rows.map(row => {
        row.push('data');
        return row;
      });
    }
    const newText = formatTable(rows);
    cmEditor.replaceRange(newText, { line: startLine, ch: 0 }, { line: endLine + 1, ch: 0 });
  }

  function tableRemoveColumn() {
    const block = getCurrentTableBlock();
    if (!block) return;
    const { startLine, endLine } = block;
    let rows = parseTable(block.tableText);
    if (rows[0].length <= 1) return;
    const cursor = cmEditor.getCursor();
    const lineText = cmEditor.getLine(cursor.line);
    let parts = lineText.split('|').map(part => part.trim());
    if (parts[0] === '') parts.shift();
    if (parts[parts.length - 1] === '') parts.pop();
    let ch = cursor.ch;
    let colIndex = 0;
    let pos = 0;
    for (let i = 0; i < parts.length; i++) {
      pos += parts[i].length + 3;
      if (pos > ch) {
        colIndex = i;
        break;
      }
    }
    rows = rows.map(row => {
      if (row.length > colIndex) {
        row.splice(colIndex, 1);
      }
      return row;
    });
    const newText = formatTable(rows);
    cmEditor.replaceRange(newText, { line: startLine, ch: 0 }, { line: endLine + 1, ch: 0 });
  }

  addRowBtn.addEventListener('click', () => tableAddRow());
  removeRowBtn.addEventListener('click', () => tableRemoveRow());
  addColBtn.addEventListener('click', () => tableAddColumn());
  removeColBtn.addEventListener('click', () => tableRemoveColumn());

  // Link, Media, Table dialogs
  function showLinkDialog() {
    linkTextInput.value = '';
    linkUrlInput.value = 'https://';
    linkDialog.style.display = 'flex';
    function cleanup() {
      linkDialog.style.display = 'none';
      linkOkBtn.removeEventListener('click', onOk);
      linkCancelBtn.removeEventListener('click', onCancel);
    }
    function onOk() {
      const text = linkTextInput.value.trim() || 'link text';
      const url = linkUrlInput.value.trim() || '#';
      cleanup();
      if (cmEditor) {
        cmEditor.replaceSelection(`[${text}](${url})`);
        cmEditor.focus();
      }
    }
    function onCancel() { cleanup(); }
    linkOkBtn.addEventListener('click', onOk);
    linkCancelBtn.addEventListener('click', onCancel);
  }

  function showMediaDialog() {
    mediaAlt.value = '';
    mediaUrl.value = 'https://';
    mediaDialog.style.display = 'flex';
    function cleanup() {
      mediaDialog.style.display = 'none';
      mediaOk.removeEventListener('click', onOk);
      mediaCancel.removeEventListener('click', onCancel);
      mediaBrowse.removeEventListener('click', onBrowse);
    }
    function onOk() {
      const altText = mediaAlt.value.trim() || 'Image';
      let url = mediaUrl.value.trim() || '#';
      if (url.includes("github.com") && url.includes("/blob/")) {
        url = url.replace("github.com", "raw.githubusercontent.com").replace("/blob", "");
      }
      if (!/^https?:\/\//.test(url) && !url.startsWith('file://')) {
        url = 'https://' + url;
      }
      cleanup();
      if (cmEditor) {
        cmEditor.replaceSelection(`![${altText}](${url})`);
        cmEditor.focus();
      }
    }
    async function onBrowse() {
      try {
        const filePath = await ipcRenderer.invoke('open-file-dialog', {
          filters: [{ name: 'Images', extensions: ['png', 'jpg', 'jpeg', 'gif', 'svg'] }]
        });
        if (filePath) {
          mediaUrl.value = `file://${filePath}`;
        }
      } catch (err) {
        console.error('Error browsing for media:', err);
      }
    }
    function onCancel() { cleanup(); }
    mediaOk.addEventListener('click', onOk);
    mediaCancel.addEventListener('click', onCancel);
    mediaBrowse.addEventListener('click', onBrowse);
  }
  if (btnMedia) {
    btnMedia.addEventListener('click', showMediaDialog);
  }

  function showTableDialog() {
    tableRowsInput.value = '3';
    tableColsInput.value = '3';
    tableHeaderCheck.checked = true;
    tableDialog.style.display = 'flex';
    function cleanup() {
      tableDialog.style.display = 'none';
      tableOkBtn.removeEventListener('click', onOk);
      tableCancelBtn.removeEventListener('click', onCancel);
    }
    function onOk() {
      const rows = parseInt(tableRowsInput.value, 10) || 1;
      const cols = parseInt(tableColsInput.value, 10) || 1;
      const hasHeader = tableHeaderCheck.checked;
      cleanup();
      insertTable(rows, cols, hasHeader);
    }
    function onCancel() { cleanup(); }
    tableOkBtn.addEventListener('click', onOk);
    tableCancelBtn.addEventListener('click', onCancel);
  }

  function insertTable(rows, cols, hasHeader) {
    if (!cmEditor) return;
    let out = '';
    if (hasHeader) {
      let headerLine = '| ';
      let dashLine = '| ';
      for (let c = 1; c <= cols; c++) {
        headerLine += `Header${c} | `;
        dashLine += `--- | `;
      }
      out += headerLine.trim() + '\n' + dashLine.trim() + '\n';
      for (let r = 1; r < rows; r++) {
        let row = '| ';
        for (let c = 1; c <= cols; c++) {
          row += `data | `;
        }
        out += row.trim() + '\n';
      }
    } else {
      for (let r = 1; r <= rows; r++) {
        let row = '| ';
        for (let c = 1; c <= cols; c++) {
          row += `data | `;
        }
        out += row.trim() + '\n';
      }
    }
    cmEditor.replaceRange(out, cmEditor.getCursor());
    cmEditor.focus();
  }

  // Drag & Drop .md files
  document.addEventListener('dragover', (e) => { e.preventDefault(); });
  document.addEventListener('drop', (e) => {
    e.preventDefault();
    if (!e.dataTransfer?.files) return;
    const dropped = Array.from(e.dataTransfer.files);
    for (const f of dropped) {
      if (f.name.toLowerCase().endsWith('.md')) {
        loadFile(f.path);
      }
    }
  });

  // Format Buttons
  function wrapSelection(before, after = before) {
    if (!cmEditor) return;
    cmEditor.operation(() => {
      const sels = cmEditor.listSelections();
      for (const sel of sels) {
        let { anchor, head } = sel;
        if (anchor.line > head.line || (anchor.line === head.line && anchor.ch > head.ch)) {
          [anchor, head] = [head, anchor];
        }
        const text = cmEditor.getRange(anchor, head);
        cmEditor.replaceRange(`${before}${text}${after}`, anchor, head);
      }
    });
    cmEditor.focus();
  }

  btnBold?.addEventListener('click', () => wrapSelection('**'));
  btnItalic?.addEventListener('click', () => wrapSelection('*'));
  btnCode?.addEventListener('click', () => wrapSelection('`'));
  btnLink?.addEventListener('click', showLinkDialog);
  btnHeading?.addEventListener('click', () => {
    if (!cmEditor) return;
    cmEditor.operation(() => {
      cmEditor.listSelections().forEach(sel => {
        for (let line = sel.anchor.line; line <= sel.head.line; line++) {
          cmEditor.replaceRange('# ', { line, ch: 0 });
        }
      });
    });
    cmEditor.focus();
  });
  btnTable?.addEventListener('click', showTableDialog);

  alignLeftBtn?.addEventListener('click', () => alignSelection("left"));
  alignCenterBtn?.addEventListener('click', () => alignSelection("center"));
  alignRightBtn?.addEventListener('click', () => alignSelection("right"));

  if (githubMenuBtn) {
    githubMenuBtn.addEventListener('click', async () => {
      await ipcRenderer.invoke('open-github-window');
    });
  }

  minButton?.addEventListener('click', () => ipcRenderer.send('minimize-window'));
  maxButton?.addEventListener('click', () => ipcRenderer.send('maximize-window'));
  closeButton?.addEventListener('click', () => ipcRenderer.send('close-window'));

  newFileBtn?.addEventListener('click', async () => {
    const defaultName = `untitled-${Date.now()}.md`;
    const userFilename = await customPrompt('Enter file name:', defaultName);
    if (!userFilename) return;
    let finalName = userFilename;
    if (!/\.[Mm][Dd]$/.test(finalName)) {
      finalName += '.md';
    }
    const folder = userSettings.defaultFolder || process.cwd();
    const filePath = path.join(folder, finalName);
    try {
      await fsp.writeFile(filePath, '', 'utf8');
      createOrActivateTab(filePath, finalName, '');
      refreshFileList();
    } catch (err) {
      customAlert(`Failed to create file.\n${err.message}`);
    }
  });
  openFileBtn?.addEventListener('click', async () => {
    try {
      const chosen = await ipcRenderer.invoke('open-file-dialog');
      if (chosen) {
        loadFile(chosen);
      }
    } catch (err) {
      customAlert(`Failed to open file.\n${err.message}`);
    }
  });

  async function saveCurrentTab() {
    if (!activeTab) return;
    const tabObj = tabs.find(t => t.filePath === activeTab);
    if (!tabObj) return;
    if (cmEditor) {
      tabObj.content = cmEditor.getValue();
    }
    await saveSpecificTab(activeTab);
    refreshFileList();
  }
  saveFileBtn?.addEventListener('click', saveCurrentTab);

  renameFileBtn?.addEventListener('click', async () => {
    if (!activeTab) {
      customAlert('No file loaded to rename.');
      return;
    }
    const tabObj = tabs.find(t => t.filePath === activeTab);
    if (!tabObj) return;
    if (cmEditor) {
      tabObj.content = cmEditor.getValue();
    }
    const newName = await customPrompt('Enter the new file name:', tabObj.fileName);
    if (newName && newName !== tabObj.fileName) {
      const folder = path.dirname(tabObj.filePath);
      let finalName = newName;
      if (!/\.[Mm][Dd]$/.test(finalName)) {
        finalName += '.md';
      }
      const newPath = path.join(folder, finalName);
      try {
        await fsp.rename(tabObj.filePath, newPath);
        tabObj.filePath = newPath;
        tabObj.fileName = finalName;
        tabObj.originalContent = tabObj.content;
        tabObj.isDirty = false;
        refreshFileList();
        if (tabObj.tabEl) {
          tabObj.tabEl.querySelector('.tab-text').textContent = finalName;
        }
        customAlert('File renamed successfully.');
      } catch (err) {
        customAlert(`Failed to rename file.\n${err.message}`);
      }
    }
  });

  refreshFilesBtn?.addEventListener('click', refreshFileList);

  copyPreviewBtn?.addEventListener('click', () => {
    if (!cmEditor) return;
    const text = cmEditor.getValue();
    navigator.clipboard.writeText(text)
      .then(() => customAlert('Markdown source copied to clipboard.'))
      .catch(err => console.error('Error copying text:', err));
  });

  aboutBtn?.addEventListener('click', async () => {
    await ipcRenderer.invoke('open-about-window');
  });

  settingsBtn?.addEventListener('click', async () => {
    await ipcRenderer.invoke('open-settings-window');
  });

  btnSearch?.addEventListener('click', () => {
    document.getElementById('search-replace-bar').classList.toggle('hidden');
  });
  document.getElementById('search-close-btn')?.addEventListener('click', () => {
    document.getElementById('search-replace-bar').classList.add('hidden');
    clearSearchHighlights();
  });

  function clearSearchHighlights() {
    searchMarks.forEach(mark => mark.clear());
    searchMarks = [];
    currentSearchCursor = null;
    if (currentSearchMatch) {
      currentSearchMatch.clear();
      currentSearchMatch = null;
    }
  }

  function highlightAll(query) {
    clearSearchHighlights();
    if (!cmEditor || !query) return;
    const cursor = cmEditor.getSearchCursor(query, { line: 0, ch: 0 });
    while (cursor.findNext()) {
      const from = cursor.from();
      const to = cursor.to();
      const mark = cmEditor.markText(from, to, { className: 'cm-searching' });
      searchMarks.push(mark);
    }
  }

  function findNext(query) {
    if (!currentSearchCursor) {
      currentSearchCursor = cmEditor.getSearchCursor(query, { line: 0, ch: 0 });
    }
    if (currentSearchMatch) {
      currentSearchCursor = cmEditor.getSearchCursor(query, currentSearchMatch.to());
    }
    if (currentSearchCursor.findNext()) {
      const from = currentSearchCursor.from();
      const to = currentSearchCursor.to();
      if (currentSearchMatch) currentSearchMatch.clear();
      currentSearchMatch = cmEditor.markText(from, to, { className: 'cm-searching-active' });
      cmEditor.scrollIntoView({ from, to }, 60);
    }
  }

  document.getElementById('search-next-btn')?.addEventListener('click', () => {
    const query = document.getElementById('search-input').value;
    if (!query) return;
    if (!currentSearchCursor) highlightAll(query);
    findNext(query);
  });

  document.getElementById('search-replace-btn')?.addEventListener('click', () => {
    const query = document.getElementById('search-input').value;
    if (!query) return;
    if (!currentSearchCursor) {
      highlightAll(query);
      findNext(query);
      return;
    }
    if (!currentSearchMatch) {
      findNext(query);
      return;
    }
    const from = currentSearchCursor.from();
    const to = currentSearchCursor.to();
    const replacement = document.getElementById('replace-input').value;
    cmEditor.replaceRange(replacement, from, to);
    currentSearchMatch.clear();
    currentSearchMatch = null;
    highlightAll(query);
    findNext(query);
  });

  document.getElementById('search-replace-all-btn')?.addEventListener('click', () => {
    const query = document.getElementById('search-input').value;
    if (!query) return;
    const replacement = document.getElementById('replace-input').value;
    clearSearchHighlights();
    const cursor = cmEditor.getSearchCursor(query, { line: 0, ch: 0 });
    while (cursor.findNext()) {
      cursor.replace(replacement);
    }
    highlightAll(query);
  });

  // AI Tools: Summarize, Simplify, Headings
  if (document.getElementById('btn-summarize')) {
    document.getElementById('btn-summarize').addEventListener('click', async () => {
      const currentText = cmEditor.getValue();
      const summaryLines = await summarizeText(currentText);
      displayAiResults("Summary", summaryLines);
    });
  }
  if (document.getElementById('btn-simplify')) {
    document.getElementById('btn-simplify').addEventListener('click', async () => {
      const currentText = cmEditor.getValue();
      const simplifiedLines = await simplifyText(currentText);
      displayAiResults("Simplified Text", simplifiedLines);
    });
  }
  if (document.getElementById('btn-suggest-headings')) {
    document.getElementById('btn-suggest-headings').addEventListener('click', async () => {
      const currentText = cmEditor.getValue();
      const suggestions = await suggestHeadings(currentText);
      displayAiResults("Heading Suggestions", suggestions);
    });
  }

  // Additional Buttons
  if (btnPrint) {
    btnPrint.addEventListener('click', async () => {
      try {
        const result = await ipcRenderer.invoke('print-document');
        if (result.startsWith('error:') || result === 'no-main-window') {
          console.error("Print failed =>", result);
        } else {
          console.log("Printed or user canceled => no popup shown.");
        }
      } catch (err) {
        console.error("Print error =>", err);
      }
    });
  }

  if (btnExportPDF) {
    btnExportPDF.addEventListener('click', async () => {
      await exportCurrentTabToPDF();
    });
  }

  // Toggling button active state helper
  function setButtonActive(button, isActive) {
    if (!button) return;
    if (isActive) {
      button.classList.add('toggle-active');
    } else {
      button.classList.remove('toggle-active');
    }
  }

  if (btnToggleSpellcheck) {
    btnToggleSpellcheck.addEventListener('click', async () => {
      try {
        const newVal = await ipcRenderer.invoke('toggle-spellcheck');
        if (cmEditor) {
          cmEditor.setOption('spellcheck', newVal);
        }
        setButtonActive(btnToggleSpellcheck, newVal);
        console.log("Spellcheck =>", newVal ? "ON" : "OFF");
      } catch (err) {
        console.error("Toggle Spellcheck failed:", err);
      }
    });
  }

  if (btnThemeSwitch) {
    btnThemeSwitch.addEventListener('click', async () => {
      try {
        const newTheme = await ipcRenderer.invoke('switch-theme');
        if (cmEditor) {
          if (newTheme === 'light') {
            cmEditor.setOption('theme', 'default');
            document.body.style.backgroundColor = '#f0f0f0';
            setButtonActive(btnThemeSwitch, true);
          } else {
            cmEditor.setOption('theme', 'material-darker');
            document.body.style.backgroundColor = '#0b131a';
            setButtonActive(btnThemeSwitch, false);
          }
        }
        console.log("Theme =>", newTheme);
      } catch (err) {
        console.error("Switch Theme failed:", err);
      }
    });
  }

  // Init application
  (async () => {
    console.log("[DEBUG] init app...");
    try {
      userDataPath = await ipcRenderer.invoke('get-user-data-path');
    } catch (err) {
      console.error('Failed to get userData path:', err);
    }
    try {
      userSettings = await ipcRenderer.invoke('load-app-settings');
      console.log("[DEBUG] Loaded user settings:", userSettings);
    } catch (err) {
      console.error("Failed to load user settings:", err);
      userSettings = {};
    }
    loadNotes();
    initCodeMirror();
    refreshFileList();
    updatePreview();
    if (typeof userSettings.spellCheck === 'boolean') {
      cmEditor.setOption('spellcheck', userSettings.spellCheck);
      setButtonActive(btnToggleSpellcheck, userSettings.spellCheck);
    }
    if (userSettings.theme === 'light') {
      cmEditor.setOption('theme', 'default');
      document.body.style.backgroundColor = '#f0f0f0';
      setButtonActive(btnThemeSwitch, true);
    } else {
      cmEditor.setOption('theme', 'material-darker');
      document.body.style.backgroundColor = '#0b131a';
      setButtonActive(btnThemeSwitch, false);
    }
    if (userSettings.lastFile) {
      try {
        if (fs.existsSync(userSettings.lastFile)) {
          console.log("[DEBUG] Opening lastFile:", userSettings.lastFile);
          loadFile(userSettings.lastFile);
        }
      } catch (err) {
        console.log("[DEBUG] lastFile no longer exists:", err);
      }
    }
  })();

  // Insert GitHub Markdown globally
  window.insertGitHubMarkdown = function(markdown) {
    if (!cmEditor) {
      console.error("No cmEditor to insert GitHub markdown.");
      return;
    }
    const cur = cmEditor.getCursor();
    cmEditor.replaceRange('\n' + markdown + '\n', cur);
    cmEditor.focus();
    updatePreview();
  };
});
