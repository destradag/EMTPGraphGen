import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib as mpl
import numpy as np
import os
import glob
from io import StringIO

class StatisticalAnalyzer:
    def __init__(self, root):
        self.root = root
        self.root.title("Analizador Estadístico de Sobretensiones - Avanzado")
        self.root.geometry("1400x900")
        
        # Variables
        self.data = None
        self.df = None
        self.labels = []
        self.custom_labels = {}
        self.output_folder = ""
        
        # Configurar matplotlib globalmente
        mpl.rcParams['figure.figsize'] = [7.54/2.54, 7.09/2.54]
        mpl.rcParams['font.family'] = 'Times New Roman'
        mpl.rcParams['font.size'] = 10
        mpl.rcParams['axes.titlesize'] = 10
        mpl.rcParams['axes.labelsize'] = 10
        mpl.rcParams['xtick.labelsize'] = 10
        mpl.rcParams['ytick.labelsize'] = 10
        mpl.rcParams['legend.fontsize'] = 10
        mpl.rcParams['savefig.dpi'] = 300
        mpl.rcParams['savefig.bbox'] = 'tight'
        
        # Diccionarios para escalado de unidades del eje Y
        self.y_unit_factors = {
            'Voltios (V)': (1, 'V'),
            'Kilovoltios (kV)': (1e-3, 'kV'),
            'Megavoltios (MV)': (1e-6, 'MV'),
            'Milivoltios (mV)': (1e3, 'mV'),
            'time (s)': (1, 's'),
            'time (ms)': (1e3, 'ms')
        }
        
        self.setup_gui()
    
    def setup_gui(self):
        # Frame principal
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Frame superior - Carga de archivos
        file_frame = ttk.LabelFrame(main_frame, text="Cargar Archivos", padding=10)
        file_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Botones de carga
        button_frame = ttk.Frame(file_frame)
        button_frame.pack(fill=tk.X)
        
        ttk.Button(button_frame, text="Cargar Datos (.txt)", 
                  command=self.load_data_file).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="Cargar Labels (.txt)", 
                  command=self.load_labels_file).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="Seleccionar Carpeta de Salida", 
                  command=self.select_output_folder).pack(side=tk.LEFT)
        
        # Labels de estado
        status_frame = ttk.Frame(file_frame)
        status_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.data_label = ttk.Label(status_frame, text="Datos: No cargados", foreground="red")
        self.data_label.pack(anchor=tk.W)
        
        self.labels_label = ttk.Label(status_frame, text="Labels: No cargados", foreground="red")
        self.labels_label.pack(anchor=tk.W)
        
        self.output_label = ttk.Label(status_frame, text="Carpeta salida: No seleccionada", foreground="red")
        self.output_label.pack(anchor=tk.W)
        
        # Frame medio - Editor de labels
        labels_frame = ttk.LabelFrame(main_frame, text="Editar Nombres de Columnas", padding=10)
        labels_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Canvas scrollable para labels
        labels_canvas = tk.Canvas(labels_frame, height=120)  # Reducido para más espacio
        labels_scrollbar = ttk.Scrollbar(labels_frame, orient="vertical", command=labels_canvas.yview)
        self.labels_scrollable_frame = ttk.Frame(labels_canvas)
        
        self.labels_scrollable_frame.bind(
            "<Configure>",
            lambda e: labels_canvas.configure(scrollregion=labels_canvas.bbox("all"))
        )
        
        labels_canvas.create_window((0, 0), window=self.labels_scrollable_frame, anchor="nw")
        labels_canvas.configure(yscrollcommand=labels_scrollbar.set)
        
        labels_canvas.pack(side="left", fill="both", expand=True)
        labels_scrollbar.pack(side="right", fill="y")
        
        # Frame inferior - Configuración y análisis CON SCROLL
        analysis_frame = ttk.LabelFrame(main_frame, text="Configuración de Análisis", padding=10)
        analysis_frame.pack(fill=tk.BOTH, expand=True)
        
        # Frame izquierdo - Controles CON SCROLL IMPLEMENTADO
        left_analysis_frame = ttk.Frame(analysis_frame)
        left_analysis_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        
        # Canvas y scrollbar para el panel izquierdo de configuración
        config_canvas = tk.Canvas(left_analysis_frame, width=400)
        config_scrollbar = ttk.Scrollbar(left_analysis_frame, orient="vertical", command=config_canvas.yview)
        config_scrollable_frame = ttk.Frame(config_canvas)
        
        # Configurar scroll para el panel de configuración
        config_scrollable_frame.bind(
            "<Configure>",
            lambda e: config_canvas.configure(scrollregion=config_canvas.bbox("all"))
        )
        
        config_canvas.create_window((0, 0), window=config_scrollable_frame, anchor="nw")
        config_canvas.configure(yscrollcommand=config_scrollbar.set)
        
        # Empacar canvas y scrollbar para configuración
        config_canvas.pack(side="left", fill="both", expand=True)
        config_scrollbar.pack(side="right", fill="y")
        
        # SECCIONES DE CONFIGURACIÓN DENTRO DE config_scrollable_frame
        # Sección de selección de columnas
        columns_section = ttk.LabelFrame(config_scrollable_frame, text="Seleccionar Columnas", padding=5)
        columns_section.pack(fill=tk.X, pady=(0, 10), padx=5)
        
        self.columns_listbox = tk.Listbox(columns_section, selectmode=tk.MULTIPLE, height=10, width=45)
        self.columns_listbox.pack(fill=tk.X, pady=(0, 10))
        
        # Botones de selección
        columns_buttons = ttk.Frame(columns_section)
        columns_buttons.pack(fill=tk.X)
        
        ttk.Button(columns_buttons, text="Seleccionar Todo", 
                  command=self.select_all_columns).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(columns_buttons, text="Deseleccionar Todo", 
                  command=self.deselect_all_columns).pack(side=tk.LEFT)
        
        # Configuración de gráficos
        chart_config_section = ttk.LabelFrame(config_scrollable_frame, text="Tipos de Gráfico", padding=5)
        chart_config_section.pack(fill=tk.X, pady=(0, 10), padx=5)
        
        # Tipos de gráfico
        self.barras_var = tk.BooleanVar(value=True)
        self.boxplot_var = tk.BooleanVar(value=True)
        self.histogram_var = tk.BooleanVar(value=True)
        
        ttk.Checkbutton(chart_config_section, text="Gráficos de Barras", 
                       variable=self.barras_var).pack(anchor=tk.W)
        ttk.Checkbutton(chart_config_section, text="Boxplots", 
                       variable=self.boxplot_var).pack(anchor=tk.W)
        ttk.Checkbutton(chart_config_section, text="Histogramas", 
                       variable=self.histogram_var).pack(anchor=tk.W)
        
        # NUEVA SECCIÓN: Configuración de Unidades del Eje Y
        y_units_section = ttk.LabelFrame(config_scrollable_frame, text="Unidades del Eje Y", padding=5)
        y_units_section.pack(fill=tk.X, pady=(0, 10), padx=5)
        
        ttk.Label(y_units_section, text="Seleccionar unidad:", font=('TkDefaultFont', 9, 'bold')).pack(anchor=tk.W, pady=(0, 5))
        
        self.y_unit_var = tk.StringVar(value="Kilovoltios (kV)")
        y_unit_combo = ttk.Combobox(y_units_section, textvariable=self.y_unit_var,
                                   values=list(self.y_unit_factors.keys()),
                                   state="readonly", width=20)
        y_unit_combo.pack(anchor=tk.W, pady=(0, 5))
        
        # Bind para actualizar vista previa cuando cambie la unidad
        y_unit_combo.bind('<<ComboboxSelected>>', self.on_unit_change)
        
        # NUEVA SECCIÓN: Configuración de Línea de Referencia
        reference_section = ttk.LabelFrame(config_scrollable_frame, text="Línea de Referencia", padding=5)
        reference_section.pack(fill=tk.X, pady=(0, 10), padx=5)
        
        # Checkbox para habilitar/deshabilitar línea de referencia
        self.show_reference_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(reference_section, text="Mostrar línea de referencia", 
                       variable=self.show_reference_var, command=self.on_reference_change).pack(anchor=tk.W, pady=(0, 5))
        
        # Valor de la línea de referencia
        ref_value_frame = ttk.Frame(reference_section)
        ref_value_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(ref_value_frame, text="Valor de referencia:").pack(side=tk.LEFT)
        self.reference_line_var = tk.StringVar(value="707.1")
        self.reference_entry = ttk.Entry(ref_value_frame, textvariable=self.reference_line_var, width=12)
        self.reference_entry.pack(side=tk.LEFT, padx=(5, 5))
        
        # Label dinámico para mostrar la unidad actual
        self.reference_unit_label = ttk.Label(ref_value_frame, text="kV")
        self.reference_unit_label.pack(side=tk.LEFT)
        
        # Configuración de formato adicional
        format_section = ttk.LabelFrame(config_scrollable_frame, text="Configuración de Formato", padding=5)
        format_section.pack(fill=tk.X, pady=(0, 10), padx=5)
        
        # Tamaño de fuente para gráficos
        ttk.Label(format_section, text="Tamaño de Fuente:").pack(anchor=tk.W, pady=(0, 2))
        self.font_size_var = tk.StringVar(value="10")
        font_size_frame = ttk.Frame(format_section)
        font_size_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Entry(font_size_frame, textvariable=self.font_size_var, width=5).pack(side=tk.LEFT)
        ttk.Label(font_size_frame, text="px").pack(side=tk.LEFT, padx=(2, 0))
        
        # Configuración de colores
        ttk.Label(format_section, text="Esquema de Colores:").pack(anchor=tk.W, pady=(5, 2))
        self.color_scheme_var = tk.StringVar(value="default")
        color_combo = ttk.Combobox(format_section, textvariable=self.color_scheme_var, 
                                  values=["default", "viridis", "plasma", "inferno", "cool"], 
                                  state="readonly", width=12)
        color_combo.pack(anchor=tk.W, pady=(0, 5))
        
        # Configuración de DPI
        ttk.Label(format_section, text="Resolución (DPI):").pack(anchor=tk.W, pady=(5, 2))
        self.dpi_var = tk.StringVar(value="300")
        dpi_frame = ttk.Frame(format_section)
        dpi_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Entry(dpi_frame, textvariable=self.dpi_var, width=8).pack(side=tk.LEFT)
        ttk.Label(dpi_frame, text="DPI").pack(side=tk.LEFT, padx=(2, 0))
        
        # Configuración de transparencia
        ttk.Label(format_section, text="Transparencia:").pack(anchor=tk.W, pady=(5, 2))
        self.alpha_var = tk.StringVar(value="0.8")
        alpha_frame = ttk.Frame(format_section)
        alpha_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Entry(alpha_frame, textvariable=self.alpha_var, width=5).pack(side=tk.LEFT)
        ttk.Label(alpha_frame, text="(0.0-1.0)").pack(side=tk.LEFT, padx=(2, 0))
        
        # Configuración de estadísticas adicionales
        stats_section = ttk.LabelFrame(config_scrollable_frame, text="Estadísticas Adicionales", padding=5)
        stats_section.pack(fill=tk.X, pady=(0, 10), padx=5)
        
        self.show_percentiles_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(stats_section, text="Mostrar Percentiles (25%, 75%)", 
                       variable=self.show_percentiles_var).pack(anchor=tk.W)
        
        self.show_outliers_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(stats_section, text="Detectar Outliers", 
                       variable=self.show_outliers_var).pack(anchor=tk.W)
        
        self.show_confidence_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(stats_section, text="Intervalos de Confianza", 
                       variable=self.show_confidence_var).pack(anchor=tk.W)
        
        # Configuración de exportación
        export_section = ttk.LabelFrame(config_scrollable_frame, text="Opciones de Exportación", padding=5)
        export_section.pack(fill=tk.X, pady=(0, 10), padx=5)
        
        ttk.Label(export_section, text="Formato de Imagen:").pack(anchor=tk.W, pady=(0, 2))
        self.image_format_var = tk.StringVar(value="png")
        format_combo = ttk.Combobox(export_section, textvariable=self.image_format_var, 
                                   values=["png", "pdf", "svg", "jpg"], 
                                   state="readonly", width=8)
        format_combo.pack(anchor=tk.W, pady=(0, 5))
        
        self.create_summary_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(export_section, text="Crear Resumen CSV", 
                       variable=self.create_summary_var).pack(anchor=tk.W)
        
        self.timestamp_folder_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(export_section, text="Carpeta con Timestamp", 
                       variable=self.timestamp_folder_var).pack(anchor=tk.W)
        
        # Botones principales
        main_buttons_section = ttk.Frame(config_scrollable_frame)
        main_buttons_section.pack(fill=tk.X, pady=(10, 0), padx=5)
        
        ttk.Button(main_buttons_section, text="Procesar Datos", 
                  command=self.process_data).pack(fill=tk.X, pady=(0, 5))
        ttk.Button(main_buttons_section, text="Generar Análisis", 
                  command=self.generate_analysis).pack(fill=tk.X, pady=(0, 5))
        ttk.Button(main_buttons_section, text="Abrir Carpeta Salida", 
                  command=self.open_output_folder).pack(fill=tk.X)
        
        # Bind para scroll con mouse wheel en el panel de configuración
        def _on_config_mousewheel(event):
            config_canvas.yview_scroll(int(-1*(event.delta/120)), "units")

        config_canvas.bind("<MouseWheel>", _on_config_mousewheel)  # Windows
        config_canvas.bind("<Button-4>", lambda e: config_canvas.yview_scroll(-1, "units"))  # Linux
        config_canvas.bind("<Button-5>", lambda e: config_canvas.yview_scroll(1, "units"))   # Linux
        
        # Frame derecho - Vista previa y log
        right_analysis_frame = ttk.Frame(analysis_frame)
        right_analysis_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Vista previa
        preview_section = ttk.LabelFrame(right_analysis_frame, text="Vista Previa", padding=5)
        preview_section.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        self.fig, self.ax = plt.subplots(figsize=(4, 3))
        self.canvas = FigureCanvasTkAgg(self.fig, preview_section)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Log de actividades
        log_section = ttk.LabelFrame(right_analysis_frame, text="Log de Actividades", padding=5)
        log_section.pack(fill=tk.BOTH, expand=True)
        
        self.log_text = tk.Text(log_section, height=8, wrap=tk.WORD)
        log_scrollbar = ttk.Scrollbar(log_section, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scrollbar.set)
        
        self.log_text.pack(side="left", fill="both", expand=True)
        log_scrollbar.pack(side="right", fill="y")
        
        # Mensaje inicial
        self.log_message("Analizador Estadístico iniciado. Cargue los archivos de datos y labels para comenzar.")
    
    def on_unit_change(self, event=None):
        """Callback cuando cambia la unidad del eje Y"""
        # Actualizar la etiqueta de la unidad en la línea de referencia
        selected_unit = self.y_unit_var.get()
        if selected_unit in self.y_unit_factors:
            unit_symbol = self.y_unit_factors[selected_unit][1]
            self.reference_unit_label.config(text=unit_symbol)
        
        # Regenerar vista previa
        if self.df is not None:
            self.generate_preview()
    
    def on_reference_change(self, event=None):
        """Callback cuando cambia la configuración de línea de referencia"""
        # Habilitar/deshabilitar el campo de valor de referencia
        if self.show_reference_var.get():
            self.reference_entry.config(state="normal")
        else:
            self.reference_entry.config(state="disabled")
        
        # Regenerar vista previa
        if self.df is not None:
            self.generate_preview()
    
    def log_message(self, message):
        """Agregar mensaje al log"""
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)
        self.root.update()
    
    def load_data_file(self):
        """Cargar archivo de datos"""
        file_path = filedialog.askopenfilename(
            title="Seleccionar archivo de datos",
            filetypes=[("Archivos TXT", "*.txt"), ("Todos los archivos", "*.*")]
        )
        
        if file_path:
            try:
                self.data = np.loadtxt(file_path)
                self.data_label.config(text=f"Datos: {os.path.basename(file_path)} ({self.data.shape})", foreground="green")
                self.log_message(f"Datos cargados: {file_path}")
                self.log_message(f"Forma de los datos: {self.data.shape}")
                self.process_data()
            except Exception as e:
                messagebox.showerror("Error", f"Error al cargar datos:\n{str(e)}")
                self.log_message(f"Error cargando datos: {str(e)}")
    
    def load_labels_file(self):
        """Cargar archivo de labels"""
        file_path = filedialog.askopenfilename(
            title="Seleccionar archivo de labels",
            filetypes=[("Archivos TXT", "*.txt"), ("Todos los archivos", "*.*")]
        )
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    labels_raw = f.read().strip().split('\n')
                
                # Procesar labels (cada dos líneas: descripción y label)
                self.labels = [labels_raw[i+1].strip() for i in range(0, len(labels_raw), 2)]
                self.custom_labels = {label: label for label in self.labels}
                
                self.labels_label.config(text=f"Labels: {os.path.basename(file_path)} ({len(self.labels)})", foreground="green")
                self.log_message(f"Labels cargados: {file_path}")
                self.log_message(f"Número de labels: {len(self.labels)}")
                
                self.setup_labels_editor()
                self.process_data()
                
            except Exception as e:
                messagebox.showerror("Error", f"Error al cargar labels:\n{str(e)}")
                self.log_message(f"Error cargando labels: {str(e)}")
    
    def select_output_folder(self):
        """Seleccionar carpeta de salida"""
        folder_path = filedialog.askdirectory(title="Seleccionar carpeta de salida")
        
        if folder_path:
            self.output_folder = folder_path
            self.output_label.config(text=f"Carpeta salida: {folder_path}", foreground="green")
            self.log_message(f"Carpeta de salida seleccionada: {folder_path}")
    
    def setup_labels_editor(self):
        """Configurar editor de labels"""
        # Limpiar frame anterior
        for widget in self.labels_scrollable_frame.winfo_children():
            widget.destroy()
        
        # Crear editores para cada label
        for i, label in enumerate(self.labels):
            row_frame = ttk.Frame(self.labels_scrollable_frame)
            row_frame.pack(fill=tk.X, pady=2)
            
            ttk.Label(row_frame, text=f"Original: {label[:30]}...", width=35).pack(side=tk.LEFT)
            
            entry_var = tk.StringVar(value=self.custom_labels[label])
            entry = ttk.Entry(row_frame, textvariable=entry_var, width=25)
            entry.pack(side=tk.LEFT, padx=(10, 0))
            
            # Callback para actualizar el diccionario
            def update_label(var=entry_var, orig=label):
                self.custom_labels[orig] = var.get()
            
            entry_var.trace('w', lambda *args, var=entry_var, orig=label: update_label(var, orig))
    
    def process_data(self):
        """Procesar datos cargados"""
        if self.data is None or not self.labels:
            return
        
        try:
            # Seleccionar solo columnas pares (datos de voltaje)
            columnas_pares_idx = [i for i in range(1, self.data.shape[1], 2)]
            data_filtrada = self.data[:, columnas_pares_idx]
            
            # Crear nombres únicos para las columnas
            cols = []
            for i, label in enumerate(self.labels):
                if i < len(columnas_pares_idx):
                    # Usar nombre personalizado
                    base_name = self.custom_labels[label].strip()
                    if base_name in cols:
                        # Si ya existe, agregar índice
                        counter = 2
                        while f"{base_name}_{counter}" in cols:
                            counter += 1
                        cols.append(f"{base_name}_{counter}")
                    else:
                        cols.append(base_name)
            
            # Crear DataFrame con datos en voltios (sin conversión automática a kV)
            self.df = pd.DataFrame(data_filtrada, columns=cols)
            
            # Actualizar lista de columnas
            self.update_columns_list()
            
            self.log_message(f"Datos procesados: {self.df.shape}")
            self.log_message(f"Datos en voltios - Conversión según unidad seleccionada")
            
            # Generar vista previa
            self.generate_preview()
            
        except Exception as e:
            messagebox.showerror("Error", f"Error procesando datos:\n{str(e)}")
            self.log_message(f"Error procesando datos: {str(e)}")
    
    def update_columns_list(self):
        """Actualizar lista de columnas disponibles"""
        self.columns_listbox.delete(0, tk.END)
        
        if self.df is not None:
            for col in self.df.columns:
                self.columns_listbox.insert(tk.END, col)
    
    def select_all_columns(self):
        """Seleccionar todas las columnas"""
        self.columns_listbox.select_set(0, tk.END)
    
    def deselect_all_columns(self):
        """Deseleccionar todas las columnas"""
        self.columns_listbox.selection_clear(0, tk.END)
    
    def apply_unit_conversion(self, data):
        """Aplicar conversión de unidades a los datos"""
        selected_unit = self.y_unit_var.get()
        if selected_unit in self.y_unit_factors:
            factor, _ = self.y_unit_factors[selected_unit]
            return data * factor
        return data
    
    def get_unit_label(self):
        """Obtener la etiqueta de la unidad actual"""
        selected_unit = self.y_unit_var.get()
        if selected_unit in self.y_unit_factors:
            return selected_unit
        return "Valores"
    
    def get_reference_value_in_current_units(self):
        """Obtener valor de referencia convertido a las unidades actuales"""
        try:
            # El valor de referencia se asume que está en kV
            ref_value_kv = float(self.reference_line_var.get())
            selected_unit = self.y_unit_var.get()
            
            if selected_unit == 'Voltios (V)':
                return ref_value_kv * 1000  # kV a V
            elif selected_unit == 'Kilovoltios (kV)':
                return ref_value_kv  # kV a kV
            elif selected_unit == 'Megavoltios (MV)':
                return ref_value_kv / 1000  # kV a MV
            elif selected_unit == 'Milivoltios (mV)':
                return ref_value_kv * 1000000  # kV a mV
            else:
                return ref_value_kv
        except ValueError:
            return 707.1  # Valor por defecto
    
    def generate_preview(self):
        """Generar vista previa con primera columna"""
        if self.df is None or self.df.empty:
            return
        
        try:
            self.ax.clear()
            
            # Usar primera columna para preview
            col = self.df.columns[0]
            data = self.df[col].dropna()
            
            if len(data) > 0:
                # Aplicar conversión de unidades
                converted_data = self.apply_unit_conversion(data)
                
                # Calcular estadísticas básicas
                stats = {
                    'mean': np.mean(converted_data),
                    'median': np.median(converted_data),
                    'std': np.std(converted_data),
                    'min': np.min(converted_data),
                    'max': np.max(converted_data)
                }
                
                # Crear gráfico de barras simple
                estadisticas = ['Media', 'Mediana', 'Std', 'Min', 'Max']
                valores = [stats['mean'], stats['median'], stats['std'], stats['min'], stats['max']]
                
                bars = self.ax.bar(estadisticas, valores, color='steelblue', alpha=0.8)
                
                # Línea de referencia (si está habilitada)
                if self.show_reference_var.get():
                    ref_value = self.get_reference_value_in_current_units()
                    unit_symbol = self.y_unit_factors[self.y_unit_var.get()][1]
                    self.ax.axhline(y=ref_value, color='red', linestyle='--', linewidth=1.5, 
                                   label=f'Referencia ({ref_value:.1f} {unit_symbol})')
                    self.ax.legend(fontsize=8)
                
                self.ax.set_title(f'Vista Previa: {col[:20]}...', fontsize=9)
                self.ax.set_ylabel(self.get_unit_label(), fontsize=8)
                self.ax.tick_params(axis='x', rotation=45, labelsize=7)
                self.ax.tick_params(axis='y', labelsize=7)
                
                self.fig.tight_layout()
                self.canvas.draw()
                
        except Exception as e:
            self.log_message(f"Error en vista previa: {str(e)}")
    
    def generate_analysis(self):
        """Generar análisis estadístico completo"""
        if self.df is None:
            messagebox.showwarning("Advertencia", "Primero procese los datos")
            return
        
        if not self.output_folder:
            messagebox.showwarning("Advertencia", "Seleccione una carpeta de salida")
            return
        
        selected_indices = self.columns_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("Advertencia", "Seleccione al menos una columna")
            return
        
        try:
            # Crear carpeta de salida específica
            if self.timestamp_folder_var.get():
                timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
                analysis_folder = os.path.join(self.output_folder, f"analisis_estadistico_{timestamp}")
            else:
                analysis_folder = os.path.join(self.output_folder, "analisis_estadistico")
            
            os.makedirs(analysis_folder, exist_ok=True)
            
            self.log_message(f"Iniciando análisis en: {analysis_folder}")
            
            # Limpiar imágenes anteriores
            self.clean_previous_images(analysis_folder)
            
            # Obtener configuración
            try:
                font_size = int(self.font_size_var.get())
                dpi_value = int(self.dpi_var.get())
                alpha_value = float(self.alpha_var.get())
            except ValueError:
                font_size = 10
                dpi_value = 300
                alpha_value = 0.8
            
            # Actualizar configuración matplotlib
            mpl.rcParams['font.size'] = font_size
            
            # Generar gráficos para columnas seleccionadas
            selected_columns = [self.df.columns[i] for i in selected_indices]
            
            total_graphs = 0
            graph_types = []
            
            if self.barras_var.get():
                graph_types.append('barras')
            if self.boxplot_var.get():
                graph_types.append('boxplot')
            if self.histogram_var.get():
                graph_types.append('histograma')
            
            total_graphs = len(selected_columns) * len(graph_types)
            
            self.log_message(f"Generando {total_graphs} gráficos para {len(selected_columns)} columnas...")
            
            progress = 0
            all_statistics = {}
            
            for graph_type in graph_types:
                type_statistics = {}
                
                for col in selected_columns:
                    progress += 1
                    self.log_message(f"[{progress}/{total_graphs}] Generando {graph_type}: {col[:30]}...")
                    
                    stats = self.generate_statistical_chart(
                        self.df, col, graph_type, analysis_folder, dpi_value, alpha_value
                    )
                    
                    if stats:
                        type_statistics[col] = stats
                
                all_statistics[graph_type] = type_statistics
            
            # Generar resúmenes CSV si está habilitado
            if self.create_summary_var.get():
                self.generate_summary_reports(all_statistics, analysis_folder)
            
            self.log_message(f"✅ Análisis completado: {analysis_folder}")
            messagebox.showinfo("Éxito", f"Análisis estadístico completado.\n{total_graphs} gráficos generados.")
            
        except Exception as e:
            messagebox.showerror("Error", f"Error durante el análisis:\n{str(e)}")
            self.log_message(f"❌ Error en análisis: {str(e)}")
    
    def clean_previous_images(self, folder_path):
        """Limpiar imágenes anteriores"""
        for ext in ['*.png', '*.pdf', '*.svg', '*.jpg']:
            for file_path in glob.glob(os.path.join(folder_path, ext)):
                try:
                    os.remove(file_path)
                except Exception as e:
                    self.log_message(f"No se pudo eliminar {file_path}: {e}")
    
    def generate_statistical_chart(self, df, column, chart_type, output_folder, dpi_value, alpha_value):
        """Generar gráfico estadístico para una columna"""
        try:
            # Obtener datos originales en voltios
            data = df[column].dropna()
            if len(data) == 0:
                self.log_message(f"⚠️  Columna '{column}' sin datos válidos")
                return None
            
            # Aplicar conversión de unidades
            converted_data = self.apply_unit_conversion(data)
            
            # Calcular estadísticas
            stats = {
                'mean': np.mean(converted_data),
                'median': np.median(converted_data),
                'std': np.std(converted_data),
                'min': np.min(converted_data),
                'max': np.max(converted_data),
                'count': len(converted_data)
            }
            
            # Agregar estadísticas adicionales si están habilitadas
            if self.show_percentiles_var.get():
                stats['25%'] = np.percentile(converted_data, 25)
                stats['75%'] = np.percentile(converted_data, 75)
            
            # Crear figura con tamaño específico
            plt.figure(figsize=(7.54/2.54, 7.09/2.54))
            
            # Obtener etiqueta de unidad
            unit_label = self.get_unit_label()
            
            if chart_type == 'barras':
                estadisticas = ['Media', 'Mediana', 'Std', 'Min', 'Max']
                valores = [stats['mean'], stats['median'], stats['std'], stats['min'], stats['max']]
                
                if self.show_percentiles_var.get():
                    estadisticas.extend(['Q1', 'Q3'])
                    valores.extend([stats['25%'], stats['75%']])
                
                bars = plt.bar(estadisticas, valores, color='steelblue', alpha=alpha_value, edgecolor='black')
                
                # Línea de referencia (si está habilitada)
                if self.show_reference_var.get():
                    ref_value = self.get_reference_value_in_current_units()
                    unit_symbol = self.y_unit_factors[self.y_unit_var.get()][1]
                    plt.axhline(y=ref_value, color='red', linestyle='--', linewidth=2, 
                               label=f'Vp Admitido ({ref_value:.1f} {unit_symbol})')
                    plt.legend(fontsize=8)
                
                # Valores en las barras
                for bar, valor in zip(bars, valores):
                    plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + abs(valor)*0.01, 
                            f'{valor:.1f}', ha='center', va='bottom', fontsize=8)
                
                plt.title(f'Estadísticas: {column[:25]}...' if len(column) > 25 else f'Estadísticas: {column}')
                plt.ylabel(unit_label)
                plt.xticks(rotation=45)
                
            elif chart_type == 'boxplot':
                if stats['std'] < 1e-6:
                    plt.text(0.5, 0.5, f'Valor Constante:\n{stats["mean"]:.1f} {self.y_unit_factors[self.y_unit_var.get()][1]}', 
                            ha='center', va='center', transform=plt.gca().transAxes, fontsize=10)
                else:
                    box_plot = plt.boxplot(converted_data, patch_artist=True, 
                                          boxprops=dict(facecolor='lightblue', alpha=alpha_value))
                    
                    # Configurar outliers si está habilitado
                    if not self.show_outliers_var.get():
                        for outlier in box_plot['fliers']:
                            outlier.set_visible(False)
                
                plt.title(f'Boxplot: {column[:25]}...' if len(column) > 25 else f'Boxplot: {column}')
                plt.ylabel(unit_label)
                plt.xticks([1], [column.split('@')[0] if '@' in column else column[:10]])
                
            elif chart_type == 'histograma':
                if stats['std'] < 1e-6:
                    plt.text(0.5, 0.5, f'Valor Constante:\n{stats["mean"]:.1f} {self.y_unit_factors[self.y_unit_var.get()][1]}', 
                            ha='center', va='center', transform=plt.gca().transAxes, fontsize=10)
                else:
                    plt.hist(converted_data, bins=20, color='lightgreen', alpha=alpha_value, edgecolor='black')
                    plt.axvline(stats['mean'], color='red', linestyle='--', 
                               label=f'Media: {stats["mean"]:.1f} {self.y_unit_factors[self.y_unit_var.get()][1]}')
                    plt.axvline(stats['median'], color='blue', linestyle='--', 
                               label=f'Mediana: {stats["median"]:.1f} {self.y_unit_factors[self.y_unit_var.get()][1]}')
                    
                    # Añadir intervalos de confianza si está habilitado
                    if self.show_confidence_var.get():
                        ci_lower = stats['mean'] - 1.96 * stats['std'] / np.sqrt(stats['count'])
                        ci_upper = stats['mean'] + 1.96 * stats['std'] / np.sqrt(stats['count'])
                        plt.axvline(ci_lower, color='orange', linestyle=':', alpha=0.7)
                        plt.axvline(ci_upper, color='orange', linestyle=':', alpha=0.7)
                    
                    plt.legend(fontsize=8)
                
                plt.title(f'Histograma: {column[:25]}...' if len(column) > 25 else f'Histograma: {column}')
                plt.xlabel(unit_label)
                plt.ylabel('Frecuencia')
            
            plt.tight_layout()
            
            # Guardar imagen
            safe_filename = column.replace('@', '_').replace('/', '_').replace(' ', '_').replace(':', '_')
            image_format = self.image_format_var.get()
            unit_suffix = self.y_unit_factors[self.y_unit_var.get()][1]
            file_path = os.path.join(output_folder, f'stats_{chart_type}_{safe_filename}_{unit_suffix}.{image_format}')
            
            plt.savefig(file_path, dpi=dpi_value, bbox_inches='tight', format=image_format)
            plt.close()  # Importante: cerrar para liberar memoria
            
            return stats
            
        except Exception as e:
            self.log_message(f"❌ Error generando {chart_type} para {column}: {str(e)}")
            plt.close()  # Asegurar que se cierre en caso de error
            return None
    
    def generate_summary_reports(self, all_statistics, output_folder):
        """Generar reportes resumen en CSV"""
        try:
            unit_suffix = self.y_unit_factors[self.y_unit_var.get()][1]
            
            for graph_type, statistics in all_statistics.items():
                if statistics:
                    df_stats = pd.DataFrame(statistics).T
                    csv_file = os.path.join(output_folder, f'resumen_estadisticas_{graph_type}_{unit_suffix}.csv')
                    df_stats.to_csv(csv_file, index=True)
                    self.log_message(f"📊 Resumen guardado: resumen_estadisticas_{graph_type}_{unit_suffix}.csv")
            
            self.log_message("📈 Todos los resúmenes CSV generados")
            
        except Exception as e:
            self.log_message(f"❌ Error generando resúmenes: {str(e)}")
    
    def open_output_folder(self):
        """Abrir carpeta de salida en el explorador"""
        if self.output_folder:
            try:
                os.startfile(self.output_folder)
            except:
                messagebox.showinfo("Info", f"Carpeta de salida:\n{self.output_folder}")
        else:
            messagebox.showwarning("Advertencia", "No se ha seleccionado carpeta de salida")

def main():
    root = tk.Tk()
    app = StatisticalAnalyzer(root)
    root.mainloop()

if __name__ == "__main__":
    main()
