import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.font_manager as fm
import numpy as np
from io import StringIO
import os

class SignalPlotter:
    def __init__(self, root):
        self.root = root
        self.root.title("Graficador de Señales - Con Selección de Rangos y Scroll")
        self.root.geometry("1200x800")
        
        # Variables
        self.df = None
        self.original_headers = []
        self.custom_headers = {}
        self.selected_signals = []
        
        # Variables para rangos de ejes
        self.auto_range_x = True
        self.auto_range_y = True
        self.x_min = None
        self.x_max = None
        self.y_min = None
        self.y_max = None
        
        # Configurar matplotlib para Times New Roman
        plt.rcParams['font.family'] = 'serif'
        plt.rcParams['font.serif'] = ['Times New Roman']
        plt.rcParams['font.size'] = 10
        
        # Colores predefinidos para las señales
        self.colors = ['blue', 'red', 'green', 'orange', 'purple', 'brown', 
                      'pink', 'gray', 'olive', 'cyan', 'magenta', 'black']
        
        # Diccionarios para escalado
        self.scale_factors = {
            'ninguno': (1, ''),
            'mili': (1e3, 'm'),
            'kilo': (1e-3, 'k'),
            'mega': (1e-6, 'M')
        }
        
        self.setup_gui()
    
    def setup_gui(self):
        # Frame principal
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Frame superior - Carga de archivo
        file_frame = ttk.LabelFrame(main_frame, text="Cargar Archivo", padding=10)
        file_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(file_frame, text="Seleccionar Archivo TXT", 
                  command=self.load_file).pack(side=tk.LEFT, padx=(0, 10))
        
        self.file_label = ttk.Label(file_frame, text="Ningún archivo seleccionado")
        self.file_label.pack(side=tk.LEFT)
        
        # Frame medio - Configuración de headers
        header_frame = ttk.LabelFrame(main_frame, text="Configurar Nombres de Señales", padding=10)
        header_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Scrollable frame para headers - ALTURA REDUCIDA
        canvas = tk.Canvas(header_frame, height=100)
        scrollbar = ttk.Scrollbar(header_frame, orient="vertical", command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Frame inferior - Selección de señales y ploteo
        plot_frame = ttk.LabelFrame(main_frame, text="Selección de Señales y Ploteo", padding=10)
        plot_frame.pack(fill=tk.BOTH, expand=True)
        
        # Frame izquierdo - Controles expandidos CON SCROLL CORREGIDO
        left_frame = ttk.Frame(plot_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))

        # NUEVO: Canvas y scrollbar para todo el panel izquierdo
        left_canvas = tk.Canvas(left_frame, width=450)  # Ancho fijo para consistencia
        left_scrollbar = ttk.Scrollbar(left_frame, orient="vertical", command=left_canvas.yview)
        left_scrollable_frame = ttk.Frame(left_canvas)

        # Configurar scroll
        left_scrollable_frame.bind(
            "<Configure>",
            lambda e: left_canvas.configure(scrollregion=left_canvas.bbox("all"))
        )

        left_canvas.create_window((0, 0), window=left_scrollable_frame, anchor="nw")
        left_canvas.configure(yscrollcommand=left_scrollbar.set)

        # Empacar canvas y scrollbar
        left_canvas.pack(side="left", fill="both", expand=True)
        left_scrollbar.pack(side="right", fill="y")

        # AHORA TODAS LAS SECCIONES VAN DENTRO DE left_scrollable_frame
        # Sección de selección de señales
        signals_section = ttk.LabelFrame(left_scrollable_frame, text="Selección de Señales", padding=5)
        signals_section.pack(fill=tk.X, pady=(0, 8), padx=5)
        
        ttk.Label(signals_section, text="Señales disponibles:", font=('TkDefaultFont', 9, 'bold')).pack(anchor=tk.W)
        ttk.Label(signals_section, text="(Todas las seleccionadas aparecerán superpuestas)", 
                 font=('TkDefaultFont', 8), foreground='gray').pack(anchor=tk.W)
        
        # Listbox con altura optimizada
        self.signals_listbox = tk.Listbox(signals_section, selectmode=tk.MULTIPLE, width=50, height=8)
        self.signals_listbox.pack(fill=tk.X, pady=(5, 5))
        
        # Botones de selección
        button_frame = ttk.Frame(signals_section)
        button_frame.pack(fill=tk.X)
        
        ttk.Button(button_frame, text="Seleccionar Todo", 
                  command=self.select_all).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="Deseleccionar Todo", 
                  command=self.deselect_all).pack(side=tk.LEFT)
        
        # Sección de rangos de ejes
        range_section = ttk.LabelFrame(left_scrollable_frame, text="Rangos de Ejes", padding=5)
        range_section.pack(fill=tk.X, pady=(0, 8), padx=5)
        
        # Configuración del Eje X
        ttk.Label(range_section, text="Eje X (Tiempo):", font=('TkDefaultFont', 9, 'bold')).grid(row=0, column=0, columnspan=3, sticky=tk.W, pady=(0,2))
        
        self.auto_x_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(range_section, text="Automático", variable=self.auto_x_var, 
                       command=self.toggle_x_range).grid(row=1, column=0, sticky=tk.W)
        
        ttk.Label(range_section, text="Min:").grid(row=1, column=1, padx=(10,2), sticky=tk.E)
        self.x_min_var = tk.StringVar()
        self.x_min_entry = ttk.Entry(range_section, textvariable=self.x_min_var, width=8, state="disabled")
        self.x_min_entry.grid(row=1, column=2, padx=(0,5))
        
        ttk.Label(range_section, text="Max:").grid(row=2, column=1, padx=(10,2), sticky=tk.E)
        self.x_max_var = tk.StringVar()
        self.x_max_entry = ttk.Entry(range_section, textvariable=self.x_max_var, width=8, state="disabled")
        self.x_max_entry.grid(row=2, column=2, padx=(0,5))
        
        # Configuración del Eje Y
        ttk.Label(range_section, text="Eje Y (Señales):", font=('TkDefaultFont', 9, 'bold')).grid(row=3, column=0, columnspan=3, sticky=tk.W, pady=(10,2))
        
        self.auto_y_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(range_section, text="Automático", variable=self.auto_y_var, 
                       command=self.toggle_y_range).grid(row=4, column=0, sticky=tk.W)
        
        ttk.Label(range_section, text="Min:").grid(row=4, column=1, padx=(10,2), sticky=tk.E)
        self.y_min_var = tk.StringVar()
        self.y_min_entry = ttk.Entry(range_section, textvariable=self.y_min_var, width=8, state="disabled")
        self.y_min_entry.grid(row=4, column=2, padx=(0,5))
        
        ttk.Label(range_section, text="Max:").grid(row=5, column=1, padx=(10,2), sticky=tk.E)
        self.y_max_var = tk.StringVar()
        self.y_max_entry = ttk.Entry(range_section, textvariable=self.y_max_var, width=8, state="disabled")
        self.y_max_entry.grid(row=5, column=2, padx=(0,5))
        
        # Botones de rango
        ttk.Button(range_section, text="Aplicar Rangos", 
                  command=self.apply_ranges).grid(row=6, column=0, columnspan=3, pady=(8,0), sticky=tk.EW)
        
        ttk.Button(range_section, text="Resetear a Automático", 
                  command=self.reset_to_auto).grid(row=7, column=0, columnspan=3, pady=(2,0), sticky=tk.EW)
        
        # Sección de escalado de unidades
        scale_section = ttk.LabelFrame(left_scrollable_frame, text="Escalado de Unidades", padding=5)
        scale_section.pack(fill=tk.X, pady=(0, 8), padx=5)
        
        # Escalado del Eje X
        ttk.Label(scale_section, text="Eje X (Tiempo):").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.x_scale_var = tk.StringVar(value="ninguno")
        x_scale_combo = ttk.Combobox(scale_section, textvariable=self.x_scale_var, 
                                    values=list(self.scale_factors.keys()), 
                                    state="readonly", width=10)
        x_scale_combo.grid(row=0, column=1, padx=(5, 0), pady=2, sticky=tk.W)
        
        # Escalado del Eje Y
        ttk.Label(scale_section, text="Eje Y (Señales):").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.y_scale_var = tk.StringVar(value="ninguno")
        y_scale_combo = ttk.Combobox(scale_section, textvariable=self.y_scale_var, 
                                    values=list(self.scale_factors.keys()), 
                                    state="readonly", width=10)
        y_scale_combo.grid(row=1, column=1, padx=(5, 0), pady=2, sticky=tk.W)
        
        # Sección de configuración del gráfico
        config_section = ttk.LabelFrame(left_scrollable_frame, text="Configuración del Gráfico", padding=5)
        config_section.pack(fill=tk.X, pady=(0, 8), padx=5)
        
        # Título del gráfico
        ttk.Label(config_section, text="Título:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.title_var = tk.StringVar(value="Señales vs Tiempo")
        ttk.Entry(config_section, textvariable=self.title_var, width=30).grid(row=0, column=1, padx=(5, 0), pady=2)
        
        # Etiqueta del eje Y
        ttk.Label(config_section, text="Eje Y:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.ylabel_var = tk.StringVar(value="Voltaje (V)")
        ttk.Entry(config_section, textvariable=self.ylabel_var, width=30).grid(row=1, column=1, padx=(5, 0), pady=2)
        
        # Checkboxes
        self.legend_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(config_section, text="Mostrar leyenda", 
                       variable=self.legend_var).grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=2)
        
        self.grid_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(config_section, text="Mostrar grid", 
                       variable=self.grid_var).grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=2)
        
        # Botones principales
        buttons_section = ttk.Frame(left_scrollable_frame)
        buttons_section.pack(fill=tk.X, pady=(0, 10), padx=5)
        
        ttk.Button(buttons_section, text="Generar Gráfico", 
                  command=self.generate_plot).pack(fill=tk.X, pady=(0, 5))
        ttk.Button(buttons_section, text="Guardar Gráfico", 
                  command=self.save_plot).pack(fill=tk.X)

        # Bind para scroll con mouse wheel - IMPORTANTE
        def _on_mousewheel(event):
            left_canvas.yview_scroll(int(-1*(event.delta/120)), "units")

        left_canvas.bind("<MouseWheel>", _on_mousewheel)  # Windows
        left_canvas.bind("<Button-4>", lambda e: left_canvas.yview_scroll(-1, "units"))  # Linux
        left_canvas.bind("<Button-5>", lambda e: left_canvas.yview_scroll(1, "units"))   # Linux

        # Bind para actualizar gráfico cuando cambien las escalas
        x_scale_combo.bind('<<ComboboxSelected>>', self.on_scale_change)
        y_scale_combo.bind('<<ComboboxSelected>>', self.on_scale_change)
        
        # Frame derecho - Vista previa REDUCIDA
        right_frame = ttk.Frame(plot_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        ttk.Label(right_frame, text="Vista Previa:", font=('TkDefaultFont', 9, 'bold')).pack(anchor=tk.W)
        
        # Canvas para matplotlib - TAMAÑO REDUCIDO
        self.fig, self.ax = plt.subplots(figsize=(4.5, 3.5))
        self.canvas = FigureCanvasTkAgg(self.fig, right_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Información de estado
        self.info_label = ttk.Label(right_frame, text="Selecciona señales para ver información", 
                                   font=('TkDefaultFont', 8), foreground='blue')
        self.info_label.pack(anchor=tk.W, pady=(5, 0))
        
        # Bind para actualizar información cuando cambie la selección
        self.signals_listbox.bind('<<ListboxSelect>>', self.update_selection_info)
    
    def toggle_x_range(self):
        """Habilita/deshabilita los campos de rango X"""
        if self.auto_x_var.get():
            self.x_min_entry.config(state="disabled")
            self.x_max_entry.config(state="disabled")
            self.auto_range_x = True
        else:
            self.x_min_entry.config(state="normal")
            self.x_max_entry.config(state="normal")
            self.auto_range_x = False
            # Sugerir valores actuales si existen
            if self.ax and hasattr(self.ax, 'get_xlim'):
                try:
                    xlim = self.ax.get_xlim()
                    if not self.x_min_var.get():
                        self.x_min_var.set(f"{xlim[0]:.6f}")
                    if not self.x_max_var.get():
                        self.x_max_var.set(f"{xlim[1]:.6f}")
                except:
                    pass
    
    def toggle_y_range(self):
        """Habilita/deshabilita los campos de rango Y"""
        if self.auto_y_var.get():
            self.y_min_entry.config(state="disabled")
            self.y_max_entry.config(state="disabled")
            self.auto_range_y = True
        else:
            self.y_min_entry.config(state="normal")
            self.y_max_entry.config(state="normal")
            self.auto_range_y = False
            # Sugerir valores actuales si existen
            if self.ax and hasattr(self.ax, 'get_ylim'):
                try:
                    ylim = self.ax.get_ylim()
                    if not self.y_min_var.get():
                        self.y_min_var.set(f"{ylim[0]:.6f}")
                    if not self.y_max_var.get():
                        self.y_max_var.set(f"{ylim[1]:.6f}")
                except:
                    pass
    
    def apply_ranges(self):
        """Aplica los rangos especificados y regenera el gráfico"""
        if not self.auto_range_x:
            try:
                self.x_min = float(self.x_min_var.get()) if self.x_min_var.get() else None
                self.x_max = float(self.x_max_var.get()) if self.x_max_var.get() else None
            except ValueError:
                messagebox.showerror("Error", "Los valores del rango X deben ser números válidos")
                return
        
        if not self.auto_range_y:
            try:
                self.y_min = float(self.y_min_var.get()) if self.y_min_var.get() else None
                self.y_max = float(self.y_max_var.get()) if self.y_max_var.get() else None
            except ValueError:
                messagebox.showerror("Error", "Los valores del rango Y deben ser números válidos")
                return
        
        # Regenerar gráfico con los nuevos rangos
        if self.df is not None and self.signals_listbox.curselection():
            self.generate_plot()
    
    def reset_to_auto(self):
        """Resetea ambos ejes a rango automático"""
        self.auto_x_var.set(True)
        self.auto_y_var.set(True)
        self.toggle_x_range()
        self.toggle_y_range()
        self.x_min_var.set("")
        self.x_max_var.set("")
        self.y_min_var.set("")
        self.y_max_var.set("")
        # Regenerar gráfico
        if self.df is not None and self.signals_listbox.curselection():
            self.generate_plot()
    
    def on_scale_change(self, event=None):
        """Callback para regenerar gráfico cuando cambia la escala"""
        if self.df is not None and self.signals_listbox.curselection():
            self.generate_plot()
    
    def get_scaled_data_and_label(self, data, scale_type, original_label):
        """Aplica escalado a los datos y devuelve etiqueta actualizada"""
        if scale_type not in self.scale_factors:
            return data, original_label
        
        factor, prefix = self.scale_factors[scale_type]
        
        # Solo escalar datos si no está vacío
        if len(data) > 0:
            scaled_data = data * factor
        else:
            scaled_data = data
        
        if prefix:
            # Actualizar etiqueta con prefijo
            if '(' in original_label and ')' in original_label:
                # Extraer unidad entre paréntesis
                start = original_label.find('(')
                end = original_label.find(')')
                base_label = original_label[:start+1]
                unit = original_label[start+1:end]
                rest = original_label[end:]
                new_label = f"{base_label}{prefix}{unit}{rest}"
            else:
                new_label = f"{original_label} ({prefix})"
        else:
            new_label = original_label
        
        return scaled_data, new_label
    
    def get_scaled_label_only(self, scale_type, original_label):
        """Función auxiliar para obtener solo la etiqueta escalada sin procesar datos"""
        if scale_type not in self.scale_factors:
            return original_label
        
        _, prefix = self.scale_factors[scale_type]
        
        if prefix:
            if '(' in original_label and ')' in original_label:
                start = original_label.find('(')
                end = original_label.find(')')
                base_label = original_label[:start+1]
                unit = original_label[start+1:end]
                rest = original_label[end:]
                new_label = f"{base_label}{prefix}{unit}{rest}"
            else:
                new_label = f"{original_label} ({prefix})"
        else:
            new_label = original_label
        
        return new_label
    
    def load_file(self):
        file_path = filedialog.askopenfilename(
            title="Seleccionar archivo TXT",
            filetypes=[("Archivos de texto", "*.txt"), ("Todos los archivos", "*.*")]
        )
        
        if file_path:
            try:
                # Leer el archivo
                with open(file_path, 'r', encoding='utf-8') as file:
                    content = file.read()
                
                # Procesar el formato del archivo
                lines = content.strip().split('\n')
                
                # Extraer headers (primera línea)
                header1 = lines[0].split('\t')
                
                # Si hay segunda línea de headers, combinarla
                if len(lines) > 1 and any(word in lines[1].lower() for word in ['time', 'voltage', 's)', 'v)']):
                    header2 = lines[1].split('\t')
                    headers = []
                    for h1, h2 in zip(header1, header2):
                        combined = f'{h1.strip()} {h2.strip()}' if h2.strip() else h1.strip()
                        headers.append(combined.strip())
                    data_start = 2
                else:
                    headers = [h.strip() for h in header1]
                    data_start = 1
                
                # Extraer datos
                data_lines = lines[data_start:]
                data_content = '\n'.join(data_lines)
                
                # Crear DataFrame
                self.df = pd.read_csv(StringIO(data_content), sep='\t', names=headers)
                
                # Convertir notación científica de forma moderna
                for col in self.df.columns:
                    try:
                        self.df[col] = pd.to_numeric(self.df[col])
                    except (ValueError, TypeError):
                        pass
                
                self.original_headers = list(self.df.columns)
                self.custom_headers = {header: header for header in self.original_headers}
                
                # Actualizar interfaz
                self.file_label.config(text=f"Archivo cargado: {os.path.basename(file_path)}")
                self.setup_header_editors()
                self.update_signals_list()
                
                messagebox.showinfo("Éxito", f"Archivo cargado correctamente.\n{len(self.df)} filas, {len(self.df.columns)} columnas")
                
            except Exception as e:
                messagebox.showerror("Error", f"Error al cargar el archivo:\n{str(e)}")
    
    def setup_header_editors(self):
        # Limpiar frame anterior
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        
        # Crear editores para cada header
        for i, header in enumerate(self.original_headers):
            row_frame = ttk.Frame(self.scrollable_frame)
            row_frame.pack(fill=tk.X, pady=1)
            
            ttk.Label(row_frame, text=f"Original: {header[:35]}...", width=40).pack(side=tk.LEFT)
            
            entry_var = tk.StringVar(value=self.custom_headers[header])
            entry = ttk.Entry(row_frame, textvariable=entry_var, width=20)
            entry.pack(side=tk.LEFT, padx=(10, 0))
            
            # Callback para actualizar el diccionario
            def update_header(var=entry_var, orig=header):
                self.custom_headers[orig] = var.get()
                self.update_signals_list()
            
            entry_var.trace('w', lambda *args, var=entry_var, orig=header: update_header(var, orig))
    
    def update_signals_list(self):
        if self.df is not None:
            self.signals_listbox.delete(0, tk.END)
            
            for header in self.original_headers:
                custom_name = self.custom_headers[header]
                self.signals_listbox.insert(tk.END, custom_name)
    
    def select_all(self):
        self.signals_listbox.select_set(0, tk.END)
        self.update_selection_info()
    
    def deselect_all(self):
        self.signals_listbox.selection_clear(0, tk.END)
        self.update_selection_info()
    
    def update_selection_info(self, event=None):
        selected_indices = self.signals_listbox.curselection()
        if selected_indices:
            count = len(selected_indices)
            range_info = ""
            if not self.auto_range_x or not self.auto_range_y:
                range_parts = []
                if not self.auto_range_x:
                    range_parts.append("X personalizado")
                if not self.auto_range_y:
                    range_parts.append("Y personalizado")
                range_info = f" | Rangos: {', '.join(range_parts)}"
            
            scale_x = self.x_scale_var.get()
            scale_y = self.y_scale_var.get()
            scale_info = f" | Escalas: X={scale_x}, Y={scale_y}" if scale_x != 'ninguno' or scale_y != 'ninguno' else ""
            
            if count == 1:
                self.info_label.config(text=f"1 señal seleccionada{range_info}{scale_info}")
            else:
                self.info_label.config(text=f"{count} señales seleccionadas{range_info}{scale_info}")
        else:
            self.info_label.config(text="Ninguna señal seleccionada")
    
    def generate_plot(self):
        if self.df is None:
            messagebox.showwarning("Advertencia", "Primero carga un archivo")
            return
        
        selected_indices = self.signals_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("Advertencia", "Selecciona al menos una señal")
            return
        
        # Limpiar figura anterior
        self.fig.clear()
        
        # Configurar tamaño para Word (7.54 cm x 7.09 cm)
        width_inches = 7.54 * 0.393701
        height_inches = 7.09 * 0.393701
        
        self.fig.set_size_inches(width_inches, height_inches)
        
        # Crear un solo subplot
        ax = self.fig.add_subplot(1, 1, 1)
        
        # Obtener columna de tiempo (primera columna)
        time_col = self.df.columns[0]
        time_data = self.df[time_col]
        
        # Aplicar escalado al eje X (tiempo)
        scaled_time_data, time_label = self.get_scaled_data_and_label(
            time_data, self.x_scale_var.get(), "Tiempo (s)"
        )
        
        # Plotear todas las señales seleccionadas en el mismo gráfico
        legend_labels = []
        
        for i, idx in enumerate(selected_indices):
            original_header = self.original_headers[idx]
            custom_header = self.custom_headers[original_header]
            signal_data = self.df[original_header]
            
            # Aplicar escalado al eje Y (señal)
            scaled_signal_data, _ = self.get_scaled_data_and_label(
                signal_data, self.y_scale_var.get(), custom_header
            )
            
            # Usar diferentes colores para cada señal
            color = self.colors[i % len(self.colors)]
            
            # Plotear la señal
            ax.plot(scaled_time_data, scaled_signal_data, linewidth=1.5, color=color, 
                   label=custom_header, alpha=0.8)
            
            legend_labels.append(custom_header)
        
        # Configurar etiquetas de los ejes con escalado
        ylabel_base = self.ylabel_var.get()
        ylabel_scaled = self.get_scaled_label_only(self.y_scale_var.get(), ylabel_base)
        
        # Configurar el gráfico
        ax.set_title(self.title_var.get(), fontsize=10, pad=10, weight='bold')
        ax.set_xlabel(time_label, fontsize=9)
        ax.set_ylabel(ylabel_scaled, fontsize=9)
        ax.tick_params(labelsize=8)
        
        # APLICAR RANGOS PERSONALIZADOS
        if not self.auto_range_x:
            if self.x_min is not None or self.x_max is not None:
                current_xlim = ax.get_xlim()
                x_min = self.x_min if self.x_min is not None else current_xlim[0]
                x_max = self.x_max if self.x_max is not None else current_xlim[1]
                ax.set_xlim(x_min, x_max)
        
        if not self.auto_range_y:
            if self.y_min is not None or self.y_max is not None:
                current_ylim = ax.get_ylim()
                y_min = self.y_min if self.y_min is not None else current_ylim[0]
                y_max = self.y_max if self.y_max is not None else current_ylim[1]
                ax.set_ylim(y_min, y_max)
        
        # Mostrar grid si está habilitado
        if self.grid_var.get():
            ax.grid(True, alpha=0.3, linestyle='--')
        
        # Mostrar leyenda si está habilitada y hay múltiples señales
        if self.legend_var.get() and len(selected_indices) > 1:
            ax.legend(fontsize=7, loc='best', framealpha=0.9)
        
        # Guardar referencia al axis para uso posterior
        self.ax = ax
        
        # Ajustar layout
        self.fig.tight_layout(pad=0.5)
        
        # Actualizar canvas
        self.canvas.draw()
        
        # Actualizar información
        self.update_selection_info()
    
    def save_plot(self):
        if self.df is None:
            messagebox.showwarning("Advertencia", "Primero genera un gráfico")
            return
        
        file_path = filedialog.asksaveasfilename(
            title="Guardar gráfico",
            defaultextension=".png",
            filetypes=[
                ("PNG", "*.png"),
                ("PDF", "*.pdf"),
                ("SVG", "*.svg"),
                ("JPG", "*.jpg")
            ]
        )
        
        if file_path:
            try:
                # Configurar DPI alto para calidad de Word
                self.fig.savefig(file_path, dpi=300, bbox_inches='tight', 
                               facecolor='white', edgecolor='none')
                messagebox.showinfo("Éxito", f"Gráfico guardado como:\n{file_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Error al guardar:\n{str(e)}")

def main():
    root = tk.Tk()
    app = SignalPlotter(root)
    root.mainloop()

if __name__ == "__main__":
    main()
