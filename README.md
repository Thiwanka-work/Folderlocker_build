# FolderDoor (Folder Locker) 🔒

FolderDoor is a secure and beautifully designed Python application to lock and protect your private folders. 
It uses robust encryption to ensure your files remain inaccessible to unauthorized users and provides a seamless locking/unlocking experience through a modern, glassmorphism-inspired UI.

## Features ✨
- **Strong Encryption**: Uses the `cryptography` (Fernet) library to encrypt folder metadata and securely lock access.
- **Recovery Keys**: Automatically generates a secure recovery key when locking a folder, in case you forget your password.
- **Modern UI**: A sleek, dark-themed glassmorphism interface built with `flet`, complete with smooth lock/unlock animations.
- **Shortcut Integration**: Creates convenient folder shortcuts that seamlessly prompt for a password when trying to access the locked folder.

## Requirements 📦
- Python 3.8+
- `flet`
- `cryptography`
- `pywin32` (for Windows shortcut creation)

## Installation 🛠️
1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/Folderlocker.git
   cd Folderlocker_build
   ```
2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage 🚀
Run the application using Python:
```bash
python main.py
```

### How to Lock a Folder:
1. Click **Choose Folder** and select the directory you want to protect.
2. Enter a secure password.
3. Click **Lock Folder**.
4. Important: **Save the Recovery Key** shown in the dialog box! The original folder will be hidden and replaced with a locked shortcut.

### How to Unlock a Folder:
1. Double-click the locked folder shortcut (or open `main.py` and select the hidden folder).
2. Enter your password (or check "Use Recovery Key" and enter the recovery key).
3. Click **Unlock Folder**. The folder will be restored to its original state.

## Technologies Used 💻
- [Flet](https://flet.dev/) - For the beautiful desktop GUI.
- [Cryptography](https://cryptography.io/en/latest/) - For secure data encryption.
- [PyWin32](https://github.com/mhammond/pywin32) - Windows API integration for shortcuts and file attributes.

## Disclaimer ⚠️
This tool is for personal use to hide and lock folders. Please ensure you do not lose your recovery key or password, as the data cannot be recovered without them!
