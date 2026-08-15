import customtkinter as ctk
from tkinter import filedialog, messagebox
import locker
import os
import threading
import sys
from PIL import Image

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

class FolderLockerApp(ctk.CTk):
    def __init__(self, direct_folder_path=None):
        super().__init__()
        
        self.direct_mode = direct_folder_path is not None
        self.selected_folder = direct_folder_path
        
        icon_path = r"C:\Users\2021icts36\Desktop\Folderlocker_build\Folderlocker\Folderlocker.ico"
        
        try:
            logo_image = ctk.CTkImage(light_image=Image.open(icon_path), dark_image=Image.open(icon_path), size=(64, 64))
        except Exception:
            logo_image = None

        if self.direct_mode:
            self.title("Unlock FolderDoor")
            self.geometry("380x400")
            self.resizable(False, False)
            if os.path.exists(icon_path):
                self.iconbitmap(icon_path)
            
            if logo_image:
                self.logo_label = ctk.CTkLabel(self, image=logo_image, text="")
                self.logo_label.pack(pady=(20, 0))
            
            self.title_label = ctk.CTkLabel(self, text="Unlock Secure Folder", font=ctk.CTkFont(size=20, weight="bold"))
            self.title_label.pack(pady=(10, 10))
            
            self.password_entry = ctk.CTkEntry(self, placeholder_text="Enter Password or Recovery Key", show="*", width=250)
            self.password_entry.pack(pady=5)
            
            self.show_password_var = ctk.BooleanVar(value=False)
            self.show_password_cb = ctk.CTkCheckBox(self, text="Show Password", variable=self.show_password_var, command=self.toggle_password_visibility)
            self.show_password_cb.pack(pady=5)
            
            self.recovery_var = ctk.BooleanVar(value=False)
            self.recovery_cb = ctk.CTkCheckBox(self, text="Use Recovery Key", variable=self.recovery_var)
            self.recovery_cb.pack(pady=5)
            
            self.progress_bar = ctk.CTkProgressBar(self, width=250)
            self.progress_bar.pack(pady=10)
            self.progress_bar.set(0)
            
            self.action_btn = ctk.CTkButton(self, text="Unlock", command=self.start_action_thread, fg_color="#28a745", hover_color="#218838")
            self.action_btn.pack(pady=10)
            
        else:
            self.title("FolderDoor")
            self.geometry("450x500")
            self.resizable(False, False)
            if os.path.exists(icon_path):
                self.iconbitmap(icon_path)
            
            if logo_image:
                self.logo_label = ctk.CTkLabel(self, image=logo_image, text="")
                self.logo_label.pack(pady=(20, 0))
                
            self.title_label = ctk.CTkLabel(self, text="FolderDoor", font=ctk.CTkFont(size=24, weight="bold"))
            self.title_label.pack(pady=(10, 10))
            
            self.folder_btn = ctk.CTkButton(self, text="Select Folder", command=self.select_folder)
            self.folder_btn.pack(pady=10)
            
            self.folder_label = ctk.CTkLabel(self, text="No folder selected", text_color="gray")
            self.folder_label.pack(pady=(0, 10))
            
            self.password_entry = ctk.CTkEntry(self, placeholder_text="Enter Password", show="*", width=250)
            self.password_entry.pack(pady=5)
            
            self.show_password_var = ctk.BooleanVar(value=False)
            self.show_password_cb = ctk.CTkCheckBox(self, text="Show Password", variable=self.show_password_var, command=self.toggle_password_visibility)
            self.show_password_cb.pack(pady=5)
            
            self.recovery_var = ctk.BooleanVar(value=False)
            self.recovery_cb = ctk.CTkCheckBox(self, text="Use Recovery Key", variable=self.recovery_var)
            
            self.progress_bar = ctk.CTkProgressBar(self, width=250)
            self.progress_bar.pack(pady=15)
            self.progress_bar.set(0)
            
            self.action_btn = ctk.CTkButton(self, text="Lock / Unlock", state="disabled", command=self.start_action_thread)
            self.action_btn.pack(pady=10)

    def toggle_password_visibility(self):
        if self.show_password_var.get():
            self.password_entry.configure(show="")
        else:
            self.password_entry.configure(show="*")
            
    def select_folder(self):
        folder = filedialog.askdirectory(title="Select Folder to Lock/Unlock")
        if folder:
            self.selected_folder = folder
            self.folder_label.configure(text=f"...{folder[-30:]}" if len(folder) > 30 else folder, text_color=("black", "white"))
            
            if locker.is_locked(folder):
                self.action_btn.configure(text="Unlock Folder", state="normal", fg_color="#28a745", hover_color="#218838")
                self.recovery_cb.pack(pady=5)
                self.password_entry.configure(placeholder_text="Enter Password or Recovery Key")
            else:
                self.action_btn.configure(text="Lock Folder", state="normal", fg_color="#dc3545", hover_color="#c82333")
                self.recovery_cb.pack_forget()
                self.recovery_var.set(False)
                self.password_entry.configure(placeholder_text="Enter Password")
                
            self.progress_bar.set(0)

    def update_progress(self, current, total):
        if total > 0:
            percentage = current / total
            self.after(0, lambda: self.progress_bar.set(percentage))

    def start_action_thread(self):
        thread = threading.Thread(target=self.perform_action)
        thread.start()

    def perform_action(self):
        if not self.selected_folder:
            return
            
        password = self.password_entry.get()
        if not password:
            self.after(0, lambda: messagebox.showwarning("Warning", "Please enter a password!"))
            return
            
        self.after(0, lambda: self.action_btn.configure(state="disabled", text="Processing..."))
        self.after(0, lambda: self.progress_bar.set(0))
        
        is_locked = locker.is_locked(self.selected_folder)
        is_recovery = self.recovery_var.get()
        
        try:
            if is_locked:
                unlocked_path = locker.unlock_folder(
                    self.selected_folder, 
                    password, 
                    is_recovery=is_recovery,
                    progress_callback=self.update_progress
                )
                if self.direct_mode:
                    self.after(0, lambda: self.direct_success(unlocked_path))
                else:
                    self.after(0, lambda: self.success_callback("Folder unlocked successfully!", "Lock Folder", "#dc3545", "#c82333"))
            else:
                recovery_key = locker.lock_folder(
                    self.selected_folder, 
                    password,
                    progress_callback=self.update_progress
                )
                
                success_msg = (
                    "Folder locked successfully!\n\n"
                    "IMPORTANT: Save this Recovery Key in a safe place.\n"
                    "If you forget your password, you will need this key to unlock the folder.\n\n"
                    f"Recovery Key:\n{recovery_key}"
                )
                self.after(0, lambda: self.success_callback(success_msg, "Unlock Folder", "#28a745", "#218838", True))
                
        except ValueError as ve:
            self.after(0, lambda: self.error_callback(str(ve), is_locked))
        except Exception as e:
            self.after(0, lambda: self.error_callback(f"An error occurred: {str(e)}", is_locked))

    def direct_success(self, unlocked_path):
        os.startfile(unlocked_path)
        self.destroy()

    def success_callback(self, msg, new_btn_text, fg_color, hover_color, is_lock=False):
        messagebox.showinfo("Success", msg)
        self.action_btn.configure(text=new_btn_text, fg_color=fg_color, hover_color=hover_color, state="normal")
        self.password_entry.delete(0, 'end')
        
        if not self.direct_mode:
            if is_lock:
                self.recovery_cb.pack(pady=5)
                self.password_entry.configure(placeholder_text="Enter Password or Recovery Key")
            else:
                self.selected_folder = None
                self.folder_label.configure(text="No folder selected", text_color="gray")
                self.action_btn.configure(state="disabled")
                self.recovery_cb.pack_forget()

    def error_callback(self, msg, is_locked):
        messagebox.showerror("Error", msg)
        btn_text = "Unlock Folder" if is_locked else "Lock Folder"
        if self.direct_mode:
            btn_text = "Unlock"
        fg_color = "#28a745" if is_locked else "#dc3545"
        hover_color = "#218838" if is_locked else "#c82333"
        self.action_btn.configure(text=btn_text, fg_color=fg_color, hover_color=hover_color, state="normal")
        self.progress_bar.set(0)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        folder_to_unlock = sys.argv[1]
        app = FolderLockerApp(direct_folder_path=folder_to_unlock)
    else:
        app = FolderLockerApp()
    app.mainloop()
