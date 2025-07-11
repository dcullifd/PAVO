import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from datetime import datetime, timedelta
import re
from PIL import Image
from PIL.ExifTags import TAGS
import subprocess
import json
from collections import defaultdict
import shutil

class FileOrganizer:
    def __init__(self, root):
        self.root = root
        self.root.title("Photo/Video File Organizer")
        self.root.geometry("900x700")
        
        # Variables
        self.source_folder = tk.StringVar()
        self.custom_name = tk.StringVar()
        self.files_to_rename = []
        self.preview_data = []
        self.time_gap_threshold = tk.IntVar(value=120)
        
        # Supported file extensions
        self.image_extensions = {'.jpg', '.jpeg', '.png', '.tiff', '.bmp', '.gif'}
        self.video_extensions = {'.mp4', '.mov', '.avi', '.mkv', '.wmv', '.flv', '.webm'}
        self.supported_extensions = self.image_extensions | self.video_extensions
        
        self.create_widgets()
        
    def create_widgets(self):
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Tab 1: File Renaming
        self.rename_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.rename_frame, text="File Renaming")
        self.create_rename_tab()
        
        # Tab 2: File Organization
        self.organize_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.organize_frame, text="File Organization")
        self.create_organize_tab()
        
    def create_rename_tab(self):
        main_frame = ttk.Frame(self.rename_frame, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.rename_frame.columnconfigure(0, weight=1)
        self.rename_frame.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # Source folder selection
        ttk.Label(main_frame, text="Source Folder:").grid(row=0, column=0, sticky=tk.W, pady=5)
        ttk.Entry(main_frame, textvariable=self.source_folder, width=50).grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)
        ttk.Button(main_frame, text="Browse", command=self.browse_folder).grid(row=0, column=2, padx=5)
        
        # Custom name input
        ttk.Label(main_frame, text="Custom Name:").grid(row=1, column=0, sticky=tk.W, pady=5)
        ttk.Entry(main_frame, textvariable=self.custom_name, width=50).grid(row=1, column=1, sticky=(tk.W, tk.E), padx=5)
        
        # Buttons
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
        
        self.tree = ttk.Treeview(tree_frame, columns=('original', 'new', 'date_time'), show='headings')
        self.tree.heading('original', text='Original Name')
        self.tree.heading('new', text='New Name')
        self.tree.heading('date_time', text='Date/Time Source')
        
        self.tree.column('original', width=250)
        self.tree.column('new', width=250)
        self.tree.column('date_time', width=150)
        
        v_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        h_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        self.tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        v_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        h_scrollbar.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
    def create_organize_tab(self):
        org_main_frame = ttk.Frame(self.organize_frame, padding="10")
        org_main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.organize_frame.columnconfigure(0, weight=1)
        self.organize_frame.rowconfigure(0, weight=1)
        org_main_frame.columnconfigure(1, weight=1)
        
        # Instructions
        info_label = ttk.Label(org_main_frame, 
                              text="Use this tab after renaming files to organize them into folders by date and time periods.",
                              font=('TkDefaultFont', 9, 'italic'))
        info_label.grid(row=0, column=0, columnspan=3, pady=(0, 10), sticky=tk.W)
        
        # Folder to organize
        ttk.Label(org_main_frame, text="Folder to Organize:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.organize_folder = tk.StringVar()
        ttk.Entry(org_main_frame, textvariable=self.organize_folder, width=50).grid(row=1, column=1, sticky=(tk.W, tk.E), padx=5)
        ttk.Button(org_main_frame, text="Browse", command=self.browse_organize_folder).grid(row=1, column=2, padx=5)
        
        # Time gap threshold
        threshold_frame = ttk.Frame(org_main_frame)
        threshold_frame.grid(row=2, column=0, columnspan=3, pady=10, sticky=tk.W)
        
        ttk.Label(threshold_frame, text="Time gap for new session (minutes):").pack(side=tk.LEFT)
        ttk.Scale(threshold_frame, from_=30, to=300, orient=tk.HORIZONTAL, 
                 variable=self.time_gap_threshold, length=200).pack(side=tk.LEFT, padx=10)
        self.threshold_label = ttk.Label(threshold_frame, text="120")
        self.threshold_label.pack(side=tk.LEFT)
        
        self.time_gap_threshold.trace('w', self.update_threshold_label)
        
        # Organization options
        options_frame = ttk.LabelFrame(org_main_frame, text="Organization Options", padding="10")
        options_frame.grid(row=3, column=0, columnspan=3, pady=10, sticky=(tk.W, tk.E))
        
        self.separate_by_date = tk.BooleanVar(value=True)
        self.separate_by_session = tk.BooleanVar(value=True)
        self.separate_by_type = tk.BooleanVar(value=True)
        
        ttk.Checkbutton(options_frame, text="Separate by date", variable=self.separate_by_date).grid(row=0, column=0, sticky=tk.W)
        ttk.Checkbutton(options_frame, text="Separate by session (time gaps)", variable=self.separate_by_session).grid(row=0, column=1, sticky=tk.W, padx=20)
        ttk.Checkbutton(options_frame, text="Separate photos and videos", variable=self.separate_by_type).grid(row=0, column=2, sticky=tk.W, padx=20)
        
        # Organization buttons
        org_buttons_frame = ttk.Frame(org_main_frame)
        org_buttons_frame.grid(row=4, column=0, columnspan=3, pady=10)
        
        ttk.Button(org_buttons_frame, text="Analyze Files", command=self.analyze_files).pack(side=tk.LEFT, padx=5)
        ttk.Button(org_buttons_frame, text="Preview Organization", command=self.preview_organization).pack(side=tk.LEFT, padx=5)
        ttk.Button(org_buttons_frame, text="Apply Organization", command=self.apply_organization).pack(side=tk.LEFT, padx=5)
        
        # Organization progress
        self.org_progress = ttk.Progressbar(org_main_frame, mode='determinate')
        self.org_progress.grid(row=5, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        
        # Organization status
        self.org_status_label = ttk.Label(org_main_frame, text="Ready to organize files")
        self.org_status_label.grid(row=6, column=0, columnspan=3, pady=5)
        
        # Organization preview tree
        org_tree_frame = ttk.Frame(org_main_frame)
        org_tree_frame.grid(row=7, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)
        org_tree_frame.columnconfigure(0, weight=1)
        org_tree_frame.rowconfigure(0, weight=1)
        org_main_frame.rowconfigure(7, weight=1)
        
        self.org_tree = ttk.Treeview(org_tree_frame, columns=('file', 'datetime', 'destination'), show='headings')
        self.org_tree.heading('file', text='File Name')
        self.org_tree.heading('datetime', text='Date/Time')
        self.org_tree.heading('destination', text='Destination Folder')
        
        self.org_tree.column('file', width=200)
        self.org_tree.column('datetime', width=150)
        self.org_tree.column('destination', width=300)
        
        org_v_scrollbar = ttk.Scrollbar(org_tree_frame, orient=tk.VERTICAL, command=self.org_tree.yview)
        org_h_scrollbar = ttk.Scrollbar(org_tree_frame, orient=tk.HORIZONTAL, command=self.org_tree.xview)
        self.org_tree.configure(yscrollcommand=org_v_scrollbar.set, xscrollcommand=org_h_scrollbar.set)
        
        self.org_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        org_v_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        org_h_scrollbar.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        # Data storage
        self.analyzed_files = []
        self.organization_plan = []
        
    def update_threshold_label(self, *args):
        self.threshold_label.config(text=str(self.time_gap_threshold.get()))
        
    def browse_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.source_folder.set(folder)
            
    def browse_organize_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.organize_folder.set(folder)
            
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
        
        all_files = []
        for file_path in folder_path.iterdir():
            if file_path.is_file():
                if file_path.suffix.lower() in self.supported_extensions:
                    all_files.append(file_path)
            
        self.files_to_rename = sorted(list(set(all_files)))
        
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        for file_path in self.files_to_rename:
            self.tree.insert('', 'end', values=(file_path.name, '', 'Not processed'))
            
        self.status_label.config(text=f"Found {len(self.files_to_rename)} files")
        
    def get_image_datetime(self, file_path):
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
        try:
            cmd = ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', '-show_streams', str(file_path)]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                data = json.loads(result.stdout)
                if 'format' in data and 'tags' in data['format']:
                    tags = data['format']['tags']
                    for key in ['creation_time', 'date', 'com.apple.quicktime.creationdate']:
                        if key in tags:
                            try:
                                dt_str = tags[key]
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
        try:
            stat = file_path.stat()
            timestamp = getattr(stat, 'st_birthtime', None) or stat.st_mtime
            return datetime.fromtimestamp(timestamp), 'File System'
        except Exception:
            return datetime.now(), 'Current Time'
            
    def sanitize_filename(self, filename):
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
        
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        self.preview_data = []
        self.progress['maximum'] = len(self.files_to_rename)
        
        for i, file_path in enumerate(self.files_to_rename):
            self.progress['value'] = i + 1
            self.root.update_idletasks()
            
            dt = None
            dt_source = None
            
            if file_path.suffix.lower() in self.image_extensions:
                dt, dt_source = self.get_image_datetime(file_path)
            elif file_path.suffix.lower() in self.video_extensions:
                dt, dt_source = self.get_video_datetime(file_path)
                
            if dt is None:
                dt, dt_source = self.get_file_datetime(file_path)
                
            dt_str = dt.strftime('%d-%m-%y_%H.%M.%S')
            new_name = f"{custom_name}_{dt_str}{file_path.suffix}"
            
            self.preview_data.append({
                'original_path': file_path,
                'new_name': new_name,
                'datetime': dt,
                'dt_source': dt_source
            })
            
            self.tree.insert('', 'end', values=(file_path.name, new_name, dt_source))
            
        self.progress['value'] = 0
        self.status_label.config(text=f"Preview generated for {len(self.preview_data)} files")
        
    def apply_changes(self):
        if not self.preview_data:
            messagebox.showerror("Error", "Please generate preview first")
            return
            
        result = messagebox.askyesno("Confirm", f"Are you sure you want to rename {len(self.preview_data)} files?")
        if not result:
            return
            
        success_count = 0
        error_count = 0
        errors = []
        self.progress['maximum'] = len(self.preview_data)
        
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
                
                if not old_path.exists():
                    errors.append(f"{old_path.name}: Source file not found")
                    error_count += 1
                    continue
                
                if new_path.exists():
                    counter = 1
                    base_name = new_path.stem
                    extension = new_path.suffix
                    while new_path.exists():
                        new_name = f"{base_name}_{counter}{extension}"
                        new_path = old_path.parent / new_name
                        counter += 1
                
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
        
        if error_count == 0:
            message = f"Successfully renamed {success_count} files!\n\nYou can now use the 'File Organization' tab to organize them into folders."
            messagebox.showinfo("Success", message)
            self.organize_folder.set(self.source_folder.get())
            self.notebook.select(self.organize_frame)
        else:
            error_details = "\n".join(errors[:10])
            if len(errors) > 10:
                error_details += f"\n... and {len(errors) - 10} more errors"
                
            messagebox.showwarning("Partial Success", 
                                 f"Renamed {success_count} files successfully.\n"
                                 f"{error_count} files failed to rename.\n\n"
                                 f"Errors:\n{error_details}")
            
    def clear_all(self):
        self.files_to_rename = []
        self.preview_data = []
        
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        self.status_label.config(text="Ready")
        self.progress['value'] = 0
        
    def analyze_files(self):
        if not self.organize_folder.get():
            messagebox.showerror("Error", "Please select a folder to organize")
            return
            
        folder_path = Path(self.organize_folder.get())
        if not folder_path.exists():
            messagebox.showerror("Error", "Selected folder does not exist")
            return
            
        self.org_status_label.config(text="Analyzing files...")
        self.analyzed_files = []
        
        all_files = []
        for file_path in folder_path.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in self.supported_extensions:
                all_files.append(file_path)
                
        self.org_progress['maximum'] = len(all_files)
        
        for i, file_path in enumerate(all_files):
            self.org_progress['value'] = i + 1
            self.root.update_idletasks()
            
            dt = None
            dt_source = None
            
            if file_path.suffix.lower() in self.image_extensions:
                dt, dt_source = self.get_image_datetime(file_path)
            elif file_path.suffix.lower() in self.video_extensions:
                dt, dt_source = self.get_video_datetime(file_path)
                
            if dt is None:
                dt, dt_source = self.get_file_datetime(file_path)
                
            self.analyzed_files.append({
                'path': file_path,
                'datetime': dt,
                'dt_source': dt_source,
                'is_image': file_path.suffix.lower() in self.image_extensions,
                'is_video': file_path.suffix.lower() in self.video_extensions
            })
            
        self.analyzed_files.sort(key=lambda x: x['datetime'])
        
        self.org_progress['value'] = 0
        self.org_status_label.config(text=f"Analyzed {len(self.analyzed_files)} files")
        
    def preview_organization(self):
        if not self.analyzed_files:
            messagebox.showerror("Error", "Please analyze files first")
            return
            
        for item in self.org_tree.get_children():
            self.org_tree.delete(item)
            
        self.organization_plan = []
        
        groups = self.group_files_for_organization()
        
        for group_name, files in groups.items():
            for file_info in files:
                destination = self.get_destination_path(group_name, file_info)
                
                self.organization_plan.append({
                    'file_info': file_info,
                    'destination': destination
                })
                
                self.org_tree.insert('', 'end', values=(
                    file_info['path'].name,
                    file_info['datetime'].strftime('%d-%m-%y %H:%M:%S'),
                    str(destination.relative_to(Path(self.organize_folder.get())))
                ))
                
        self.org_status_label.config(text=f"Organization plan created for {len(self.organization_plan)} files")
        
    def group_files_for_organization(self):
        groups = defaultdict(list)
        
        current_session = 0
        last_datetime = None
        current_date = None
        
        for file_info in self.analyzed_files:
            dt = file_info['datetime']
            
            if self.separate_by_date.get():
                file_date = dt.date()
                if current_date != file_date:
                    current_date = file_date
                    current_session = 0
            
            if self.separate_by_session.get() and last_datetime:
                time_diff = (dt - last_datetime).total_seconds() / 60
                if time_diff > self.time_gap_threshold.get():
                    current_session += 1
            
            group_parts = []
            
            if self.separate_by_date.get():
                group_parts.append(dt.strftime('%Y-%m-%d'))
                
            if self.separate_by_session.get():
                if current_session > 0:
                    session_time = dt.strftime('%H.%M')
                    group_parts.append(f"Session{current_session + 1}_{session_time}")
                else:
                    session_time = dt.strftime('%H.%M')
                    group_parts.append(f"Session1_{session_time}")
                    
            if self.separate_by_type.get():
                if file_info['is_image']:
                    group_parts.append('Photos')
                elif file_info['is_video']:
                    group_parts.append('Videos')
                    
            group_key = '/'.join(group_parts) if group_parts else 'All_Files'
            groups[group_key].append(file_info)
            
            last_datetime = dt
            
        return groups
        
    def get_destination_path(self, group_name, file_info):
        base_path = Path(self.organize_folder.get())
        
        if group_name == 'All_Files':
            return base_path / file_info['path'].name
        else:
            folder_structure = Path(group_name)
            return base_path / folder_structure / file_info['path'].name
            
    def apply_organization(self):
        if not self.organization_plan:
            messagebox.showerror("Error", "Please preview organization first")
            return
            
        result = messagebox.askyesno("Confirm Organization", 
                                   f"Are you sure you want to organize {len(self.organization_plan)} files into folders?")
        if not result:
            return
            
        success_count = 0
        error_count = 0
        errors = []
        self.org_progress['maximum'] = len(self.organization_plan)
        
        for i, plan_item in enumerate(self.organization_plan):
            self.org_progress['value'] = i + 1
            self.root.update_idletasks()
            
            try:
                source_path = plan_item['file_info']['path']
                dest_path = plan_item['destination']
                
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                
                shutil.move(str(source_path), str(dest_path))
                success_count += 1
                
            except Exception as e:
                error_count += 1
                errors.append(f"{source_path.name}: {str(e)}")
                
        self.org_progress['value'] = 0
        
        if error_count == 0:
            messagebox.showinfo("Success", f"Successfully organized {success_count} files into folders!")
        else:
            error_details = "\n".join(errors[:10])
            if len(errors) > 10:
                error_details += f"\n... and {len(errors) - 10} more errors"
                
            messagebox.showwarning("Partial Success", 
                                 f"Organized {success_count} files successfully.\n"
                                 f"{error_count} files failed to organize.\n\n"
                                 f"Errors:\n{error_details}")
        
        self.clear_organization()
        
    def clear_organization(self):
        self.analyzed_files = []
        self.organization_plan = []
        
        for item in self.org_tree.get_children():
            self.org_tree.delete(item)
            
        self.org_status_label.config(text="Ready to organize files")
        self.org_progress['value'] = 0

def main():
    try:
        root = tk.Tk()
        app = FileOrganizer(root)
        root.mainloop()
    except Exception as e:
        try:
            import tkinter.messagebox as mb
            mb.showerror("Error", f"Failed to start application:\n{str(e)}")
        except:
            print(f"Error: {e}")
            input("Press Enter to exit...")

if __name__ == "__main__":
    main()