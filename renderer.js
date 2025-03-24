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
  { text: '`Inline Code`', displayText: 'Inline Code' },
  { text: '```language\nCode Block\n```', displayText: 'Code Block' },
  { text: '> Blockquote', displayText: 'Blockquote' },
  { text: '- List Item', displayText: 'List Item' },
  { text: '1. Numbered List Item', displayText: 'Numbered List' },
  { text: '[Link Text](https://)', displayText: 'Link' },
  { text: '![Alt Text](image.jpg)', displayText: 'Image' },
  { text: '| Header1 | Header2 |\n| --- | --- |\n| Data1 | Data2 |', displayText: 'Table' }
];

// Provide CodeMirror hints from our snippet list
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

// Setup Marked
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

// Global State
let userDataPath = '';
let notes = [];
let tabs = [];
let activeTab = null;
let cmEditor = null;

// For searching
let searchMarks = [];
let currentSearchCursor = null;
let currentSearchMatch = null;

// We'll store user settings (including defaultFolder, lastFile) in this object
let userSettings = {};

// Markdownlint function
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

/**
 * Revised alignment function:
 * 1) Remove any existing <div style="text-align:..."> or <p align="..."> or <p style="text-align:...">
 * 2) Strip leading/trailing newlines from the selection, then merge internal newlines into single spaces.
 * 3) Wrap the entire snippet with:
 * 
 * <div style="text-align: alignment;">
 * 
 * snippet
 * </div>
 */
function alignSelection(alignment) {
  if (!cmEditor) return;

  cmEditor.operation(() => {
    const selections = cmEditor.listSelections();

    selections.forEach(sel => {
      let rawText = cmEditor.getRange(sel.anchor, sel.head);

      // If nothing was selected, select the entire current line
      if (!rawText.trim()) {
        const curLine = cmEditor.getCursor().line;
        rawText = cmEditor.getLine(curLine);
        sel = {
          anchor: { line: curLine, ch: 0 },
          head:   { line: curLine, ch: rawText.length }
        };
      }

      // 1) Remove any existing alignment wrappers:
      const wrapperRegex = /<(?:div|p)\s+(?:style="text-align:\s*[^"]+"\s*|align="[^"]+"\s*)(?:[^>]*)>([\s\S]*?)<\/(?:div|p)>/gi;
      let cleaned = rawText.replace(wrapperRegex, '$1');

      // 2) Trim leading/trailing newlines, then merge any internal newlines
      cleaned = cleaned.replace(/^\s+|\s+$/g, '');
      cleaned = cleaned.replace(/\r?\n\s*/g, ' ');

      // 3) Build final snippet with a blank line after the opening <div> and a closing </div>
      const finalText = `<div style="text-align: ${alignment};">\n\n${cleaned}\n</div>`;

      cmEditor.replaceRange(finalText, sel.anchor, sel.head);
    });
  });

  cmEditor.focus();
}


window.addEventListener('DOMContentLoaded', () => {
  console.log("[DEBUG] DOM loaded, hooking up events...");

  // DOM references
  const glassTabs      = document.getElementById('glass-tabs');
  const previewContent = document.getElementById('preview-content');
  const fileSearch     = document.getElementById('file-search');
  const fileList       = document.getElementById('file-list');
  const notesList      = document.getElementById('notes-list');
  const newNoteInput   = document.getElementById('new-note-input');
  const statusWordCount= document.getElementById('word-count');
  const statusReadTime = document.getElementById('read-time');

  // Single prompt
  const customPromptEl = document.getElementById('custom-prompt');
  const promptMessageEl= customPromptEl.querySelector('.prompt-message');
  const promptInputEl  = document.getElementById('prompt-input');
  const promptOkBtn    = document.getElementById('prompt-ok');
  const promptCancelBtn= document.getElementById('prompt-cancel');

  // Link dialog
  const linkDialog    = document.getElementById('link-dialog');
  const linkTextInput = document.getElementById('link-text');
  const linkUrlInput  = document.getElementById('link-url');
  const linkOkBtn     = document.getElementById('link-ok');
  const linkCancelBtn = document.getElementById('link-cancel');

  // Table dialog
  const tableDialog      = document.getElementById('table-dialog');
  const tableRowsInput   = document.getElementById('table-rows');
  const tableColsInput   = document.getElementById('table-cols');
  const tableHeaderCheck = document.getElementById('table-header');
  const tableOkBtn       = document.getElementById('table-ok');
  const tableCancelBtn   = document.getElementById('table-cancel');

  // Media insertion wizard
  const mediaDialog = document.getElementById('media-dialog');
  const mediaAlt = document.getElementById('media-alt');
  const mediaUrl = document.getElementById('media-url');
  const mediaOk = document.getElementById('media-ok');
  const mediaCancel = document.getElementById('media-cancel');
  const mediaBrowse = document.getElementById('media-browse');

  // Minimal table WYSIWYG
  const tableEditorPanel = document.getElementById('table-editor-panel');
  const addRowBtn        = document.getElementById('table-add-row');
  const removeRowBtn     = document.getElementById('table-remove-row');
  const addColBtn        = document.getElementById('table-add-col');
  const removeColBtn     = document.getElementById('table-remove-col');

  // Save Changes 3-Button Prompt
  const saveChangesDialog   = document.getElementById('save-changes-dialog');
  const saveChangesFilename = document.getElementById('save-changes-filename');
  const saveChangesSaveBtn  = document.getElementById('save-changes-save-btn');
  const saveChangesDontBtn  = document.getElementById('save-changes-dontsave-btn');
  const saveChangesCancelBtn= document.getElementById('save-changes-cancel-btn');

  // Window controls & file tools
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

  // Format buttons
  const btnBold    = document.getElementById('btn-bold');
  const btnItalic  = document.getElementById('btn-italic');
  const btnCode    = document.getElementById('btn-code');
  const btnLink    = document.getElementById('btn-link');
  const btnHeading = document.getElementById('btn-heading');
  const btnTable   = document.getElementById('btn-table');
  const btnMedia   = document.getElementById('btn-media');

  // Search & Replace
  const searchBar           = document.getElementById('search-replace-bar');
  const searchInput         = document.getElementById('search-input');
  const replaceInput        = document.getElementById('replace-input');
  const searchNextBtn       = document.getElementById('search-next-btn');
  const searchReplaceBtn    = document.getElementById('search-replace-btn');
  const searchReplaceAllBtn = document.getElementById('search-replace-all-btn');
  const searchCloseBtn      = document.getElementById('search-close-btn');
  const btnSearch           = document.getElementById('btn-search');

  // Alignment Buttons
  const alignLeftBtn   = document.getElementById('align-left');
  const alignCenterBtn = document.getElementById('align-center');
  const alignRightBtn  = document.getElementById('align-right');

  // GitHub menu button
  const githubMenuBtn = document.getElementById('github-menu');

  // View mode references (titlebar icons)
  const editorContainer  = document.getElementById('editor-container');
  const previewContainer = document.getElementById('preview-container');
  const btnEditorOnly    = document.getElementById('btn-editor-only');
  const btnSplitView     = document.getElementById('btn-split-view');
  const btnPreviewOnly   = document.getElementById('btn-preview-only');

  // Context Menu for Project Files
  const fileContextMenu = document.getElementById('file-context-menu');
  let fileContextMenuTargetPath = null;

  // Hide context menu on any left-click
  document.addEventListener('click', () => {
    fileContextMenu.style.display = 'none';
  });

  // Right-click on file list
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

  // Insert GitHub Markdown (IPC from main)
  ipcRenderer.on('insert-github-markdown', (event, markdown) => {
    if (typeof window.insertGitHubMarkdown === 'function') {
      window.insertGitHubMarkdown(markdown);
    } else {
      console.error("insertGitHubMarkdown is not defined.");
    }
  });

  // Show yes/cancel for file deletion etc.
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
      function onYes() {
        cleanup('yes');
      }
      function onCancel() {
        cleanup('cancel');
      }

      promptOkBtn.addEventListener('click', onYes);
      promptCancelBtn.addEventListener('click', onCancel);
    });
  }

  // View mode
  btnEditorOnly?.addEventListener('click', () => {
    editorContainer.style.display = 'flex';
    previewContainer.style.display = 'none';
  });
  btnSplitView?.addEventListener('click', () => {
    editorContainer.style.display = 'flex';
    previewContainer.style.display = 'flex';
  });
  btnPreviewOnly?.addEventListener('click', () => {
    editorContainer.style.display = 'none';
    previewContainer.style.display = 'flex';
  });

  // Dirty Save Logic (app close)
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
      function onSave()  { cleanup('save');     }
      function onDont()  { cleanup('dontsave'); }
      function onCancel() { cleanup('cancel');  }

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

    // pinned first, completed last
    const sorted = notes.slice().sort((a,b) => {
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

  // Add note
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

  // Load last file logic
  async function rememberLastFile(filePath) {
    userSettings.lastFile = filePath;
    try {
      await ipcRenderer.invoke('save-app-settings', userSettings);
      console.log("[DEBUG] rememberLastFile => saved lastFile:", filePath);
    } catch (err) {
      console.error("[DEBUG] Failed to save lastFile:", err);
    }
  }

  // File browser
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

  // TABS + Dirty Save
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
        oldTab.isDirty = (oldTab.content !== oldTab.originalContent);
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

  // CodeMirror init
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

    // Scroll sync
    cmEditor.on('scroll', () => {
      const info = cmEditor.getScrollInfo();
      const ratio = info.top / (info.height - info.clientHeight);
      const previewMax = previewContent.scrollHeight - previewContent.clientHeight;
      previewContent.scrollTop = ratio * previewMax;
    });

    // Table detection
    cmEditor.on('cursorActivity', updateTableEditorVisibility);

    // Auto-completion & snippet insertion
    cmEditor.on('keyup', (cm, event) => {
      if ((event.ctrlKey || event.metaKey) && event.keyCode === 32) {
        if (cm.showHint) {
          cm.showHint({ hint: provideHint, completeSingle: false });
        }
      }
    });
  }

  // Preview & Status
  function updatePreview() {
    if (!cmEditor) return;
    const markdownText = cmEditor.getValue();
    previewContent.innerHTML = marked.parse(markdownText);
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
      statusReadTime.textContent  = 'Read Time: 0 min';
      return;
    }
    const text = cmEditor.getValue().trim();
    const words = text.split(/\s+/).filter(w => w.length > 0).length;
    const readTime = Math.ceil(words / 200);
    statusWordCount.textContent = `Words: ${words}`;
    statusReadTime.textContent  = `Read Time: ${readTime} min`;
  }

  // Table Editor
  function updateTableEditorVisibility() {
    if (!cmEditor) return;
    const lineText = cmEditor.getLine(cmEditor.getCursor().line);
    if (lineText.includes('|')) {
      tableEditorPanel.style.display = 'flex';
    } else {
      tableEditorPanel.style.display = 'none';
    }
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
    const tableText = cmEditor.getRange(
      { line: startLine, ch: 0 },
      { line: endLine + 1, ch: 0 }
    );
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
    const { startLine, endLine, tableText } = block;
    let rows = parseTable(tableText);
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
    const { startLine, endLine, tableText } = block;
    let rows = parseTable(tableText);
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
    const { startLine, endLine, tableText } = block;
    let rows = parseTable(tableText);
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
    const { startLine, endLine, tableText } = block;
    let rows = parseTable(tableText);
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

  // Link Dialog
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
      const url  = linkUrlInput.value.trim() || '#';
      cleanup();
      if (cmEditor) {
        cmEditor.replaceSelection(`[${text}](${url})`);
        cmEditor.focus();
      }
    }
    function onCancel() {
      cleanup();
    }
    linkOkBtn.addEventListener('click', onOk);
    linkCancelBtn.addEventListener('click', onCancel);
  }

  // Media Wizard
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

      // Convert GitHub file URLs to raw URLs if needed
      if (url.includes("github.com") && url.includes("/blob/")) {
        url = url.replace("github.com", "raw.githubusercontent.com").replace("/blob", "");
      }
      // Ensure URL starts with "http", "https", or "file://"
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

    function onCancel() {
      cleanup();
    }

    mediaOk.addEventListener('click', onOk);
    mediaCancel.addEventListener('click', onCancel);
    mediaBrowse.addEventListener('click', onBrowse);
  }
  if (btnMedia) {
    btnMedia.addEventListener('click', showMediaDialog);
  }

  // Table Dialog
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
    function onCancel() {
      cleanup();
    }
    tableOkBtn.addEventListener('click', onOk);
    tableCancelBtn.addEventListener('click', onCancel);
  }

  function insertTable(rows, cols, hasHeader) {
    if (!cmEditor) return;
    let out = '';
    if (hasHeader) {
      let headerLine = '| ';
      let dashLine   = '| ';
      for (let c = 1; c <= cols; c++) {
        headerLine += `Header${c} | `;
        dashLine   += `--- | `;
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
    cmEditor.replaceSelection(out);
    cmEditor.focus();
  }

  // DRAG & DROP .md
  document.addEventListener('dragover', (e) => {
    e.preventDefault();
  });
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

  // Format buttons
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

  // Alignment
  alignLeftBtn?.addEventListener('click', () => alignSelection("left"));
  alignCenterBtn?.addEventListener('click', () => alignSelection("center"));
  alignRightBtn?.addEventListener('click', () => alignSelection("right"));

  // GitHub menu
  if (githubMenuBtn) {
    githubMenuBtn.addEventListener('click', async () => {
      await ipcRenderer.invoke('open-github-window');
    });
  }

  // Window controls & file tools
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

  // Search & Replace
  btnSearch?.addEventListener('click', () => {
    searchBar.classList.toggle('hidden');
  });

  searchCloseBtn?.addEventListener('click', () => {
    searchBar.classList.add('hidden');
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

  searchNextBtn?.addEventListener('click', () => {
    const query = searchInput.value;
    if (!query) return;
    if (!currentSearchCursor) highlightAll(query);
    findNext(query);
  });

  searchReplaceBtn?.addEventListener('click', () => {
    const query = searchInput.value;
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
    const to   = currentSearchCursor.to();
    const replacement = replaceInput.value;
    cmEditor.replaceRange(replacement, from, to);
    currentSearchMatch.clear();
    currentSearchMatch = null;
    highlightAll(query);
    findNext(query);
  });

  searchReplaceAllBtn?.addEventListener('click', () => {
    const query = searchInput.value;
    if (!query) return;
    const replacement = replaceInput.value;
    clearSearchHighlights();
    const cursor = cmEditor.getSearchCursor(query, { line: 0, ch: 0 });
    while (cursor.findNext()) {
      cursor.replace(replacement);
    }
    highlightAll(query);
  });

  // Init
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

  // Provide a global function to insert GitHub markdown on a new line
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
