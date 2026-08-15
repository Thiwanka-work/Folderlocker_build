import flet as ft
import locker
import sys
import os
import tkinter as tk
from tkinter import filedialog
import threading
import time

def get_icon_path():
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Folderlocker")
    return os.path.join(base_path, "Folderlocker.ico")

def border_all(width, color):
    bs = ft.BorderSide(width, color)
    return ft.Border(top=bs, right=bs, bottom=bs, left=bs)

def main(page: ft.Page):
    # Window setup
    page.title = "FolderDoor"
    page.window.width = 450
    page.window.height = 680
    page.window.resizable = False
    page.padding = 0
    page.theme_mode = ft.ThemeMode.DARK
    
    # Path to icon (Make sure it's accessible)
    icon_path = get_icon_path()
    
    # Check if opened via shortcut (Direct mode)
    direct_folder = sys.argv[1] if len(sys.argv) > 1 else None
    
    # State variables
    selected_folder = direct_folder
    is_locked = False
    
    # --- UI Elements ---
    
    animated_icon = ft.Icon(
        icon=ft.Icons.FOLDER_OPEN,
        size=80,
        color=ft.Colors.WHITE,
        scale=1.0,
        rotate=0.0,
        animate_scale=ft.Animation(800, ft.AnimationCurve.ELASTIC_OUT),
        animate_rotation=ft.Animation(500, ft.AnimationCurve.DECELERATE),
    )
    
    # Top Logo Container (glassmorphism circle)
    logo_container = ft.Container(
        content=animated_icon,
        width=140,
        height=140,
        alignment=ft.Alignment(0, 0),
        border_radius=70,
        gradient=ft.LinearGradient(
            begin=ft.Alignment(-1.0, -1.0),
            end=ft.Alignment(1.0, 1.0),
            colors=[ft.Colors.with_opacity(0.2, ft.Colors.WHITE), ft.Colors.with_opacity(0.05, ft.Colors.WHITE)],
        ),
        border=border_all(1, ft.Colors.with_opacity(0.2, ft.Colors.WHITE)),
        shadow=ft.BoxShadow(spread_radius=5, blur_radius=20, color=ft.Colors.with_opacity(0.3, ft.Colors.BLACK)),
        margin=ft.Margin(left=0, top=30, right=0, bottom=20)
    )
    
    title_text = ft.Text("FolderDoor", size=32, weight=ft.FontWeight.W_900, color=ft.Colors.WHITE)
    subtitle_text = ft.Text("Secure your private files", size=14, color=ft.Colors.WHITE70, italic=True)
    
    folder_text = ft.Text("No folder selected", color=ft.Colors.WHITE70, size=14, text_align=ft.TextAlign.CENTER)
    
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
        border_radius=12
    )
    
    recovery_checkbox = ft.Checkbox(label="Use Recovery Key", visible=False, fill_color=ft.Colors.CYAN_500)
    
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

    def play_lock_animation(locked: bool):
        # Scale up and rotate slightly
        animated_icon.scale = 1.4
        animated_icon.rotate = 0.1 if locked else -0.1
        page.update()
        time.sleep(0.3)
        # Change icon and color based on state
        if locked:
            animated_icon.icon = ft.Icons.LOCK_ROUNDED
            animated_icon.color = ft.Colors.RED_400
        else:
            animated_icon.icon = ft.Icons.FOLDER_OPEN_ROUNDED
            animated_icon.color = ft.Colors.GREEN_400
        # Scale down and reset rotation
        animated_icon.scale = 1.0
        animated_icon.rotate = 0.0
        page.update()

    def update_ui_state():
        nonlocal is_locked
        if selected_folder:
            folder_name = os.path.basename(selected_folder)
            if len(folder_name) > 30: 
                folder_name = "..." + folder_name[-30:]
            folder_text.value = f"Selected:\n{folder_name}"
            
            is_locked = locker.is_locked(selected_folder)
            
            if is_locked:
                animated_icon.icon = ft.Icons.LOCK_ROUNDED
                animated_icon.color = ft.Colors.RED_400
                action_button.text = "UNLOCK FOLDER"
                action_button.icon = ft.Icons.LOCK_OPEN_ROUNDED
                action_button.style.bgcolor = ft.Colors.GREEN_600
                action_button.style.shadow_color = ft.Colors.GREEN_900
                recovery_checkbox.visible = True
                password_field.label = "Password or Recovery Key"
            else:
                animated_icon.icon = ft.Icons.FOLDER_OPEN_ROUNDED
                animated_icon.color = ft.Colors.WHITE
                action_button.text = "LOCK FOLDER"
                action_button.icon = ft.Icons.LOCK_ROUNDED
                action_button.style.bgcolor = ft.Colors.RED_600
                action_button.style.shadow_color = ft.Colors.RED_900
                recovery_checkbox.visible = False
                recovery_checkbox.value = False
                password_field.label = "Set Password"
                
            action_button.disabled = False
        else:
            folder_text.value = "No folder selected"
            action_button.disabled = True
            recovery_checkbox.visible = False
            animated_icon.icon = ft.Icons.FOLDER
            animated_icon.color = ft.Colors.WHITE54
            
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

    select_btn = ft.ElevatedButton(
        "Choose Folder", 
        icon=ft.Icons.FOLDER_SPECIAL_ROUNDED, 
        on_click=lambda e: pick_folder_result(),
        visible=not direct_folder,
        width=200,
        height=45,
        style=ft.ButtonStyle(
            bgcolor=ft.Colors.with_opacity(0.2, ft.Colors.WHITE),
            color=ft.Colors.WHITE,
            shape=ft.RoundedRectangleBorder(radius=8),
            elevation=0
        )
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

    def perform_action(e):
        if not selected_folder:
            return
            
        pwd = password_field.value
        if not pwd:
            show_snack("Please enter a password!")
            return
            
        # Disable UI during processing
        action_button.disabled = True
        password_field.disabled = True
        select_btn.disabled = True
        recovery_checkbox.disabled = True
        progress_bar.visible = True
        progress_bar.value = 0
        page.update()
        
        def run_task():
            nonlocal selected_folder
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
                    time.sleep(0.5) # Let animation finish
                    
                    if direct_folder:
                        os.startfile(unlocked_path)
                        page.window.close()
                    else:
                        show_snack("Folder unlocked successfully!", ft.Colors.GREEN_600)
                        selected_folder = None
                        password_field.value = ""
                        update_ui_state()
                else:
                    rec_key = locker.lock_folder(
                        selected_folder,
                        pwd,
                        progress_callback=progress_cb
                    )
                    play_lock_animation(locked=True)
                    time.sleep(0.5) # Let animation finish
                    
                    msg = (
                        "Folder locked successfully!\n\n"
                        "IMPORTANT: Save this Recovery Key in a safe place.\n\n"
                        f"{rec_key}"
                    )
                    show_dialog("Success!", msg)
                    password_field.value = ""
                    update_ui_state()
                    
            except Exception as ex:
                show_snack(str(ex))
                update_ui_state()
            finally:
                password_field.disabled = False
                select_btn.disabled = False
                recovery_checkbox.disabled = False
                progress_bar.visible = False
                action_button.disabled = False
                page.update()
                
        # Run in thread to prevent UI freezing
        threading.Thread(target=run_task, daemon=True).start()
        
    action_button.on_click = perform_action

    # Build Page structure with elegant gradient background
    main_container = ft.Container(
        expand=True,
        gradient=ft.LinearGradient(
            begin=ft.Alignment(0.0, -1.0),
            end=ft.Alignment(0.0, 1.0),
            colors=[ft.Colors.BLUE_GREY_900, ft.Colors.BLACK],
        ),
        padding=20,
        content=ft.Column(
            [
                logo_container,
                title_text,
                subtitle_text,
                ft.Container(height=15),
                
                # Glassmorphism folder card
                ft.Container(
                    content=ft.Column(
                        [
                            select_btn,
                            folder_text,
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=15
                    ),
                    padding=25,
                    width=350,
                    border_radius=16,
                    gradient=ft.LinearGradient(
                        colors=[ft.Colors.with_opacity(0.1, ft.Colors.WHITE), ft.Colors.with_opacity(0.02, ft.Colors.WHITE)]
                    ),
                    border=border_all(1, ft.Colors.with_opacity(0.1, ft.Colors.WHITE)),
                ),
                
                ft.Container(height=15),
                password_field,
                recovery_checkbox,
                ft.Container(height=10),
                progress_bar,
                action_button
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            scroll=ft.ScrollMode.AUTO
        )
    )
    
    page.add(main_container)
    
    # Adjust for direct mode
    if direct_folder:
        page.window.width = 400
        page.window.height = 650
        title_text.value = "Unlock FolderDoor"
        subtitle_text.value = "Enter your password to unlock"
        update_ui_state()

if __name__ == "__main__":
    ft.app(target=main)
