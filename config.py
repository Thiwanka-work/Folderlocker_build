import json
import os

CONFIG_FILE = "settings.json"

def get_default_settings():
    return {
        "auto_lock": False,
        "windows_hello": False,
        "intruder_alert": False,
        "decoy_password": "",
        "locked_folders": []
    }

def load_settings():
    if not os.path.exists(CONFIG_FILE):
        return get_default_settings()
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Ensure all keys exist
            defaults = get_default_settings()
            for key in defaults:
                if key not in data:
                    data[key] = defaults[key]
            return data
    except Exception:
        return get_default_settings()

def save_settings(settings):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(settings, f, indent=4)

def add_folder(folder_path):
    settings = load_settings()
    if folder_path not in settings["locked_folders"]:
        settings["locked_folders"].append(folder_path)
        save_settings(settings)

def remove_folder(folder_path):
    settings = load_settings()
    if folder_path in settings["locked_folders"]:
        settings["locked_folders"].remove(folder_path)
        save_settings(settings)
