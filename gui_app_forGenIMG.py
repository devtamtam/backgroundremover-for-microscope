import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os
import threading
from pathlib import Path
import sys
import shutil
import time
import datetime

# Add the current directory to sys.path to ensure we can import backgroundremover
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from backgroundremover.bg import remove
except ImportError:
    messagebox.showerror("Error", "Could not import backgroundremover. Make sure it is installed.")
    sys.exit(1)

class BackgroundRemoverApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Batch Background Remover")
        self.root.geometry("800x600")

        self.directories = [] # List of Path objects
        self.processing = False

        self.setup_ui()

    def setup_ui(self):
        # Main container
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title
        title_label = ttk.Label(main_frame, text="Batch Background Remover", font=("Helvetica", 16, "bold"))
        title_label.pack(pady=(0, 10))

        # Instructions
        instructions = "Add directories like 'output_CcGAN...'. Click 'Start Processing' to begin."
        lbl_instructions = ttk.Label(main_frame, text=instructions, justify=tk.CENTER)
        lbl_instructions.pack(pady=(0, 10))

        # Buttons Frame
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(pady=(0, 10))

        self.btn_add = ttk.Button(btn_frame, text="Add Directory", command=self.add_directory)
        self.btn_add.pack(side=tk.LEFT, padx=5)

        self.btn_clear = ttk.Button(btn_frame, text="Clear List", command=self.clear_list)
        self.btn_clear.pack(side=tk.LEFT, padx=5)

        self.btn_start = ttk.Button(btn_frame, text="Start Processing", command=self.start_processing)
        self.btn_start.pack(side=tk.LEFT, padx=5)

        # Treeview for Directories
        columns = ("path", "status", "progress")
        self.tree = ttk.Treeview(main_frame, columns=columns, show="headings", height=8)
        self.tree.heading("path", text="Directory Path")
        self.tree.heading("status", text="Status")
        self.tree.heading("progress", text="Progress")
        
        self.tree.column("path", width=400)
        self.tree.column("status", width=100)
        self.tree.column("progress", width=100)
        
        self.tree.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # ETC Label
        self.lbl_etc = ttk.Label(main_frame, text="Estimated Time Remaining: --:--", font=("Helvetica", 10, "bold"))
        self.lbl_etc.pack(pady=(0, 5))

        # Overall Progress Bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(main_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X, pady=(0, 10))

        # Status Label
        self.status_var = tk.StringVar(value="Ready")
        self.lbl_status = ttk.Label(main_frame, textvariable=self.status_var)
        self.lbl_status.pack(pady=(0, 10))

        # Log Area
        self.log_text = tk.Text(main_frame, height=8, width=50, state=tk.DISABLED)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # Scrollbar for log
        scrollbar = ttk.Scrollbar(self.log_text, orient="vertical", command=self.log_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=scrollbar.set)

    def log(self, message):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def add_directory(self):
        directory = filedialog.askdirectory()
        if directory:
            path_obj = Path(directory)
            if path_obj not in self.directories:
                self.directories.append(path_obj)
                self.tree.insert("", tk.END, values=(str(path_obj), "Waiting", "0%"))
            else:
                messagebox.showinfo("Info", "Directory already added.")

    def clear_list(self):
        if self.processing:
            return
        self.directories = []
        for item in self.tree.get_children():
            self.tree.delete(item)

    def start_processing(self):
        if not self.directories:
            messagebox.showwarning("Warning", "No directories added.")
            return
        
        self.processing = True
        self.btn_add.config(state=tk.DISABLED)
        self.btn_clear.config(state=tk.DISABLED)
        self.btn_start.config(state=tk.DISABLED)
        self.progress_var.set(0)
        self.status_var.set("Starting processing...")
        
        # Run in a separate thread
        thread = threading.Thread(target=self.process_queue)
        thread.daemon = True
        thread.start()

    def update_tree_status(self, index, status, progress):
        # Treeview items are 0-indexed corresponding to self.directories
        items = self.tree.get_children()
        if 0 <= index < len(items):
            item_id = items[index]
            current_values = self.tree.item(item_id, "values")
            # values = (path, status, progress)
            new_values = (current_values[0], status, progress)
            self.tree.item(item_id, values=new_values)

    def format_time(self, seconds):
        if seconds < 0: seconds = 0
        return str(datetime.timedelta(seconds=int(seconds)))

    def process_queue(self):
        total_images_all_dirs = 0
        tasks = [] # List of (dir_index, type, source, dest)
                   # type='image': source=image_path, dest=output_path
                   # type='csv': source=csv_path, dest=output_path

        # First pass: Scan and prepare work
        for i, input_dir in enumerate(self.directories):
            self.update_tree_status(i, "Scanning...", "0%")
            
            # Construct Base Output Directory Name: {Input_Dir}_bg_removed
            # If input_dir is "output_CcGAN...", output is "output_CcGAN..._bg_removed"
            output_base_dir_name = input_dir.name + "_bg_removed"
            output_base_dir = input_dir.parent / output_base_dir_name
            
            saved_images_dir = input_dir / "saved_images"
            if not saved_images_dir.exists():
                self.log(f"Skipping {input_dir.name}: 'saved_images' folder not found.")
                items = list(input_dir.glob("*.png")) # Fallback to old behavior? Or just error?
                # The user requirement is specific. I will scan recursively just in case or strict?
                # Strict adherence to requested structure:
                # But let's look for saved_images. Only process if structure matches.
                self.update_tree_status(i, "Invalid Struct", "0%")
                continue

            # Iterate over model folders inside saved_images
            for model_dir in saved_images_dir.iterdir():
                if not model_dir.is_dir(): continue
                
                # Iterate over numbered folders (1000, 2000, ...)
                for numbered_dir in model_dir.iterdir():
                    if not numbered_dir.is_dir(): continue
                    # Check if it looks like a number (optional, but good safety)
                    # User said "number foder like 2000"
                    
                    target_numbered_dir = output_base_dir / numbered_dir.name
                    target_images_dir = target_numbered_dir / "images"

                    # 1. Look for test.csv
                    test_csv_path = numbered_dir / "test.csv"
                    if test_csv_path.exists():
                        target_csv_path = target_numbered_dir / "data.csv"
                        tasks.append((i, 'csv', test_csv_path, target_csv_path))
                    
                    # 2. Look for images in 'test' folder
                    test_images_dir = numbered_dir / "test"
                    if test_images_dir.exists() and test_images_dir.is_dir():
                        # Gather images
                        # User mentioned "hoge.img". I'll assume standard extensions.
                        # Using broad glob for images
                        for ext in ["*.png", "*.jpg", "*.jpeg", "*.bmp"]:
                            for img_path in test_images_dir.glob(ext):
                                output_filename = f"{img_path.stem}_nobg.png"
                                output_path = target_images_dir / output_filename
                                tasks.append((i, 'image', img_path, output_path))
            
            self.update_tree_status(i, "Waiting", "0%")

        # Filter image tasks for total count
        image_tasks = [t for t in tasks if t[1] == 'image']
        total_images_all_dirs = len(image_tasks)
        
        if not tasks:
            self.root.after(0, lambda: self.finish_processing("No valid tasks found."))
            return

        self.log(f"Total images to process: {total_images_all_dirs}")
        self.log(f"Total CSVs to move: {len([t for t in tasks if t[1] == 'csv'])}")

        start_time = time.time()
        processed_images_count = 0
        
        # Track progress per directory
        # We need to map tasks back to directory index `i`
        dir_progress_map = {i: {"total_images": 0, "processed_images": 0} for i in range(len(self.directories))}
        for t in image_tasks:
            dir_progress_map[t[0]]["total_images"] += 1

        # Mark first directory as Processing
        current_dir_idx = tasks[0][0]
        self.root.after(0, lambda: self.update_tree_status(current_dir_idx, "Processing", "0%"))
        last_dir_idx = -1

        for task in tasks:
            i, type_, source, dest = task
            
            # Update directory status if changed
            if i != last_dir_idx:
                if last_dir_idx != -1:
                     self.root.after(0, lambda idx=last_dir_idx: self.update_tree_status(idx, "DONE", "100%"))
                self.root.after(0, lambda idx=i: self.update_tree_status(idx, "Processing", 
                    f"{int((dir_progress_map[idx]['processed_images']/dir_progress_map[idx]['total_images'])*100) if dir_progress_map[idx]['total_images'] > 0 else 0}%"))
                last_dir_idx = i

            try:
                # Ensure parent dir exists
                dest.parent.mkdir(parents=True, exist_ok=True)

                if type_ == 'csv':
                    shutil.copy2(source, dest)
                    # self.log(f"Copied CSV: {dest}") # Verbose logging can be reduced

                elif type_ == 'image':
                    self.status_var.set(f"Processing {source.name}...")
                    
                    with open(source, "rb") as f:
                        data = f.read()

                    # Remove background
                    img_data = remove(data, model_name="u2net")

                    with open(dest, "wb") as f:
                        f.write(img_data)
                    
                    processed_images_count += 1
                    dir_progress_map[i]["processed_images"] += 1
                    
                    # Update directory progress
                    total_imgs = dir_progress_map[i]["total_images"]
                    if total_imgs > 0:
                        dir_percent = int((dir_progress_map[i]["processed_images"] / total_imgs) * 100)
                        self.root.after(0, lambda idx=i, p=dir_percent: self.update_tree_status(idx, "Processing", f"{p}%"))

                    # Update overall progress
                    overall_percent = (processed_images_count / total_images_all_dirs) * 100
                    self.root.after(0, lambda p=overall_percent: self.progress_var.set(p))

                    # Update ETC
                    elapsed_time = time.time() - start_time
                    avg_time_per_image = elapsed_time / processed_images_count
                    remaining_images = total_images_all_dirs - processed_images_count
                    etc_seconds = avg_time_per_image * remaining_images
                    etc_str = self.format_time(etc_seconds)
                    
                    self.root.after(0, lambda t=etc_str: self.lbl_etc.config(text=f"Estimated Time Remaining: {t}"))

            except Exception as e:
                self.log(f"Error processing {source}: {e}")

        # Mark last directory as DONE
        if last_dir_idx != -1:
             self.root.after(0, lambda idx=last_dir_idx: self.update_tree_status(idx, "DONE", "100%"))

        self.root.after(0, lambda: self.finish_processing("All tasks finished."))

    def finish_processing(self, msg):
        self.processing = False
        self.status_var.set("Processing complete!")
        self.log(msg)
        self.btn_add.config(state=tk.NORMAL)
        self.btn_clear.config(state=tk.NORMAL)
        self.btn_start.config(state=tk.NORMAL)
        self.lbl_etc.config(text="Estimated Time Remaining: 0:00:00")
        messagebox.showinfo("Done", msg)

if __name__ == "__main__":
    root = tk.Tk()
    app = BackgroundRemoverApp(root)
    root.mainloop()
