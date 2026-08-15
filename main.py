import flet as ft
import locker
import sys
import os
import tkinter as tk
from tkinter import filedialog
import threading
import time
import config
import keyring
import flet_dropzone as ftd

# Setup Intruders dir
if not os.path.exists("Intruders"):
    os.makedirs("Intruders")

def border_all(width, color):
    bs = ft.BorderSide(width, color)
    return ft.Border(top=bs, right=bs, bottom=bs, left=bs)

def get_icon_path():
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
        return os.path.join(base_path, "Folderlocker.ico")
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(current_dir, "Folderlocker.ico"),
        os.path.join(current_dir, "Folderlocker", "Folderlocker.ico"),
        os.path.join(current_dir, "Folderlocker.png"),
        os.path.join(current_dir, "Folderlocker", "Folderlocker.png")
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return os.path.join(current_dir, "Folderlocker.ico")

def trigger_intruder_alert():
    def capture():
        try:
            import cv2
            cap = cv2.VideoCapture(0)
            ret, frame = cap.read()
            if ret:
                filename = f"Intruders/intruder_{int(time.time())}.jpg"
                cv2.imwrite(filename, frame)
            cap.release()
        except Exception as e:
            print("Intruder capture failed:", e)
    threading.Thread(target=capture, daemon=True).start()

def windows_hello_auth():
    try:
        import ctypes
        from ctypes import wintypes
        
        CREDUIWIN_GENERIC = 0x1
        CREDUIWIN_ENUMERATE_CURRENT_USER = 0x200
        
        class CREDUI_INFO(ctypes.Structure):
            _fields_ = [
                ("cbSize", wintypes.DWORD),
                ("hwndParent", wintypes.HWND),
                ("pszMessageText", wintypes.LPCWSTR),
                ("pszCaptionText", wintypes.LPCWSTR),
                ("hbmBanner", wintypes.HBITMAP),
            ]
        
        info = CREDUI_INFO()
        info.cbSize = ctypes.sizeof(CREDUI_INFO)
        info.hwndParent = None
        info.pszMessageText = "Please authenticate to unlock FolderDoor"
        info.pszCaptionText = "FolderDoor Security"
        info.hbmBanner = None
        
        auth_package = wintypes.ULONG(0)
        auth_buffer = ctypes.c_void_p()
        auth_buffer_size = wintypes.ULONG(0)
        save = wintypes.BOOL(False)
        
        credui = ctypes.windll.credui
        result = credui.CredUIPromptForWindowsCredentialsW(
            ctypes.byref(info),
            0,
            ctypes.byref(auth_package),
            None,
            0,
            ctypes.byref(auth_buffer),
            ctypes.byref(auth_buffer_size),
            ctypes.byref(save),
            CREDUIWIN_GENERIC | CREDUIWIN_ENUMERATE_CURRENT_USER
        )
        
        if auth_buffer:
            ctypes.windll.ole32.CoTaskMemFree(auth_buffer)
            
        return result == 0
    except Exception as e:
        print("Windows Hello failed:", e)
        return False

# Global state
unlocked_folders = {} # path: password
last_activity_time = time.time()

def auto_lock_thread():
    global last_activity_time, unlocked_folders
    while True:
        time.sleep(10)
        settings = config.load_settings()
        if not settings.get("auto_lock"):
            continue
            
        if time.time() - last_activity_time > 600: # 10 mins idle
            # Need to re-lock
            folders_to_lock = list(unlocked_folders.items())
            for folder, pwd in folders_to_lock:
                try:
                    locker.lock_folder(folder, pwd)
                    del unlocked_folders[folder]
                except Exception as e:
                    print(f"Auto-lock failed for {folder}: {e}")

# Start background thread
threading.Thread(target=auto_lock_thread, daemon=True).start()


def main(page: ft.Page):
    global last_activity_time
    
    # Update activity on interactions
    def update_activity(e=None):
        global last_activity_time
        last_activity_time = time.time()

    page.on_keyboard_event = update_activity
    
    # Window setup
    page.title = "FolderDoor"
    page.window.width = 450
    page.window.height = 700
    page.window.resizable = False
    page.padding = 0
    page.theme_mode = ft.ThemeMode.DARK
    
    icon_path = get_icon_path()
    if os.path.exists(icon_path):
        page.window.icon = icon_path
        
    direct_folder = sys.argv[1] if len(sys.argv) > 1 else None
    
    selected_folder = direct_folder
    is_locked = False
    failed_attempts = 0

    # --- HOME VIEW ---
    app_logo_img = ft.Image(
        src=get_icon_path(),
        width=95,
        height=95,
        border_radius=48,
        fit="cover",
    )
    
    status_icon = ft.Icon(
        icon=ft.Icons.LOCK_OPEN_ROUNDED,
        size=18,
        color=ft.Colors.GREEN_400,
        scale=1.0,
        animate_scale=ft.Animation(500, ft.AnimationCurve.ELASTIC_OUT),
    )
    
    status_badge = ft.Container(
        content=status_icon,
        width=32,
        height=32,
        border_radius=16,
        bgcolor=ft.Colors.BLUE_GREY_900,
        border=border_all(1.5, ft.Colors.CYAN_300),
        alignment=ft.Alignment(0, 0),
    )
    
    logo_stack = ft.Stack(
        [
            app_logo_img,
            ft.Container(
                content=status_badge,
                alignment=ft.Alignment(0.95, 0.95),
                width=100,
                height=100,
            )
        ],
        width=100,
        height=100,
    )
    
    logo_container = ft.Container(
        content=logo_stack,
        width=130,
        height=130,
        alignment=ft.Alignment(0, 0),
        border_radius=65,
        gradient=ft.LinearGradient(
            begin=ft.Alignment(-1.0, -1.0),
            end=ft.Alignment(1.0, 1.0),
            colors=[ft.Colors.with_opacity(0.2, ft.Colors.CYAN_400), ft.Colors.with_opacity(0.05, ft.Colors.WHITE)],
        ),
        border=border_all(1.5, ft.Colors.with_opacity(0.4, ft.Colors.CYAN_300)),
        shadow=ft.BoxShadow(spread_radius=4, blur_radius=20, color=ft.Colors.with_opacity(0.35, ft.Colors.CYAN_900)),
        margin=ft.Margin(left=0, top=25, right=0, bottom=15)
    )
    
    title_text = ft.Text("FolderDoor", size=32, weight=ft.FontWeight.W_900, color=ft.Colors.WHITE)
    subtitle_text = ft.Text("Secure your private files", size=14, color=ft.Colors.WHITE70, italic=True)
    
    folder_icon_large = ft.Icon(ft.Icons.CLOUD_UPLOAD_ROUNDED, size=40, color=ft.Colors.CYAN_300)
    folder_text = ft.Text("Drag & Drop Folder Here", color=ft.Colors.WHITE70, size=16, text_align=ft.TextAlign.CENTER, weight=ft.FontWeight.W_500)
    
    password_field = ft.TextField(
        label="Enter Password", 
        password=True, 
        can_reveal_password=True,
        width=320,
        prefix_icon=ft.Icons.LOCK_OUTLINE,
        border_color=ft.Colors.with_opacity(0.5, ft.Colors.WHITE),
        focused_border_color=ft.Colors.CYAN_300,
        color=ft.Colors.WHITE,
        bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.WHITE),
        border_radius=12,
        on_change=update_activity
    )
    
    recovery_checkbox = ft.Checkbox(label="Use Recovery Key", visible=False, fill_color=ft.Colors.CYAN_500, on_change=update_activity)
    progress_bar = ft.ProgressBar(width=320, value=0, visible=False, color=ft.Colors.CYAN_400, bgcolor=ft.Colors.with_opacity(0.2, ft.Colors.WHITE))
    
    action_button = ft.ElevatedButton(
        "Lock / Unlock",
        disabled=True,
        width=320,
        height=55,
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=12),
            bgcolor=ft.Colors.CYAN_600,
            color=ft.Colors.WHITE,
            elevation=8,
            shadow_color=ft.Colors.CYAN_900,
            animation_duration=300
        )
    )
    
    hello_button = ft.ElevatedButton(
        "Unlock with Windows Hello",
        icon=ft.Icons.FINGERPRINT,
        visible=False,
        width=320,
        height=45,
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=12),
            bgcolor=ft.Colors.BLUE_800,
            color=ft.Colors.WHITE,
        )
    )

    def play_lock_animation(locked: bool):
        status_icon.scale = 1.4
        page.update()
        time.sleep(0.3)
        if locked:
            status_icon.icon = ft.Icons.LOCK_ROUNDED
            status_icon.color = ft.Colors.RED_400
            status_badge.border = border_all(1.5, ft.Colors.RED_400)
            logo_container.border = border_all(1.5, ft.Colors.with_opacity(0.4, ft.Colors.RED_400))
        else:
            status_icon.icon = ft.Icons.LOCK_OPEN_ROUNDED
            status_icon.color = ft.Colors.GREEN_400
            status_badge.border = border_all(1.5, ft.Colors.GREEN_400)
            logo_container.border = border_all(1.5, ft.Colors.with_opacity(0.4, ft.Colors.CYAN_300))
        status_icon.scale = 1.0
        page.update()

    def update_ui_state():
        nonlocal is_locked
        update_activity()
        
        if selected_folder:
            config.add_folder(selected_folder)
            folder_name = os.path.basename(selected_folder)
            if len(folder_name) > 25: 
                folder_name = "..." + folder_name[-25:]
            folder_text.value = folder_name
            folder_text.size = 20
            folder_text.color = ft.Colors.CYAN_100
            folder_icon_large.icon = ft.Icons.FOLDER_SPECIAL_ROUNDED
            
            is_locked = locker.is_locked(selected_folder)
            
            if is_locked:
                status_icon.icon = ft.Icons.LOCK_ROUNDED
                status_icon.color = ft.Colors.RED_400
                status_badge.border = border_all(1.5, ft.Colors.RED_400)
                logo_container.border = border_all(1.5, ft.Colors.with_opacity(0.4, ft.Colors.RED_400))
                action_button.text = "UNLOCK FOLDER"
                action_button.icon = ft.Icons.LOCK_OPEN_ROUNDED
                action_button.style.bgcolor = ft.Colors.GREEN_600
                action_button.style.shadow_color = ft.Colors.GREEN_900
                recovery_checkbox.visible = True
                password_field.label = "Password or Recovery Key"
                
                # Check if Windows hello is enabled for this folder
                hello_pwd = None
                try:
                    hello_pwd = keyring.get_password("FolderDoor", selected_folder)
                except:
                    pass
                hello_button.visible = bool(hello_pwd)
            else:
                status_icon.icon = ft.Icons.LOCK_OPEN_ROUNDED
                status_icon.color = ft.Colors.GREEN_400
                status_badge.border = border_all(1.5, ft.Colors.CYAN_300)
                logo_container.border = border_all(1.5, ft.Colors.with_opacity(0.4, ft.Colors.CYAN_300))
                action_button.text = "LOCK FOLDER"
                action_button.icon = ft.Icons.LOCK_ROUNDED
                action_button.style.bgcolor = ft.Colors.RED_600
                action_button.style.shadow_color = ft.Colors.RED_900
                recovery_checkbox.visible = False
                recovery_checkbox.value = False
                password_field.label = "Set Password"
                hello_button.visible = False
                
            action_button.disabled = False
        else:
            folder_text.value = "Drag & Drop Folder Here"
            folder_text.size = 16
            folder_text.color = ft.Colors.WHITE70
            folder_icon_large.icon = ft.Icons.CLOUD_UPLOAD_ROUNDED
            action_button.disabled = True
            recovery_checkbox.visible = False
            hello_button.visible = False
            status_icon.icon = ft.Icons.LOCK_OPEN_ROUNDED
            status_icon.color = ft.Colors.WHITE54
            status_badge.border = border_all(1.5, ft.Colors.WHITE24)
            logo_container.border = border_all(1.5, ft.Colors.with_opacity(0.3, ft.Colors.WHITE24))
            
        page.update()

    def pick_folder_result():
        root = tk.Tk()
        root.withdraw()
        folder = filedialog.askdirectory(title="Select Folder to Lock/Unlock")
        root.destroy()
        if folder:
            nonlocal selected_folder
            selected_folder = folder
            update_ui_state()
            switch_tab(0)

    select_btn = ft.ElevatedButton(
        "Choose Folder", 
        icon=ft.Icons.FOLDER_OPEN_ROUNDED, 
        on_click=lambda e: pick_folder_result(),
        visible=not direct_folder,
        width=200,
        height=45,
        style=ft.ButtonStyle(
            bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.WHITE),
            color=ft.Colors.WHITE,
            shape=ft.RoundedRectangleBorder(radius=8),
            elevation=0
        )
    )
    
    def on_dropped(e):
        if e.files:
            file_path = e.files[0].path
            if os.path.isfile(file_path):
                file_path = os.path.dirname(file_path)
            nonlocal selected_folder
            selected_folder = file_path
            update_ui_state()
            switch_tab(0)

    dropzone_content = ft.Container(
        content=ft.Column(
            [
                folder_icon_large,
                folder_text,
                select_btn,
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=10
        ),
        padding=25,
        width=350,
        border_radius=16,
        bgcolor=ft.Colors.with_opacity(0.05, ft.Colors.CYAN_300),
        border=border_all(2, ft.Colors.with_opacity(0.3, ft.Colors.CYAN_300))
    )
    
    dropzone = ftd.Dropzone(
        content=dropzone_content,
        on_dropped=on_dropped
    )
    
    def show_snack(message, color=ft.Colors.RED_500):
        page.snack_bar = ft.SnackBar(
            ft.Text(message, color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD), 
            bgcolor=color,
            behavior=ft.SnackBarBehavior.FLOATING,
            shape=ft.RoundedRectangleBorder(radius=10)
        )
        page.snack_bar.open = True
        page.update()

    def show_dialog(title, content):
        dlg = ft.AlertDialog(
            title=ft.Text(title, weight=ft.FontWeight.BOLD, color=ft.Colors.CYAN_300),
            content=ft.Text(content, selectable=True, size=16),
            shape=ft.RoundedRectangleBorder(radius=16),
            bgcolor=ft.Colors.BLUE_GREY_900,
            actions=[ft.TextButton("I have saved it", on_click=lambda e: close_dlg(dlg), style=ft.ButtonStyle(color=ft.Colors.CYAN_300))],
        )
        page.dialog = dlg
        dlg.open = True
        page.update()
        
    def close_dlg(dlg):
        dlg.open = False
        page.update()

    def perform_action(e=None, bypass_pwd=None):
        nonlocal selected_folder, failed_attempts
        update_activity()
        
        if not selected_folder:
            return
            
        pwd = bypass_pwd if bypass_pwd else password_field.value
        if not pwd:
            show_snack("Please enter a password!")
            return
            
        action_button.disabled = True
        password_field.disabled = True
        select_btn.disabled = True
        recovery_checkbox.disabled = True
        hello_button.disabled = True
        progress_bar.visible = True
        progress_bar.value = 0
        page.update()
        
        def run_task():
            nonlocal selected_folder, failed_attempts
            def progress_cb(current, total):
                if total > 0:
                    progress_bar.value = current / total
                    page.update()
                    
            try:
                if is_locked:
                    unlocked_path = locker.unlock_folder(
                        selected_folder, 
                        pwd, 
                        is_recovery=recovery_checkbox.value,
                        progress_callback=progress_cb
                    )
                    play_lock_animation(locked=False)
                    time.sleep(0.5)
                    failed_attempts = 0
                    
                    unlocked_folders[unlocked_path] = pwd
                    
                    if direct_folder:
                        os.startfile(unlocked_path)
                        page.window.close()
                    else:
                        show_snack("Folder unlocked successfully!", ft.Colors.GREEN_600)
                        selected_folder = unlocked_path
                        password_field.value = ""
                        update_ui_state()
                        update_dashboard()
                else:
                    rec_key = locker.lock_folder(
                        selected_folder,
                        pwd,
                        progress_callback=progress_cb
                    )
                    play_lock_animation(locked=True)
                    time.sleep(0.5)
                    
                    if selected_folder in unlocked_folders:
                        del unlocked_folders[selected_folder]
                    
                    msg = (
                        "Folder locked successfully!\n\n"
                        "IMPORTANT: Save this Recovery Key in a safe place.\n\n"
                        f"{rec_key}"
                    )
                    show_dialog("Success!", msg)
                    
                    parent_dir = os.path.dirname(selected_folder)
                    locked_path = os.path.join(parent_dir, "." + os.path.basename(selected_folder) + "_locked")
                    config.remove_folder(selected_folder)
                    config.add_folder(locked_path)
                    
                    selected_folder = locked_path
                    password_field.value = ""
                    update_ui_state()
                    update_dashboard()
                    
            except ValueError as ve:
                failed_attempts += 1
                show_snack(str(ve))
                settings = config.load_settings()
                if settings.get("intruder_alert") and failed_attempts >= 3:
                    trigger_intruder_alert()
                    show_snack("Intruder alert triggered!", ft.Colors.ORANGE_500)
                update_ui_state()
            except Exception as ex:
                show_snack(str(ex))
                update_ui_state()
            finally:
                password_field.disabled = False
                select_btn.disabled = False
                recovery_checkbox.disabled = False
                hello_button.disabled = False
                progress_bar.visible = False
                action_button.disabled = False
                page.update()
                
        threading.Thread(target=run_task, daemon=True).start()
        
    action_button.on_click = perform_action
    
    def on_hello_click(e):
        if windows_hello_auth():
            try:
                pwd = keyring.get_password("FolderDoor", selected_folder)
                if pwd:
                    perform_action(bypass_pwd=pwd)
                else:
                    show_snack("Password not found in Credential Manager.")
            except Exception as ex:
                show_snack("Keyring error: " + str(ex))
        else:
            show_snack("Windows Hello authentication failed or cancelled.")
            
    hello_button.on_click = on_hello_click

    home_view = ft.Column(
        [
            logo_container,
            title_text,
            subtitle_text,
            ft.Container(height=15),
            dropzone,
            ft.Container(height=15),
            password_field,
            recovery_checkbox,
            ft.Container(height=5),
            progress_bar,
            action_button,
            hello_button
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        scroll=ft.ScrollMode.AUTO,
        visible=True
    )
    
    # --- DASHBOARD VIEW ---
    dashboard_list = ft.ListView(expand=True, spacing=10)
    dashboard_view = ft.Column(
        [
            ft.Text("Dashboard", size=28, weight=ft.FontWeight.BOLD, color=ft.Colors.CYAN_300),
            ft.Text("Manage your locked folders", color=ft.Colors.WHITE70),
            ft.Container(height=10),
            dashboard_list
        ],
        visible=False,
        expand=True
    )
    
    def select_dashboard_folder(path):
        nonlocal selected_folder
        selected_folder = path
        update_ui_state()
        switch_tab(0) # Go to home
        page.navigation_bar.selected_index = 0
        page.update()
        
    def remove_dashboard_folder(path):
        config.remove_folder(path)
        update_dashboard()

    def update_dashboard():
        dashboard_list.controls.clear()
        settings = config.load_settings()
        folders = settings.get("locked_folders", [])
        if not folders:
            dashboard_list.controls.append(
                ft.Text("No folders found. Add a folder from the Home screen.", color=ft.Colors.WHITE54, text_align=ft.TextAlign.CENTER)
            )
        else:
            for fpath in folders:
                fname = os.path.basename(fpath)
                dashboard_list.controls.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Icon(ft.Icons.LOCK, color=ft.Colors.CYAN_300),
                            ft.Text(fname, expand=True, color=ft.Colors.WHITE),
                            ft.IconButton(ft.Icons.DELETE_OUTLINE, icon_color=ft.Colors.RED_400, on_click=lambda e, p=fpath: remove_dashboard_folder(p))
                        ]),
                        padding=15,
                        border_radius=10,
                        bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.WHITE),
                        on_click=lambda e, p=fpath: select_dashboard_folder(p),
                        ink=True
                    )
                )
        page.update()

    # --- SETTINGS VIEW ---
    def toggle_setting(e, key):
        settings = config.load_settings()
        settings[key] = e.control.value
        config.save_settings(settings)
        update_activity()
        
    def save_decoy(e):
        settings = config.load_settings()
        settings["decoy_password"] = e.control.value
        config.save_settings(settings)
        update_activity()

    settings = config.load_settings()
    auto_lock_switch = ft.Switch(label="Auto-Lock (10 mins idle)", value=settings.get("auto_lock", False), active_color=ft.Colors.CYAN_400, on_change=lambda e: toggle_setting(e, "auto_lock"))
    win_hello_switch = ft.Switch(label="Enable Windows Hello", value=settings.get("windows_hello", False), active_color=ft.Colors.CYAN_400, on_change=lambda e: toggle_setting(e, "windows_hello"))
    intruder_switch = ft.Switch(label="Intruder Alert (Webcam)", value=settings.get("intruder_alert", False), active_color=ft.Colors.CYAN_400, on_change=lambda e: toggle_setting(e, "intruder_alert"))
    decoy_input = ft.TextField(label="Decoy Password (Optional)", password=True, can_reveal_password=True, value=settings.get("decoy_password", ""), on_change=save_decoy, border_color=ft.Colors.with_opacity(0.3, ft.Colors.WHITE))

    settings_view = ft.Column(
        [
            ft.Text("Control Panel", size=28, weight=ft.FontWeight.BOLD, color=ft.Colors.CYAN_300),
            ft.Text("Advanced Security Settings", color=ft.Colors.WHITE70),
            ft.Container(height=20),
            ft.Container(
                content=ft.Column([
                    auto_lock_switch,
                    ft.Text("Automatically locks all unlocked folders after 10 minutes of inactivity.", color=ft.Colors.WHITE54, size=12),
                    ft.Divider(color=ft.Colors.WHITE24),
                    win_hello_switch,
                    ft.Text("Allows unlocking using Windows Hello (Fingerprint/Face). Only applies to newly locked folders.", color=ft.Colors.WHITE54, size=12),
                    ft.Divider(color=ft.Colors.WHITE24),
                    intruder_switch,
                    ft.Text("Takes a silent photo using the webcam after 3 failed password attempts.", color=ft.Colors.WHITE54, size=12),
                    ft.Divider(color=ft.Colors.WHITE24),
                    decoy_input,
                    ft.Text("Enter a fake password. If forced to unlock, typing this will open a fake, empty folder.", color=ft.Colors.WHITE54, size=12),
                ], spacing=10),
                padding=20,
                border_radius=12,
                bgcolor=ft.Colors.with_opacity(0.05, ft.Colors.WHITE),
                border=border_all(1, ft.Colors.with_opacity(0.1, ft.Colors.WHITE))
            )
        ],
        visible=False,
        expand=True,
        scroll=ft.ScrollMode.AUTO
    )

    # --- NAVIGATION ---
    def switch_tab(index):
        update_activity()
        home_view.visible = (index == 0)
        dashboard_view.visible = (index == 1)
        settings_view.visible = (index == 2)
        if index == 1:
            update_dashboard()
        page.update()

    page.navigation_bar = ft.NavigationBar(
        destinations=[
            ft.NavigationBarDestination(icon=ft.Icons.HOME_ROUNDED, label="Home"),
            ft.NavigationBarDestination(icon=ft.Icons.DASHBOARD_ROUNDED, label="Dashboard"),
            ft.NavigationBarDestination(icon=ft.Icons.SETTINGS_ROUNDED, label="Control Panel"),
        ],
        selected_index=0,
        on_change=lambda e: switch_tab(e.control.selected_index),
        bgcolor=ft.Colors.BLUE_GREY_900,
    )

    # Layout structure
    main_container = ft.Container(
        expand=True,
        gradient=ft.LinearGradient(
            begin=ft.Alignment(0.0, -1.0),
            end=ft.Alignment(0.0, 1.0),
            colors=[ft.Colors.BLUE_GREY_900, ft.Colors.BLACK],
        ),
        padding=20,
        content=ft.Stack([
            home_view,
            dashboard_view,
            settings_view
        ], expand=True)
    )
    
    page.add(main_container)
    
    # Adjust for direct mode
    if direct_folder:
        page.navigation_bar.visible = False
        page.window.width = 400
        page.window.height = 650
        title_text.value = "Unlock FolderDoor"
        subtitle_text.value = "Enter your password to unlock"
    
    update_ui_state()
    update_dashboard()

if __name__ == "__main__":
    ft.app(target=main)
