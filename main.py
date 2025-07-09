import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from datetime import datetime
import re
from PIL import Image
from PIL.ExifTags import TAGS
import subprocess
import json

class FileOrganizer:
    def __init__(self, root):
        self.root = root
        self.root.title("Photo/Video File Organizer")
        self.root.geometry("800x600")
        
        # Variables
        self.source_folder = tk.StringVar()
        self.custom_name = tk.StringVar()
        self.files_to_rename = []
        self.preview_data = []
        
        # Supported file extensions
        self.image_extensions = {'.jpg', '.jpeg', '.png', '.tiff', '.bmp', '.gif'}
        self.video_extensions = {'.mp4', '.mov', '.avi', '.mkv', '.wmv', '.flv', '.webm'}
        self.supported_extensions = self.image_extensions | self.video_extensions
        
        self.create_widgets()
        
    def create_widgets(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # Source folder selection
        ttk.Label(main_frame, text="Source Folder:").grid(row=0, column=0, sticky=tk.W, pady=5)
        ttk.Entry(main_frame, textvariable=self.source_folder, width=50).grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)
        ttk.Button(main_frame, text="Browse", command=self.browse_folder).grid(row=0, column=2, padx=5)
        
        # Custom name input
        ttk.Label(main_frame, text="Custom Name:").grid(row=1, column=0, sticky=tk.W, pady=5)
        ttk.Entry(main_frame, textvariable=self.custom_name, width=50).grid(row=1, column=1, sticky=(tk.W, tk.E), padx=5)
        
        # Buttons frame
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.grid(row=2, column=0, columnspan=3, pady=10)
        
        ttk.Button(buttons_frame, text="Scan Files", command=self.scan_files).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Preview Changes", command=self.preview_changes).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Apply Changes", command=self.apply_changes).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Clear", command=self.clear_all).pack(side=tk.LEFT, padx=5)
        
        # Progress bar
        self.progress = ttk.Progressbar(main_frame, mode='determinate')
        self.progress.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        
        # Status label
        self.status_label = ttk.Label(main_frame, text="Ready")
        self.status_label.grid(row=4, column=0, columnspan=3, pady=5)
        
        # Treeview for file preview
        tree_frame = ttk.Frame(main_frame)
        tree_frame.grid(row=5, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)
        main_frame.rowconfigure(5, weight=1)
        
        # Treeview with scrollbars
        self.tree = ttk.Treeview(tree_frame, columns=('original', 'new', 'date_time'), show='headings')
        self.tree.heading('original', text='Original Name')
        self.tree.heading('new', text='New Name')
        self.tree.heading('date_time', text='Date/Time Source')
        
        # Configure column widths
        self.tree.column('original', width=250)
        self.tree.column('new', width=250)
        self.tree.column('date_time', width=150)
        
        # Scrollbars
        v_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        h_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # Grid layout for treeview and scrollbars
        self.tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        v_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        h_scrollbar.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
    def browse_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.source_folder.set(folder)
            
    def scan_files(self):
        if not self.source_folder.get():
            messagebox.showerror("Error", "Please select a source folder")
            return
            
        folder_path = Path(self.source_folder.get())
        if not folder_path.exists():
            messagebox.showerror("Error", "Selected folder does not exist")
            return
            
        self.status_label.config(text="Scanning files...")
        self.files_to_rename = []
        
        # Get all files in the folder
        all_files = []
        for file_path in folder_path.iterdir():
            if file_path.is_file():
                # Check if the file extension (case-insensitive) is supported
                if file_path.suffix.lower() in self.supported_extensions:
                    all_files.append(file_path)
            
        # Remove duplicates and sort
        self.files_to_rename = sorted(list(set(all_files)))
        
        # Clear previous results
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        # Display found files
        for file_path in self.files_to_rename:
            self.tree.insert('', 'end', values=(file_path.name, '', 'Not processed'))
            
        self.status_label.config(text=f"Found {len(self.files_to_rename)} files")
        
    def get_image_datetime(self, file_path):
        """Extract datetime from image EXIF data"""
        try:
            with Image.open(file_path) as img:
                exif_data = img._getexif()
                if exif_data:
                    for tag_id, value in exif_data.items():
                        tag = TAGS.get(tag_id, tag_id)
                        if tag in ['DateTime', 'DateTimeOriginal', 'DateTimeDigitized']:
                            return datetime.strptime(value, '%Y:%m:%d %H:%M:%S'), 'EXIF'
        except Exception:
            pass
        return None, None
        
    def get_video_datetime(self, file_path):
        """Extract datetime from video metadata using ffprobe"""
        try:
            cmd = [
                'ffprobe', '-v', 'quiet', '-print_format', 'json',
                '-show_format', '-show_streams', str(file_path)
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                data = json.loads(result.stdout)
                
                # Try to get creation time from format
                if 'format' in data and 'tags' in data['format']:
                    tags = data['format']['tags']
                    for key in ['creation_time', 'date', 'com.apple.quicktime.creationdate']:
                        if key in tags:
                            try:
                                dt_str = tags[key]
                                # Handle different datetime formats
                                for fmt in ['%Y-%m-%dT%H:%M:%S.%fZ', '%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%SZ']:
                                    try:
                                        return datetime.strptime(dt_str, fmt), 'Metadata'
                                    except ValueError:
                                        continue
                            except ValueError:
                                continue
        except Exception:
            pass
        return None, None
        
    def get_file_datetime(self, file_path):
        """Get datetime from file system"""
        try:
            stat = file_path.stat()
            # Use creation time if available, otherwise modification time
            timestamp = getattr(stat, 'st_birthtime', None) or stat.st_mtime
            return datetime.fromtimestamp(timestamp), 'File System'
        except Exception:
            return datetime.now(), 'Current Time'
            
    def sanitize_filename(self, filename):
        """Remove invalid characters from filename"""
        # Remove invalid characters for Windows filenames
        invalid_chars = r'[<>:"/\\|?*]'
        return re.sub(invalid_chars, '', filename)
        
    def preview_changes(self):
        if not self.files_to_rename:
            messagebox.showerror("Error", "Please scan files first")
            return
            
        if not self.custom_name.get().strip():
            messagebox.showerror("Error", "Please enter a custom name")
            return
            
        custom_name = self.sanitize_filename(self.custom_name.get().strip())
        
        # Clear previous preview
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        self.preview_data = []
        self.progress['maximum'] = len(self.files_to_rename)
        
        for i, file_path in enumerate(self.files_to_rename):
            self.progress['value'] = i + 1
            self.root.update_idletasks()
            
            # Get datetime
            dt = None
            dt_source = None
            
            if file_path.suffix.lower() in self.image_extensions:
                dt, dt_source = self.get_image_datetime(file_path)
            elif file_path.suffix.lower() in self.video_extensions:
                dt, dt_source = self.get_video_datetime(file_path)
                
            if dt is None:
                dt, dt_source = self.get_file_datetime(file_path)
                
            # Create new filename
            dt_str = dt.strftime('%d-%m-%y_%H.%M.%S')  # Changed to dots
            new_name = f"{custom_name}_{dt_str}{file_path.suffix}"
            
            # Store preview data
            self.preview_data.append({
                'original_path': file_path,
                'new_name': new_name,
                'datetime': dt,
                'dt_source': dt_source
            })
            
            # Add to treeview
            self.tree.insert('', 'end', values=(file_path.name, new_name, dt_source))
            
        self.progress['value'] = 0
        self.status_label.config(text=f"Preview generated for {len(self.preview_data)} files")
        
    def apply_changes(self):
        if not self.preview_data:
            messagebox.showerror("Error", "Please generate preview first")
            return
            
        # Confirm action
        result = messagebox.askyesno("Confirm", 
                                   f"Are you sure you want to rename {len(self.preview_data)} files?")
        if not result:
            return
            
        success_count = 0
        error_count = 0
        errors = []
        self.progress['maximum'] = len(self.preview_data)
        
        # Test write permissions first
        test_file = Path(self.source_folder.get()) / "test_write_permissions.tmp"
        try:
            test_file.write_text("test")
            test_file.unlink()
        except Exception as e:
            messagebox.showerror("Permission Error", 
                               f"Cannot write to destination folder:\n{e}\n\n"
                               f"Try running as administrator or check folder permissions.")
            return
        
        for i, item in enumerate(self.preview_data):
            self.progress['value'] = i + 1
            self.root.update_idletasks()
            
            try:
                old_path = item['original_path']
                new_path = old_path.parent / item['new_name']
                
                # Check if source file exists and is accessible
                if not old_path.exists():
                    errors.append(f"{old_path.name}: Source file not found")
                    error_count += 1
                    continue
                
                # Check if target file already exists
                if new_path.exists():
                    # Add number suffix to make unique
                    counter = 1
                    base_name = new_path.stem
                    extension = new_path.suffix
                    while new_path.exists():
                        new_name = f"{base_name}_{counter}{extension}"
                        new_path = old_path.parent / new_name
                        counter += 1
                
                # Try to rename
                old_path.rename(new_path)
                success_count += 1
                
            except PermissionError as e:
                error_count += 1
                errors.append(f"{old_path.name}: Permission denied - file may be in use")
                
            except OSError as e:
                error_count += 1
                if "being used by another process" in str(e):
                    errors.append(f"{old_path.name}: File is open in another program")
                else:
                    errors.append(f"{old_path.name}: {str(e)}")
                    
            except Exception as e:
                error_count += 1
                errors.append(f"{old_path.name}: {str(e)}")
                
        self.progress['value'] = 0
        
        # Show results
        if error_count == 0:
            messagebox.showinfo("Success", f"Successfully renamed {success_count} files!")
        else:
            error_details = "\n".join(errors[:10])  # Show first 10 errors
            if len(errors) > 10:
                error_details += f"\n... and {len(errors) - 10} more errors"
                
            messagebox.showwarning("Partial Success", 
                                 f"Renamed {success_count} files successfully.\n"
                                 f"{error_count} files failed to rename.\n\n"
                                 f"Errors:\n{error_details}")
            
        # Clear data
        self.clear_all()
        
    def clear_all(self):
        """Clear all data and reset the interface"""
        self.files_to_rename = []
        self.preview_data = []
        
        # Clear treeview
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        self.status_label.config(text="Ready")
        self.progress['value'] = 0

def main():
    try:
        root = tk.Tk()
        app = FileOrganizer(root)
        root.mainloop()
    except Exception as e:
        # Show error in a message box if GUI fails
        try:
            import tkinter.messagebox as mb
            mb.showerror("Error", f"Failed to start application:\n{str(e)}")
        except:
            print(f"Error: {e}")
            input("Press Enter to exit...")

if __name__ == "__main__":
    main()

