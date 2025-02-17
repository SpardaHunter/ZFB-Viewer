import os
import struct
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk

class ZFBViewer(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ZFB Viewer")
        self.geometry("900x800")
        
        self.folder_path = tk.StringVar()
        
        # Crear un canvas con un tamaño de 640x480
        self.canvas = tk.Canvas(self, width=640, height=480, bg="gray")
        self.canvas.pack(pady=20)
        
        # Crear tabla con columnas Nombre y Path
        self.tree = ttk.Treeview(self, columns=("Name", "Path"), show="headings", height=5)
        self.tree.heading("Name", text="Name")
        self.tree.heading("Path", text="Path")
        self.tree.pack(fill=tk.BOTH, expand=False, padx=20, pady=10)
        self.tree.bind("<Double-1>", self.edit_path)
        self.tree.bind("<<TreeviewSelect>>", self.load_image)
        
        self.button_frame = tk.Frame(self)
        self.button_frame.pack(pady=20, fill=tk.X)
        
        self.btn_select_folder = tk.Button(self.button_frame, text="Select Folder", command=self.select_folder)
        self.btn_select_folder.grid(row=0, column=0, padx=10, pady=5, sticky="ew")
        
        self.btn_download = tk.Button(self.button_frame, text="Download IMG", command=self.download_image)
        self.btn_download.grid(row=0, column=1, padx=10, pady=5, sticky="ew")
        
        self.btn_change = tk.Button(self.button_frame, text="Change IMG", command=self.change_image)
        self.btn_change.grid(row=0, column=2, padx=10, pady=5, sticky="ew")
        
        self.btn_save = tk.Button(self.button_frame, text="Save", command=self.save_image)
        self.btn_save.grid(row=0, column=3, padx=10, pady=5, sticky="ew")
        
        self.button_frame.grid_columnconfigure(0, weight=1)
        self.button_frame.grid_columnconfigure(1, weight=1)
        self.button_frame.grid_columnconfigure(2, weight=1) 
        self.button_frame.grid_columnconfigure(3, weight=1)
 
    def select_folder(self):
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.folder_path.set(folder_selected)
            self.load_files()
    
    def load_files(self):
        self.tree.delete(*self.tree.get_children())
        folder = self.folder_path.get()
        if os.path.isdir(folder):
            files = [f for f in os.listdir(folder) if f.endswith(".zfb")]
            for file in files:
                path = self.extract_path(os.path.join(folder, file))
                self.tree.insert("", tk.END, values=(file, path))
    
    def extract_path(self, file_path):
        try:
            with open(file_path, "rb") as f:
                data = f.read()
                
                # Determinar el tamaño de la imagen
                img_width, img_height = self.detect_image_size(len(data))
                
                # Calcular el offset basado en el tamaño de la imagen
                if (img_width, img_height) == (640, 480):
                    img_data_size = 0x00096000
                elif (img_width, img_height) == (144, 208):
                    img_data_size = 0x0000EA00
                else:
                    img_data_size = img_width * img_height * 2  # Cálculo genérico
                
                # Extraer la parte del archivo después de la imagen
                extra_data = data[img_data_size:]
                
                # Omitir los primeros y últimos 4 bytes nulos
                clean_data = extra_data.strip(b"\x00")
                
                # Intentar decodificar el path
                try:
                    decoded_text = clean_data.decode("latin1", errors="ignore")  # Usa latin1 o iso-8859-1
                    return decoded_text
                except:
                    return "Unknown"
        except:
            return "Unknown"
    
    def update_path(self, item, new_path, entry):
        values = list(self.tree.item(item, "values"))
        
        # Agregar los bytes nulos al inicio y al final del nuevo path
        encoded_path = b"\x00\x00\x00\x00" + new_path.encode("latin1") + b"\x00\x00"
        
        values[1] = new_path
        self.tree.item(item, values=values)
        entry.destroy()
        
        # Guardar cambios en el archivo
        filename = values[0]
        file_path = os.path.join(self.folder_path.get(), filename)
        
        with open(file_path, "rb") as f:
            data = f.read()
        
        img_width, img_height = self.detect_image_size(len(data))
        if (img_width, img_height) == (640, 480):
            img_data_size = 0x00096000
        elif (img_width, img_height) == (144, 208):
            img_data_size = 0x0000EA00
        else:
            img_data_size = img_width * img_height * 2
        
        with open(file_path, "wb") as f:
            f.write(data[:img_data_size])  # Escribir la imagen
            f.write(encoded_path)  # Escribir el path actualizado
    
    def edit_path(self, event):
        item = self.tree.selection()[0]
        column = self.tree.identify_column(event.x)
        if column == "#2":
            x, y, width, height = self.tree.bbox(item, column="#2")
            entry = tk.Entry(self.tree)
            entry.place(x=x, y=y, width=width, height=height)
            entry.insert(0, self.tree.item(item, "values")[1])
            entry.focus()
            entry.bind("<Return>", lambda e: self.update_path(item, entry.get(), entry))
            entry.bind("<FocusOut>", lambda e: self.update_path(item, entry.get(), entry))
    
    
    def load_image(self, event):
        selected_item = self.tree.selection()
        if not selected_item:
            return
        filename = self.tree.item(selected_item[0], "values")[0]
        file_path = os.path.join(self.folder_path.get(), filename)
    
        try:
            with open(file_path, "rb") as f:
                raw_data = f.read()
                img_width, img_height = self.detect_image_size(len(raw_data))
    
                pixel_data = struct.unpack(f"{img_width * img_height}H", raw_data[:img_width * img_height * 2])
                img = Image.new("RGB", (img_width, img_height))
    
                for y in range(img_height):
                    for x in range(img_width):
                        pixel = pixel_data[y * img_width + x]
                        r = (pixel >> 11) & 0x1F
                        g = (pixel >> 5) & 0x3F
                        b = pixel & 0x1F
                        img.putpixel((x, y), (r << 3, g << 2, b << 3))
    
                self.current_image = img
                self.tk_image = ImageTk.PhotoImage(img)

                # Limpiar el canvas antes de mostrar una nueva imagen
                self.canvas.delete("all")

                # Calcular el centro
                canvas_width = self.canvas.winfo_width()
                canvas_height = self.canvas.winfo_height()
                x_center = canvas_width // 2
                y_center = canvas_height // 2

                # Dibujar la imagen centrada
                self.canvas.create_image(x_center, y_center, image=self.tk_image, anchor=tk.CENTER)
    
        except Exception as e:
            messagebox.showerror("Error", f"Error loading image: {e}")
    
    def detect_image_size(self, file_size):
        possible_sizes = [(640, 480), (144, 208), (320, 240)]
        for w, h in possible_sizes:
            if file_size >= w * h * 2:
                return w, h
        raise ValueError("Unknown image size")
    
    def download_image(self):
        if hasattr(self, "current_image"):
            file_path = filedialog.asksaveasfilename(defaultextension=".png")
            if file_path:
                self.current_image.save(file_path)
    
    def change_image(self):
        file_path = filedialog.askopenfilename(filetypes=[("Images", "*.png;*.jpg;*.bmp")])
        if file_path:
            new_img = Image.open(file_path).convert("RGB")
            new_img = new_img.resize(self.current_image.size)
            self.current_image = new_img
            self.tk_image = ImageTk.PhotoImage(new_img)

            # Limpiar canvas antes de cargar nueva imagen
            self.canvas.delete("all")
            
            # Redibujar imagen centrada
            x_center = self.canvas.winfo_width() // 2
            y_center = self.canvas.winfo_height() // 2
            self.canvas.create_image(x_center, y_center, image=self.tk_image, anchor=tk.CENTER)
    
    def save_image(self):
        if hasattr(self, "current_image"):
            selected_item = self.tree.selection()
            if not selected_item:
                return
            filename = self.tree.item(selected_item[0], "values")[0]
            file_path = os.path.join(self.folder_path.get(), filename)
    
            with open(file_path, "rb") as f:
                original_data = f.read()
    
            img_width, img_height = self.current_image.size
            raw_data = bytearray()
    
            for y in range(img_height):
                for x in range(img_width):
                    r, g, b = self.current_image.getpixel((x, y))
                    rgb565 = ((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3)
                    raw_data.extend(struct.pack("H", rgb565))
    
            extra_data = original_data[img_width * img_height * 2:]
            with open(file_path, "wb") as f:
                f.write(raw_data)
                f.write(extra_data)

if __name__ == "__main__":
    app = ZFBViewer()
    app.mainloop()
