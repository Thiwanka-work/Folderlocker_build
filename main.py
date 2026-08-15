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
            cap = cv2.VideoCapture(0, cv2.CAP_DSHOW) if os.name == 'nt' else cv2.VideoCapture(0)
            if cap.isOpened():
                ret, frame = cap.read()
                if ret and frame is not None:
                    if not os.path.exists("Intruders"):
                        os.makedirs("Intruders", exist_ok=True)
                    filename = f"Intruders/intruder_{int(time.time())}.jpg"
                    cv2.imwrite(filename, frame)
                cap.release()
        except Exception as e:
            print("Intruder capture error:", e)
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
                    parent_dir = os.path.dirname(folder)
                    locked_path = os.path.join(parent_dir, "." + os.path.basename(folder) + "_locked")
                    config.add_folder(locked_path)
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
        rotate=ft.Rotate(angle=0, alignment=ft.Alignment(0, 0)),
        animate_rotation=ft.Animation(200, ft.AnimationCurve.EASE_IN_OUT),
        animate_scale=ft.Animation(300, ft.AnimationCurve.EASE_IN_OUT),
        animate_opacity=ft.Animation(200, ft.AnimationCurve.EASE_IN_OUT),
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
        margin=ft.Margin(left=0, top=25, right=0, bottom=15),
        animate_scale=ft.Animation(350, ft.AnimationCurve.ELASTIC_OUT),
        animate_opacity=ft.Animation(200, ft.AnimationCurve.EASE_IN_OUT),
    )
    
    title_text = ft.Text("FolderDoor", size=32, weight=ft.FontWeight.W_900, color=ft.Colors.WHITE)
    subtitle_text = ft.Text("Secure your private files", size=14, color=ft.Colors.WHITE70, italic=True)
    
    folder_icon_large = ft.Icon(ft.Icons.FOLDER_OPEN_ROUNDED, size=40, color=ft.Colors.CYAN_300)
    folder_text = ft.Text("Select a Folder to Secure", color=ft.Colors.WHITE, size=16, text_align=ft.TextAlign.CENTER, weight=ft.FontWeight.W_600)
    folder_hint = ft.Text("Click card or button to browse", color=ft.Colors.WHITE54, size=12, text_align=ft.TextAlign.CENTER)
    
    password_error_text = ft.Text("", color=ft.Colors.RED_300, size=12, visible=False)

    def on_pwd_change(e):
        update_activity()
        if password_error_text.visible:
            password_error_text.visible = False
            password_error_text.value = ""
            page.update()

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
        on_change=on_pwd_change,
        on_submit=lambda e: perform_action()
    )
    
    # Animated loading indicator using Flet's native ProgressRing (thread-safe)
    loading_ring = ft.ProgressRing(
        width=24,
        height=24,
        stroke_width=3,
        color=ft.Colors.CYAN_300,
    )
    loading_text = ft.Text("Working...", color=ft.Colors.CYAN_200, size=13)
    loading_row = ft.Row(
        [loading_ring, loading_text],
        alignment=ft.MainAxisAlignment.CENTER,
        spacing=10,
        visible=False,
    )

    def show_loading(message="Working..."):
        loading_text.value = message
        loading_row.visible = True
        page.update()

    def hide_loading():
        loading_row.visible = False
        try:
            loading_row.update()
        except Exception:
            pass


    recovery_checkbox = ft.Checkbox(label="Use Recovery Key", visible=False, fill_color=ft.Colors.CYAN_500, on_change=update_activity)
    
    action_button = ft.ElevatedButton(
        "SELECT A FOLDER FIRST",
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
    
    def hello_hover(e):
        if e.data == "true":
            hello_button.bgcolor = ft.Colors.with_opacity(0.15, ft.Colors.CYAN_300)
            hello_button.border = border_all(2, ft.Colors.with_opacity(0.6, ft.Colors.CYAN_300))
            hello_button.shadow = ft.BoxShadow(spread_radius=6, blur_radius=25, color=ft.Colors.with_opacity(0.3, ft.Colors.CYAN_900))
        else:
            hello_button.bgcolor = ft.Colors.with_opacity(0.05, ft.Colors.CYAN_300)
            hello_button.border = border_all(2, ft.Colors.with_opacity(0.3, ft.Colors.CYAN_300))
            hello_button.shadow = ft.BoxShadow(spread_radius=4, blur_radius=20, color=ft.Colors.with_opacity(0.15, ft.Colors.CYAN_900))
        try:
            hello_button.update()
        except:
            pass

    hello_button = ft.Container(
        content=ft.Column(
            [
                ft.Icon(ft.Icons.FINGERPRINT, size=55, color=ft.Colors.CYAN_300),
                ft.Text("Unlock with Fingerprint", size=11, color=ft.Colors.CYAN_200, weight=ft.FontWeight.W_500)
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=5
        ),
        visible=False,
        width=130,
        height=130,
        border_radius=65,
        bgcolor=ft.Colors.with_opacity(0.05, ft.Colors.CYAN_300),
        border=border_all(2, ft.Colors.with_opacity(0.3, ft.Colors.CYAN_300)),
        shadow=ft.BoxShadow(spread_radius=4, blur_radius=20, color=ft.Colors.with_opacity(0.15, ft.Colors.CYAN_900)),
        ink=True,
        on_hover=hello_hover,
        animate=ft.Animation(300, ft.AnimationCurve.EASE_OUT)
    )

    def play_lock_animation(locked: bool):
        try:
            if locked:
                # Step 1: Shake + scale up (Flet animates rotation smoothly)
                logo_container.scale = 1.12
                logo_stack.rotate = ft.Rotate(angle=0.2, alignment=ft.Alignment(0, 0))
                status_icon.icon = ft.Icons.LOCK_ROUNDED
                status_icon.color = ft.Colors.RED_400
                status_badge.border = border_all(1.5, ft.Colors.RED_400)
                logo_container.border = border_all(2.5, ft.Colors.with_opacity(0.8, ft.Colors.RED_400))
                logo_container.shadow = ft.BoxShadow(spread_radius=8, blur_radius=35, color=ft.Colors.with_opacity(0.5, ft.Colors.RED_900))
                logo_container.gradient = ft.LinearGradient(
                    begin=ft.Alignment(-1.0, -1.0),
                    end=ft.Alignment(1.0, 1.0),
                    colors=[ft.Colors.with_opacity(0.3, ft.Colors.RED_400), ft.Colors.with_opacity(0.05, ft.Colors.WHITE)],
                )
                page.update()
                time.sleep(0.3)

                # Step 2: Settle back — Flet ELASTIC_OUT curve bounces naturally
                logo_container.scale = 1.0
                logo_stack.rotate = ft.Rotate(angle=0, alignment=ft.Alignment(0, 0))
                status_icon.scale = 1.0
                page.update()

            else:
                # Step 1: Shrink + swap to green
                logo_container.scale = 0.88
                logo_container.opacity = 0.7
                status_icon.icon = ft.Icons.LOCK_OPEN_ROUNDED
                status_icon.color = ft.Colors.GREEN_400
                status_badge.border = border_all(1.5, ft.Colors.GREEN_400)
                logo_container.border = border_all(2.5, ft.Colors.with_opacity(0.8, ft.Colors.GREEN_400))
                logo_container.shadow = ft.BoxShadow(spread_radius=10, blur_radius=40, color=ft.Colors.with_opacity(0.55, ft.Colors.GREEN_900))
                logo_container.gradient = ft.LinearGradient(
                    begin=ft.Alignment(-1.0, -1.0),
                    end=ft.Alignment(1.0, 1.0),
                    colors=[ft.Colors.with_opacity(0.3, ft.Colors.GREEN_400), ft.Colors.with_opacity(0.05, ft.Colors.WHITE)],
                )
                page.update()
                time.sleep(0.2)

                # Step 2: Elastic bounce back — animate_scale ELASTIC_OUT handles the bounce
                logo_container.scale = 1.0
                logo_container.opacity = 1.0
                status_icon.scale = 1.0
                page.update()

        except Exception:
            pass  # Never crash the UI due to animation failure



    def update_ui_state():
        nonlocal is_locked
        update_activity()
        
        if selected_folder:
            folder_name = os.path.basename(selected_folder)
            if len(folder_name) > 25: 
                folder_name = "..." + folder_name[-25:]
            folder_text.value = folder_name
            folder_text.size = 18
            folder_text.color = ft.Colors.CYAN_200
            folder_hint.value = "Click to change folder"
            folder_icon_large.icon = ft.Icons.FOLDER_SPECIAL_ROUNDED
            select_btn.content = "Change Folder"
            
            is_locked = locker.is_locked(selected_folder)
            
            if is_locked:
                # Only add locked folders to dashboard/config
                config.add_folder(selected_folder)
                status_icon.icon = ft.Icons.LOCK_ROUNDED
                status_icon.color = ft.Colors.RED_400
                status_badge.border = border_all(1.5, ft.Colors.RED_400)
                logo_container.border = border_all(1.5, ft.Colors.with_opacity(0.4, ft.Colors.RED_400))
                
                # Check if Windows hello is enabled for this folder
                hello_pwd = None
                try:
                    hello_pwd = keyring.get_password("FolderDoor", selected_folder)
                except:
                    pass
                
                # Show Fingerprint option if available
                hello_button.visible = bool(hello_pwd)
                
                # ALWAYS show password option
                password_field.visible = True
                action_button.visible = True
                recovery_checkbox.visible = True
                action_button.content = "UNLOCK FOLDER"
                action_button.icon = ft.Icons.LOCK_OPEN_ROUNDED
                action_button.style.bgcolor = ft.Colors.GREEN_600
                action_button.style.shadow_color = ft.Colors.GREEN_900
                password_field.label = "Password or Recovery Key"
            else:
                status_icon.icon = ft.Icons.LOCK_OPEN_ROUNDED
                status_icon.color = ft.Colors.GREEN_400
                status_badge.border = border_all(1.5, ft.Colors.CYAN_300)
                logo_container.border = border_all(1.5, ft.Colors.with_opacity(0.4, ft.Colors.CYAN_300))
                action_button.content = "LOCK FOLDER"
                action_button.icon = ft.Icons.LOCK_ROUNDED
                action_button.style.bgcolor = ft.Colors.RED_600
                action_button.style.shadow_color = ft.Colors.RED_900
                recovery_checkbox.visible = False
                recovery_checkbox.value = False
                password_field.label = "Set Password"
                hello_button.visible = False
                password_field.visible = True
                action_button.visible = True
                
            action_button.disabled = False
        else:
            folder_text.value = "Select a Folder to Secure"
            folder_text.size = 16
            folder_text.color = ft.Colors.WHITE
            folder_hint.value = "Click card or button to browse"
            folder_icon_large.icon = ft.Icons.FOLDER_OPEN_ROUNDED
            select_btn.content = "Browse Folder"
            action_button.content = "SELECT A FOLDER FIRST"
            action_button.icon = ft.Icons.FOLDER_OPEN_ROUNDED
            action_button.style.bgcolor = ft.Colors.BLUE_GREY_700
            action_button.style.shadow_color = ft.Colors.BLUE_GREY_900
            action_button.disabled = True
            recovery_checkbox.visible = False
            hello_button.visible = False
            password_field.visible = True
            action_button.visible = True
            status_icon.icon = ft.Icons.LOCK_OPEN_ROUNDED
            status_icon.color = ft.Colors.WHITE54
            status_badge.border = border_all(1.5, ft.Colors.WHITE24)
            logo_container.border = border_all(1.5, ft.Colors.with_opacity(0.3, ft.Colors.WHITE24))
            
        try:
            action_button.update()
            password_field.update()
            recovery_checkbox.update()
            hello_button.update()
        except Exception:
            pass
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
        "Browse Folder", 
        icon=ft.Icons.FOLDER_OPEN_ROUNDED, 
        on_click=lambda e: pick_folder_result(),
        visible=not direct_folder,
        width=180,
        height=40,
        style=ft.ButtonStyle(
            bgcolor=ft.Colors.with_opacity(0.15, ft.Colors.CYAN_400),
            color=ft.Colors.CYAN_100,
            shape=ft.RoundedRectangleBorder(radius=8),
            elevation=0
        )
    )

    folder_card = ft.Container(
        content=ft.Column(
            [
                folder_icon_large,
                folder_text,
                folder_hint,
                select_btn,
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=8
        ),
        padding=20,
        width=350,
        border_radius=16,
        bgcolor=ft.Colors.with_opacity(0.06, ft.Colors.CYAN_400),
        border=border_all(1.5, ft.Colors.with_opacity(0.35, ft.Colors.CYAN_400)),
        on_click=lambda e: pick_folder_result() if not direct_folder else None,
        ink=True,
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
            show_snack("Please select a folder first!")
            return
            
        pwd = bypass_pwd if bypass_pwd else password_field.value
        if not pwd:
            password_error_text.value = "Password is required"
            password_error_text.visible = True
            page.update()
            return
            
        password_error_text.visible = False
        password_error_text.value = ""
        action_button.disabled = True
        show_loading("Processing...")
        page.update()
        
        def run_task():
            start_time = time.time()
            nonlocal selected_folder, failed_attempts
            
            last_update = 0
            def progress_cb(current, total):
                nonlocal last_update
                if total > 0:
                    now = time.time()
                    # Throttle updates to max 10 per second to prevent Flet WS crash
                    if now - last_update > 0.1 or current == total:
                        pct = int((current / total) * 100)
                        loading_text.value = f"Processing... {pct}%"
                        try:
                            loading_text.update()
                        except Exception:
                            pass
                        last_update = now
                    
            try:
                if is_locked:
                    unlocked_path = locker.unlock_folder(
                        selected_folder, 
                        pwd, 
                        is_recovery=recovery_checkbox.value,
                        progress_callback=progress_cb
                    )
                    config.remove_folder(selected_folder)
                    
                    try:
                        keyring.delete_password("FolderDoor", selected_folder)
                    except:
                        pass
                        
                    elapsed = time.time() - start_time
                    if elapsed < 1.5:
                        time.sleep(1.5 - elapsed)
                        
                    hide_loading()  # Hide before animation
                    play_lock_animation(locked=False)
                    failed_attempts = 0
                    unlocked_folders[unlocked_path] = pwd
                    
                    if direct_folder:
                        os.startfile(unlocked_path)
                        page.window.close()
                        return
                    else:
                        password_field.value = ""
                        password_error_text.visible = False
                        password_error_text.value = ""
                        selected_folder = unlocked_path
                        update_ui_state()
                        update_dashboard()
                        show_snack("Folder unlocked successfully!", ft.Colors.GREEN_600)
                        page.update()
                else:
                    rec_key = locker.lock_folder(
                        selected_folder,
                        pwd,
                        progress_callback=progress_cb
                    )
                    
                    elapsed = time.time() - start_time
                    if elapsed < 1.5:
                        time.sleep(1.5 - elapsed)
                        
                    hide_loading()  # Hide before animation
                    play_lock_animation(locked=True)
                    
                    if selected_folder in unlocked_folders:
                        del unlocked_folders[selected_folder]
                    
                    msg = (
                        "Folder locked successfully!\n\n"
                        "IMPORTANT: Save this Recovery Key in a safe place:\n\n"
                        f"{rec_key}"
                    )
                    show_dialog("Folder Locked Successfully", msg)
                    
                    parent_dir = os.path.dirname(selected_folder)
                    locked_path = os.path.join(parent_dir, "." + os.path.basename(selected_folder) + "_locked")
                    config.remove_folder(selected_folder)
                    config.add_folder(locked_path)
                    
                    # Save to keyring for Windows Hello if enabled
                    settings = config.load_settings()
                    if settings.get("windows_hello", False):
                        try:
                            keyring.set_password("FolderDoor", locked_path, pwd)
                        except:
                            pass
                    
                    selected_folder = locked_path
                    password_field.value = ""
                    password_error_text.visible = False
                    password_error_text.value = ""
                    update_ui_state()
                    update_dashboard()
                    page.update()
                    
            except ValueError as ve:
                failed_attempts += 1
                err_msg = str(ve)
                password_error_text.value = "Incorrect password or recovery key!"
                password_error_text.visible = True
                password_error_text.update()
                show_snack(err_msg, ft.Colors.RED_600)
                
                settings = config.load_settings()
                if settings.get("intruder_alert") and failed_attempts >= 3:
                    trigger_intruder_alert()
                    show_snack(f"Intruder alert! Photo captured ({failed_attempts} attempts)", ft.Colors.ORANGE_700)
            except Exception as ex:
                err_msg = str(ex)
                password_error_text.value = err_msg
                password_error_text.visible = True
                password_error_text.update()
                show_snack(err_msg, ft.Colors.RED_600)
            finally:
                hide_loading()
                action_button.disabled = False
                action_button.update()
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
            folder_card,
            ft.Container(height=15),
            password_field,
            password_error_text,
            recovery_checkbox,
            ft.Container(height=5),
            loading_row,
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
                ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.Icons.FOLDER_OFF_ROUNDED, size=48, color=ft.Colors.WHITE24),
                        ft.Text("No locked folders", color=ft.Colors.WHITE54, size=16, weight=ft.FontWeight.W_600, text_align=ft.TextAlign.CENTER),
                        ft.Text("Lock a folder from the Home screen.", color=ft.Colors.WHITE38, size=12, text_align=ft.TextAlign.CENTER),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
                    alignment=ft.Alignment(0, 0),
                    expand=True,
                    padding=ft.Padding(left=0, top=60, right=0, bottom=0),
                )
            )
        else:
            for fpath in folders:
                fname = os.path.basename(fpath)
                # Determine if folder is still locked
                folder_is_locked = locker.is_locked(fpath)
                lock_icon = ft.Icons.LOCK_ROUNDED if folder_is_locked else ft.Icons.LOCK_OPEN_ROUNDED
                lock_color = ft.Colors.RED_400 if folder_is_locked else ft.Colors.GREEN_400
                status_label = "Locked" if folder_is_locked else "Unlocked"
                status_label_color = ft.Colors.RED_300 if folder_is_locked else ft.Colors.GREEN_300
                dashboard_list.controls.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Container(
                                content=ft.Icon(lock_icon, color=lock_color, size=22),
                                width=40, height=40,
                                border_radius=20,
                                bgcolor=ft.Colors.with_opacity(0.1, lock_color),
                                alignment=ft.Alignment(0, 0)
                            ),
                            ft.Column([
                                ft.Text(fname, color=ft.Colors.WHITE, weight=ft.FontWeight.W_600, size=14, 
                                        max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                                ft.Text(status_label, color=status_label_color, size=11)
                            ], expand=True, spacing=2),
                            ft.IconButton(
                                ft.Icons.OPEN_IN_NEW_ROUNDED, 
                                icon_color=ft.Colors.CYAN_300, 
                                tooltip="Select this folder",
                                on_click=lambda e, p=fpath: select_dashboard_folder(p)
                            ),
                            ft.IconButton(
                                ft.Icons.DELETE_OUTLINE_ROUNDED, 
                                icon_color=ft.Colors.RED_400, 
                                tooltip="Remove from list",
                                on_click=lambda e, p=fpath: remove_dashboard_folder(p)
                            )
                        ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                        padding=ft.Padding(left=15, top=12, right=15, bottom=12),
                        border_radius=12,
                        bgcolor=ft.Colors.with_opacity(0.07, ft.Colors.WHITE),
                        border=border_all(1, ft.Colors.with_opacity(0.12, ft.Colors.WHITE)),
                        ink=True,
                        on_click=lambda e, p=fpath: select_dashboard_folder(p),
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

    def open_intruders_folder(e):
        if os.path.exists("Intruders"):
            os.startfile(os.path.abspath("Intruders"))

    open_intruders_btn = ft.ElevatedButton(
        "View Captured Intruders",
        icon=ft.Icons.PHOTO_LIBRARY_ROUNDED,
        on_click=open_intruders_folder,
        disabled=True,
        style=ft.ButtonStyle(
            bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.RED_400),
            color=ft.Colors.RED_200,
        )
    )

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
                    open_intruders_btn,
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
        if index == 2:
            has_images = False
            if os.path.exists("Intruders"):
                has_images = any(f.endswith('.jpg') for f in os.listdir("Intruders"))
            open_intruders_btn.disabled = not has_images
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
