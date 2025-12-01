import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os
import threading
from pathlib import Path
import sys

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
        self.root.geometry("600x400")

        self.setup_ui()

    def setup_ui(self):
        # Main container
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title
        title_label = ttk.Label(main_frame, text="Batch Background Remover", font=("Helvetica", 16, "bold"))
        title_label.pack(pady=(0, 20))

        # Instructions
        instructions = "Select a directory containing PNG images.\nThe app will remove backgrounds and save them to a new folder."
        lbl_instructions = ttk.Label(main_frame, text=instructions, justify=tk.CENTER)
        lbl_instructions.pack(pady=(0, 20))

        # Select Button
        self.btn_select = ttk.Button(main_frame, text="Select Directory", command=self.select_directory)
        self.btn_select.pack(pady=(0, 20), ipadx=10, ipady=5)

        # Progress Bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(main_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X, pady=(0, 10))

        # Status Label
        self.status_var = tk.StringVar(value="Ready")
        self.lbl_status = ttk.Label(main_frame, textvariable=self.status_var)
        self.lbl_status.pack(pady=(0, 10))

        # Log Area
        self.log_text = tk.Text(main_frame, height=10, width=50, state=tk.DISABLED)
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

    def select_directory(self):
        directory = filedialog.askdirectory()
        if directory:
            self.start_processing(directory)

    def start_processing(self, directory):
        self.btn_select.config(state=tk.DISABLED)
        self.progress_var.set(0)
        self.status_var.set("Starting processing...")
        
        # Run in a separate thread to keep UI responsive
        thread = threading.Thread(target=self.process_images, args=(directory,))
        thread.daemon = True
        thread.start()

    def process_images(self, input_dir_str):
        input_dir = Path(input_dir_str)
        dir_name = input_dir.name
        
        # Define output directory structure
        # /home/fishman/Tools_Tam/background-remover/backgroundremover-for-microscope/background-removed/{dir_name}_backgournd-removed/
        base_output_path = Path("/home/fishman/Tools_Tam/background-remover/backgroundremover-for-microscope/background-removed")
        output_dir = base_output_path / f"{dir_name}_backgournd-removed"
        
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
            self.log(f"Output directory created: {output_dir}")
        except Exception as e:
            self.log(f"Error creating output directory: {e}")
            self.root.after(0, self.processing_finished)
            return

        # Find PNG files
        png_files = list(input_dir.glob("*.png"))
        if not png_files:
            self.log("No PNG files found in the selected directory.")
            self.root.after(0, self.processing_finished)
            return

        total_files = len(png_files)
        self.log(f"Found {total_files} PNG files.")

        for i, file_path in enumerate(png_files):
            try:
                self.status_var.set(f"Processing {file_path.name} ({i+1}/{total_files})")
                self.log(f"Processing: {file_path.name}")

                # Read image
                with open(file_path, "rb") as f:
                    data = f.read()

                # Remove background
                # Using default u2net model
                img_data = remove(data, model_name="u2net")

                # Save output
                # original_name.png -> original_name_nobg.png
                output_filename = f"{file_path.stem}_nobg.png"
                output_path = output_dir / output_filename

                with open(output_path, "wb") as f:
                    f.write(img_data)
                
                self.log(f"Saved: {output_filename}")

            except Exception as e:
                self.log(f"Error processing {file_path.name}: {e}")

            # Update progress
            progress = ((i + 1) / total_files) * 100
            self.root.after(0, lambda p=progress: self.progress_var.set(p))

        self.root.after(0, self.processing_finished)

    def processing_finished(self):
        self.status_var.set("Processing complete!")
        self.log("All tasks finished.")
        self.btn_select.config(state=tk.NORMAL)
        messagebox.showinfo("Done", "Background removal process completed.")

if __name__ == "__main__":
    root = tk.Tk()
    app = BackgroundRemoverApp(root)
    root.mainloop()
