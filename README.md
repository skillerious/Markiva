<p align="center">
  <img src="https://github.com/skillerious/Markiva/blob/main/assets/MarkivaLogo%20(1).png" alt="Markiva Logo" style="width:200px;"/>
</p>

<h1 align="center">Markiva v3.0 – Now Powered by Electron ⚡</h1>

Markiva has undergone a transformative update! We've officially moved away from our previous Python-based foundation and fully embraced **Electron**, delivering a sleek, fast, and modern markdown editing experience across platforms.

---

## 🚀 Highlights of v3.0

- ✅ **Electron-based**: Seamless cross-platform experience with modern performance.
- ✅ **Multi-tab support**: Edit multiple markdown files with glass-style tab navigation.
- ✅ **Split, Editor-Only, and Preview-Only Views**: Toggle between layouts like in VS Code.
- ✅ **Live Preview Sync**: See changes reflected instantly as you type.
- ✅ **Persistent Notes & Last Session Resume**: Never lose your place or notes.
- ✅ **Drag-and-drop file loading** with support for `.md` files.
- ✅ **Modern UI with Themes**: Refined interface with a professional, glass-like aesthetic.
- ✅ **Powerful Find & Replace**: Includes Regex, Replace All, and inline highlights.
- ✅ **File Operations**: Create, rename, and delete files directly from the integrated explorer.

---

## 📥 Download

Get the latest release from the [Releases Page](https://github.com/skillerious/Markiva/releases/tag/MarkivaV3)

---

## 📸 Screenshots

| Feature | Screenshot |
|--------|------------|
| **Main App Interface** | ![Main](https://github.com/skillerious/Markiva/blob/main/screenshots/Screenshot%202025-03-22%20201331.png) |
| **Settings Modal** | ![Settings](https://github.com/skillerious/Markiva/blob/main/screenshots/Screenshot%202025-03-22%20201343.png) |
| **Find & Replace** | ![FindReplace](https://github.com/skillerious/Markiva/blob/main/screenshots/Screenshot%202025-03-22%20201355.png) |
| **View Mode Toggle (Editor, Split, Preview)** | ![ViewToggle](https://github.com/skillerious/Markiva/blob/main/screenshots/Screenshot%202025-03-22%20201404.png) |
| **Notes Sidebar** | ![Notes](https://github.com/skillerious/Markiva/blob/main/screenshots/Screenshot%202025-03-22%20201435.png) |

---

## 🔧 How to Run via VS Code

1. **Clone the repository**:
   ```bash
   git clone https://github.com/skillerious/Markiva.git
   cd Markiva
   ```

2. **Install dependencies**:
   ```bash
   npm install
   ```

3. **Start the app**:
   ```bash
   npm start
   ```

> 💡 Tip: Use VS Code’s built-in terminal and debugger for quick development cycles.

---

## ✨ Features in Detail

### 🔄 View Modes (Like VS Code)
Switch between:
- 📝 **Editor only**
- 🔍 **Preview only**
- 🖥️ **Split view** (editor + preview side by side)

### 🧠 Smart Markdown Editor
- CodeMirror 5 powered
- Line numbering and spell check
- Live syncing with preview
- Enhanced table editing toolbar

### 🗂️ File Browser
- Drag-and-drop markdown files
- Right-click menu to rename/delete
- Visual feedback for file interactions

### 📝 Sticky Notes Pane
- Add/remove/pin/complete notes
- All notes persist via local JSON
- Beautiful empty-state visuals

### 🔍 Search & Replace
- Highlighted results
- Inline replace or replace all
- Supports complex regex

### 📥 File Save Prompts
- On app close, you’ll be prompted to save unsaved files
- Graceful dirty file handling

### ⚙️ Custom Settings Dialog
- Launch via the settings gear icon
- Modify themes, font, and other preferences
- Modal and non-dismissible for clarity

---

## 🔐 Auto-Save & Restore

Markiva saves your **last opened tab** and restores it automatically on the next launch. Your notes and editor layout are also remembered for a seamless experience.

---

## 📌 Planned Features

- GitHub markdown flavor toggle
- Template manager
- HTML and PDF export
- Plugin support

---

## 🧪 Tech Stack

- **Electron** – Cross-platform desktop app framework
- **CodeMirror 5** – Markdown editor
- **Marked.js** – Markdown parser
- **Highlight.js** – Syntax highlighter
- **Font Awesome** – Icons
- **Node.js / FS** – File I/O
- **Vanilla JS / HTML / CSS** – Clean and minimal front-end

---

## 💬 Contributing

We welcome feedback, ideas, and PRs!  
Open issues for bugs or feature requests. Let’s build Markiva together.

---

## 📄 License

[MIT License](LICENSE)

---

<p align="center"><strong>🛠️ Built with love by Robin Doak</strong></p>
