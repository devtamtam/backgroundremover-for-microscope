import sys
import os
from PIL import Image
import tkinter as tk
from tkinter import filedialog, messagebox

def count_pixels(image_path):
    """
    Counts the number of non-transparent pixels in an image.
    Assumes the image has an alpha channel or converts it to RGBA.
    """
    try:
        img = Image.open(image_path)
        img = img.convert("RGBA")
        datas = img.getdata()

        non_transparent_count = 0
        for item in datas:
            # item is (r, g, b, a)
            if item[3] > 0:  # Check alpha channel
                non_transparent_count += 1
        
        total_pixels = img.size[0] * img.size[1]
        return non_transparent_count, total_pixels
    except Exception as e:
        return None, str(e)

def main():
    image_path = None
    use_gui = len(sys.argv) == 1
    
    if not use_gui:
        image_path = sys.argv[1]
    else:
        # Initialize Tkinter
        root = tk.Tk()
        root.withdraw() # Hide the main window
        
        image_path = filedialog.askopenfilename(
            title="Select an Image",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp *.gif *.tiff")]
        )
        
        if not image_path:
            print("No file selected.")
            root.destroy()
            return

    if not os.path.exists(image_path):
        msg = f"Error: File '{image_path}' not found."
        print(msg)
        if use_gui:
            messagebox.showerror("Error", msg)
            root.destroy()
        return

    print(f"Processing: {image_path}")
    non_transparent_count, total_or_error = count_pixels(image_path)

    if non_transparent_count is not None:
        result_msg = (f"Image: {os.path.basename(image_path)}\n"
                      f"Non-transparent pixels: {non_transparent_count}\n"
                      f"Total pixels: {total_or_error}")
        print(result_msg)
        
        if use_gui:
            messagebox.showinfo("Pixel Count Result", result_msg)
    else:
        error_msg = f"Error processing image: {total_or_error}"
        print(error_msg)
        if use_gui:
            messagebox.showerror("Error", error_msg)

    if use_gui:
        root.destroy()

if __name__ == "__main__":
    main()
