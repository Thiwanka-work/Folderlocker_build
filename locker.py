import os
import sys
import base64
import json
import win32com.client
import ctypes
import random
import string
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

def _refresh_explorer():
    if os.name == 'nt':
        ctypes.windll.shell32.SHChangeNotify(0x08000000, 0x0000, None, None)

def _get_key(password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=480000,
    )
    return base64.urlsafe_b64encode(kdf.derive(password.encode()))

def _create_shortcut(target_path, link_path, arguments="", icon_location=r"C:\Users\2021icts36\Desktop\Folderlocker_build\Folderlocker\Folderlocker.ico"):
    shell = win32com.client.Dispatch("WScript.Shell")
    shortcut = shell.CreateShortCut(link_path)
    shortcut.TargetPath = target_path
    shortcut.Arguments = arguments
    shortcut.IconLocation = icon_location
    shortcut.WorkingDirectory = os.path.dirname(target_path)
    shortcut.Save()

def get_hidden_folder_path(folder_path: str) -> str:
    """Returns the expected hidden folder path given the original folder path."""
    original_name = os.path.basename(folder_path)
    parent_dir = os.path.dirname(folder_path)
    return os.path.join(parent_dir, f".{original_name}_locked")

def _generate_recovery_key():
    parts = [''.join(random.choices(string.ascii_uppercase + string.digits, k=4)) for _ in range(4)]
    return '-'.join(parts)

def lock_folder(folder_path: str, password: str, progress_callback=None):
    if not os.path.exists(folder_path):
        raise FileNotFoundError("Folder does not exist")
    
    metadata_path = os.path.join(folder_path, ".locker_metadata")
    if os.path.exists(metadata_path):
        raise ValueError("Folder is already locked")
    
    salt = os.urandom(16)
    master_key = Fernet.generate_key()
    fernet_master = Fernet(master_key)
    
    user_key = _get_key(password, salt)
    fernet_user = Fernet(user_key)
    
    recovery_key = _generate_recovery_key()
    recovery_derived_key = _get_key(recovery_key, salt)
    fernet_recovery = Fernet(recovery_derived_key)
    
    # Encrypt the master key twice
    encrypted_master_key_user = fernet_user.encrypt(master_key)
    encrypted_master_key_recovery = fernet_recovery.encrypt(master_key)
    
    # Encrypt all files
    files_to_encrypt = []
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if file == ".locker_metadata":
                continue
            files_to_encrypt.append(os.path.join(root, file))
            
    total_files = len(files_to_encrypt)
    for i, file_path in enumerate(files_to_encrypt):
        if progress_callback:
            progress_callback(i, total_files)
        try:
            with open(file_path, "rb") as f:
                data = f.read()
            encrypted_data = fernet_master.encrypt(data)
            with open(file_path, "wb") as f:
                f.write(encrypted_data)
            os.rename(file_path, file_path + ".locked")
        except Exception as e:
            print(f"Error encrypting {file_path}: {e}")
            
    if progress_callback:
        progress_callback(total_files, total_files)

    # Save metadata
    verification_token = fernet_master.encrypt(b"VERIFIED")
    metadata = {
        "salt": base64.b64encode(salt).decode('utf-8'),
        "verification": verification_token.decode('utf-8'),
        "master_key_user": encrypted_master_key_user.decode('utf-8'),
        "master_key_recovery": encrypted_master_key_recovery.decode('utf-8')
    }
    with open(metadata_path, "w") as f:
        json.dump(metadata, f)
        
    hidden_folder_path = get_hidden_folder_path(folder_path)
    os.rename(folder_path, hidden_folder_path)
    if os.name == 'nt':
        os.system(f'attrib +h +s "{hidden_folder_path}"')
        
    original_name = os.path.basename(folder_path)
    parent_dir = os.path.dirname(folder_path)
    shortcut_path = os.path.join(parent_dir, f"{original_name}.lnk")
    
    if getattr(sys, 'frozen', False):
        exe_path = sys.executable
        arguments = f'"{hidden_folder_path}"'
    else:
        exe_path = sys.executable.replace("python.exe", "pythonw.exe")
        main_script = os.path.abspath(sys.argv[0])
        arguments = f'"{main_script}" "{hidden_folder_path}"'
        
    _create_shortcut(exe_path, shortcut_path, arguments)
    _refresh_explorer()
    
    return recovery_key

def unlock_folder(hidden_folder_path: str, password_or_recovery: str, is_recovery: bool = False, progress_callback=None):
    if not os.path.exists(hidden_folder_path):
        raise FileNotFoundError("Hidden locked folder not found.")
        
    metadata_path = os.path.join(hidden_folder_path, ".locker_metadata")
    if not os.path.exists(metadata_path):
        raise ValueError("Folder is not locked or metadata is missing")
    
    with open(metadata_path, "r") as f:
        metadata = json.load(f)
    
    salt = base64.b64decode(metadata["salt"])
    
    derived_key = _get_key(password_or_recovery, salt)
    fernet_outer = Fernet(derived_key)
    
    try:
        if is_recovery:
            encrypted_master = metadata["master_key_recovery"].encode('utf-8')
        else:
            encrypted_master = metadata["master_key_user"].encode('utf-8')
            
        master_key = fernet_outer.decrypt(encrypted_master)
    except Exception:
        raise ValueError("Invalid password or recovery key!")
        
    fernet_master = Fernet(master_key)
    
    try:
        verification_token = metadata["verification"].encode('utf-8')
        decrypted_token = fernet_master.decrypt(verification_token)
        if decrypted_token != b"VERIFIED":
            raise ValueError("Verification failed!")
    except Exception:
        raise ValueError("Verification failed!")
        
    files_to_decrypt = []
    for root, dirs, files in os.walk(hidden_folder_path):
        for file in files:
            if file == ".locker_metadata":
                continue
            if file.endswith(".locked"):
                files_to_decrypt.append(os.path.join(root, file))
                
    total_files = len(files_to_decrypt)
    for i, file_path in enumerate(files_to_decrypt):
        if progress_callback:
            progress_callback(i, total_files)
        try:
            with open(file_path, "rb") as f:
                data = f.read()
            decrypted_data = fernet_master.decrypt(data)
            original_file_path = file_path[:-7]
            with open(original_file_path, "wb") as f:
                f.write(decrypted_data)
            os.remove(file_path)
        except Exception as e:
            print(f"Error decrypting {file_path}: {e}")

    if progress_callback:
        progress_callback(total_files, total_files)

    if os.name == 'nt':
        os.system(f'attrib -h -s "{hidden_folder_path}"')
    os.remove(metadata_path)
    
    original_name = os.path.basename(hidden_folder_path)
    if original_name.startswith(".") and original_name.endswith("_locked"):
        original_name = original_name[1:-7]
        
    parent_dir = os.path.dirname(hidden_folder_path)
    original_folder_path = os.path.join(parent_dir, original_name)
    os.rename(hidden_folder_path, original_folder_path)
    
    shortcut_path = os.path.join(parent_dir, f"{original_name}.lnk")
    if os.path.exists(shortcut_path):
        os.remove(shortcut_path)
        
    _refresh_explorer()
    return original_folder_path

def is_locked(folder_path: str) -> bool:
    if os.path.basename(folder_path).startswith(".") and os.path.basename(folder_path).endswith("_locked"):
        metadata_path = os.path.join(folder_path, ".locker_metadata")
        return os.path.exists(metadata_path)
        
    hidden_path = get_hidden_folder_path(folder_path)
    metadata_path = os.path.join(hidden_path, ".locker_metadata")
    return os.path.exists(metadata_path)
