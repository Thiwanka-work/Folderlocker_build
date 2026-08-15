import flet as ft
import locker
import sys
import os
from tkinter import filedialog
import threading

def main(page: ft.Page):
    # Window setup
    page.title = "FolderDoor"
    page.window.width = 450
    page.window.height = 620
    page.window.resizable = False
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 30
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    
    # Path to icon (Make sure it's accessible)
    icon_path = r"C:\Users\2021icts36\Desktop\Folderlocker_build\Folderlocker\Folderlocker.ico"
    
    # Check if opened via shortcut (Direct mode)
    direct_folder = sys.argv[1] if len(sys.argv) > 1 else None
    
    # State variables
    selected_folder = direct_folder
    is_locked = False
    
    # --- UI Elements ---
    
    # Animated Logo
    logo = ft.Image(src=icon_path, width=80, height=80, fit="contain", visible=os.path.exists(icon_path))
    
    title_text = ft.Text("FolderDoor", size=28, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_400)
    
    folder_text = ft.Text("No folder selected", color=ft.Colors.GREY_400, italic=True)
    
    password_field = ft.TextField(
        label="Password", 
        password=True, 
        can_reveal_password=True,
        width=300,
        prefix_icon=ft.icons.LOCK,
        border_color=ft.Colors.BLUE_500,
        focused_border_color=ft.Colors.BLUE_300
    )
    
    recovery_checkbox = ft.Checkbox(label="Use Recovery Key", visible=False, fill_color=ft.Colors.BLUE_500)
    
    progress_bar = ft.ProgressBar(width=300, value=0, visible=False, color=ft.Colors.AMBER_400)
    
    action_button = ft.ElevatedButton(
        "Lock / Unlock",
        disabled=True,
        width=200,
        height=45,
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=8),
            animation_duration=300 # Smooth color transition
        )
    )

    def update_ui_state():
        """Updates the UI based on whether the selected folder is locked or not."""
        nonlocal is_locked
        if selected_folder:
            folder_name = os.path.basename(selected_folder)
            if len(folder_name) > 25: 
                folder_name = "..." + folder_name[-25:]
            folder_text.value = folder_name
            
            is_locked = locker.is_locked(selected_folder)
            
            if is_locked:
                action_button.text = "Unlock Folder"
                action_button.icon = ft.icons.LOCK_OPEN
                action_button.style.bgcolor = ft.Colors.GREEN_700
                action_button.style.color = ft.Colors.WHITE
                recovery_checkbox.visible = True
                password_field.label = "Password or Recovery Key"
            else:
                action_button.text = "Lock Folder"
                action_button.icon = ft.icons.LOCK
                action_button.style.bgcolor = ft.Colors.RED_700
                action_button.style.color = ft.Colors.WHITE
                recovery_checkbox.visible = False
                recovery_checkbox.value = False
                password_field.label = "Password"
                
            action_button.disabled = False
        else:
            folder_text.value = "No folder selected"
            action_button.disabled = True
            recovery_checkbox.visible = False
            
        page.update()

    def pick_folder_result():
        # Native file dialog is more reliable for simple desktop apps
        folder = filedialog.askdirectory(title="Select Folder to Lock/Unlock")
        if folder:
            nonlocal selected_folder
            selected_folder = folder
            update_ui_state()

    select_btn = ft.ElevatedButton(
        "Select Folder", 
        icon=ft.icons.FOLDER, 
        on_click=lambda e: pick_folder_result(),
        visible=not direct_folder,
        style=ft.ButtonStyle(
            bgcolor=ft.Colors.BLUE_GREY_800,
            color=ft.Colors.WHITE,
            shape=ft.RoundedRectangleBorder(radius=8)
        )
    )
    
    def show_snack(message, color=ft.Colors.RED_500):
        page.snack_bar = ft.SnackBar(ft.Text(message, color=ft.Colors.WHITE), bgcolor=color)
        page.snack_bar.open = True
        page.update()

    def show_dialog(title, content):
        dlg = ft.AlertDialog(
            title=ft.Text(title, weight=ft.FontWeight.BOLD),
            content=ft.Text(content, selectable=True), # Selectable so user can copy the key
            actions=[ft.TextButton("I have saved it", on_click=lambda e: close_dlg(dlg))],
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
                    
                    if direct_folder:
                        # Direct mode -> Open folder and close app
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
                    
                    msg = (
                        "Folder locked successfully!\n\n"
                        "IMPORTANT: Save this Recovery Key in a safe place.\n"
                        f"Recovery Key: {rec_key}"
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

    # Build Page structure
    page.add(
        ft.Container(height=10),
        logo,
        title_text,
        ft.Container(height=20),
        
        ft.Card(
            content=ft.Container(
                content=ft.Column(
                    [
                        select_btn,
                        folder_text,
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=10
                ),
                padding=20,
                width=350,
            ),
            elevation=5,
            color=ft.Colors.SURFACE_VARIANT
        ),
        
        ft.Container(height=10),
        password_field,
        recovery_checkbox,
        ft.Container(height=10),
        progress_bar,
        action_button
    )
    
    # Adjust for direct mode
    if direct_folder:
        page.window.width = 400
        page.window.height = 550
        title_text.value = "Unlock FolderDoor"
        update_ui_state()

if __name__ == "__main__":
    ft.app(target=main)
