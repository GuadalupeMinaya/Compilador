"""Interfaz gráfica: léxico -> sintáctico -> semántico (tabla de símbolos) -> código intermedio -> JavaScript."""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os

from semantico import analizar_semantica_completo
from motor import procesar_codigo, ErrorLexer
from diagnosticos import (ejecutar_js, node_disponible, posicion_error_traduccion,
                          sugerencia, sugerencia_lexica)


NOMBRES_ESTRUCTURAS = [
    ("declaraciones", "declaración de variables", "declaraciones de variables"),
    ("funciones", "definición de función", "definiciones de función"),
    ("asignaciones", "asignación", "asignaciones"),
    ("llamadas", "llamada a función", "llamadas a función"),
    ("condicionales", "condicional (if)", "condicionales (if)"),
    ("ciclos_while", "ciclo while", "ciclos while"),
    ("ciclos_for", "ciclo for", "ciclos for"),
    ("prints", "instrucción print", "instrucciones print"),
    ("returns", "instrucción return", "instrucciones return"),
]

NOMBRES_SEMANTICOS = [
    ("variables", "variable declarada", "variables declaradas"),
    ("parametros", "parámetro", "parámetros"),
    ("funciones", "función", "funciones"),
    ("asignaciones", "asignación verificada", "asignaciones verificadas"),
    ("llamadas", "llamada a función verificada", "llamadas a función verificadas"),
    ("retornos", "return verificado", "returns verificados"),
]

COLORES_TOKEN = {
    "PALABRA_RESERVADA": "#8e44ad", "IDENTIFICADOR": "#2980b9",
    "NUMERO_ENTERO": "#16a085", "NUMERO_DECIMAL": "#16a085", "CADENA": "#d35400", "CARACTER": "#d35400",
    "OP_RELACIONAL": "#c0392b", "OP_ASIGNACION": "#c0392b", "OP_ARITMETICO": "#c0392b", "OP_LOGICO": "#c0392b", "OP_INCREMENTO": "#c0392b", "CORCHETE_IZQ": "#7f8c8d", "CORCHETE_DER": "#7f8c8d",
    "ERROR_LEXICO": "#e74c3c",
}

COLUMNAS_SINTACTICO = (("num", "#", 36, "center"), ("linea", "Línea", 52, "center"),
                       ("tipo", "Tipo de error", 170, "w"), ("descripcion", "Descripción", 300, "w"))
COLUMNAS_SEMANTICO = (("num", "#", 36, "center"), ("linea", "Línea", 52, "center"),
                      ("col", "Col.", 45, "center"), ("tipo", "Tipo de error", 170, "w"),
                      ("descripcion", "Descripción", 290, "w"))

SAMPLE = ("int main(void) {\n"
          '    char nombre[] = "Maria";\n'
          "    char inicial = 'M';\n"
          '    double nota = 92.75;\n'
          '    bool aprobado = nota >= 70;\n'
          '    print("Estudiante:", nombre, "Inicial:", inicial);\n'
          '    if (aprobado) { print("Aprobada con", nota); }\n'
          '    return 0;\n}\n')

COLUMNAS_SIMBOLOS = (("nombre", "Nombre", 140, "w"), ("clase", "Clase", 80, "w"), ("tipo", "Tipo", 65, "w"),
                     ("ambito", "Ámbito", 190, "w"), ("linea", "Línea", 58, "center"),
                     ("detalle", "Detalle", 110, "w"))
COLUMNAS_CUADRUPLAS = (("num", "#", 40, "center"), ("op", "Operador", 85, "w"), ("arg1", "Arg. 1", 100, "w"),
                       ("arg2", "Arg. 2", 100, "w"), ("res", "Resultado", 100, "w"))

TITULOS_PESTANAS = {"trad": "Traducción JS", "ir": "Intermedio", "sim": "Símbolos",
                    "sem": "Semántico", "sint": "Sintáctico", "lex": "Léxico"}
ICONOS = {"ok": " ✓", "error": " ✗", "no": " –", None: ""}


class AnalizadorCompiladorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Compilador y Traductor")
        self.root.geometry("1280x760")
        self.root.minsize(1000, 600)
        self.root.configure(bg="#eef1f5")
        self._lineas_error = []
        self.javascript = ""
        self._configurar_estilos()
        self._construir_interfaz()

    # ------------------------------------------------------------------ estilos
    def _configurar_estilos(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TButton", font=("Segoe UI", 10), padding=8, relief="flat")
        style.configure("Accent.TButton", font=("Segoe UI", 10, "bold"), padding=8,
                        background="#2e7d32", foreground="white")
        style.map("Accent.TButton", background=[("active", "#256428")])
        style.configure("Treeview", font=("Consolas", 10), rowheight=26,
                        background="white", fieldbackground="white", borderwidth=0)
        style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"),
                        background="#34495e", foreground="white", padding=6)
        style.map("Treeview.Heading", background=[("active", "#2c3e50")])
        style.configure("TNotebook.Tab", font=("Segoe UI", 10, "bold"), padding=(9, 7))

    # ------------------------------------------------------------------ interfaz
    def _construir_interfaz(self):
        encabezado = tk.Frame(self.root, bg="#2c3e50", height=64)
        encabezado.pack(fill="x")
        encabezado.pack_propagate(False)
        tk.Label(encabezado, text="Compilador y Traductor", font=("Segoe UI", 16, "bold"),
                 bg="#2c3e50", fg="white").pack(side="left", padx=20)

        barra = tk.Frame(self.root, bg="#eef1f5", pady=10, padx=16)
        barra.pack(fill="x")
        ttk.Button(barra, text="Abrir archivo...", command=self.abrir_archivo).pack(side="left", padx=(0, 6))
        ttk.Button(barra, text="Analizar código", style="Accent.TButton", command=self.analizar).pack(side="left", padx=6)
        ttk.Button(barra, text="Limpiar", command=self.limpiar).pack(side="left", padx=6)
        self.lbl_estado = tk.Label(barra, text="Listo", font=("Segoe UI", 10), bg="#eef1f5", fg="#5a6572")
        self.lbl_estado.pack(side="right", padx=4)

        panel = tk.PanedWindow(self.root, orient="horizontal", sashwidth=6, bg="#eef1f5", bd=0)
        panel.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        # -------- Editor --------
        marco_izq = tk.Frame(panel, bg="white", highlightbackground="#d0d5db", highlightthickness=1)
        tk.Label(marco_izq, text="Código fuente", font=("Segoe UI", 10, "bold"),
                 bg="#f4f6f8", fg="#2c3e50", anchor="w", padx=10, pady=6).pack(fill="x")
        cuerpo_izq = tk.Frame(marco_izq, bg="white")
        cuerpo_izq.pack(fill="both", expand=True)
        self.numeros = tk.Canvas(cuerpo_izq, width=42, bg="#f4f6f8", highlightthickness=0)
        self.numeros.pack(side="left", fill="y")
        self.editor = tk.Text(cuerpo_izq, wrap="none", font=("Consolas", 11), bd=0,
                              padx=8, pady=8, bg="white", undo=True)
        self.editor.pack(side="left", fill="both", expand=True)
        scroll_editor = ttk.Scrollbar(cuerpo_izq, orient="vertical", command=self._scroll_editor)
        scroll_editor.pack(side="right", fill="y")
        self.editor.configure(yscrollcommand=lambda a, b: self._sync_scroll(scroll_editor, a, b))
        for evento in ("<KeyRelease>", "<ButtonRelease>", "<MouseWheel>", "<Configure>"):
            self.editor.bind(evento, lambda e: self._redibujar_numeros())
        self.editor.insert("1.0", SAMPLE)
        self.editor.tag_configure("linea_error", background="#fdecea")
        self.editor.tag_configure("token_error", background="#ffb3ad", foreground="#b71c1c", underline=True)
        self.editor.tag_configure("token_adv", background="#fff3c4", underline=True)
        self.editor.tag_configure("flash_error", background="#ffcc80")
        self.root.after(50, self._redibujar_numeros)
        panel.add(marco_izq, stretch="always")

        # -------- Resultados con pestañas --------
        marco_der = tk.Frame(panel, bg="white", highlightbackground="#d0d5db", highlightthickness=1)
        tk.Label(marco_der, text="Resultados del análisis", font=("Segoe UI", 10, "bold"),
                 bg="#f4f6f8", fg="#2c3e50", anchor="w", padx=10, pady=6).pack(fill="x")
        self.notebook = ttk.Notebook(marco_der)
        self.notebook.pack(fill="both", expand=True, padx=8, pady=8)

        self.tab_trad = tk.Frame(self.notebook, bg="white")
        self.tab_sem = tk.Frame(self.notebook, bg="white")
        self.tab_sint = tk.Frame(self.notebook, bg="white")
        self.tab_lexico = tk.Frame(self.notebook, bg="white")
        self.tab_sim = tk.Frame(self.notebook, bg="white")
        self.tab_ir = tk.Frame(self.notebook, bg="white")
        self._construir_pestana_simbolos()
        self._construir_pestana_intermedio()

        # Pestañas semántica y sintáctica: mismo diseño (texto o tabla de errores)
        self.sem = self._crear_panel(self.tab_sem, COLUMNAS_SEMANTICO)
        self.sin = self._crear_panel(self.tab_sint, COLUMNAS_SINTACTICO)

        # Pestaña léxica: tabla de tokens
        self.lbl_resumen = tk.Label(self.tab_lexico, text="", font=("Segoe UI", 9), bg="white",
                                    fg="#5a6572", anchor="w", justify="left", wraplength=430, padx=4, pady=4)
        self.lbl_resumen.pack(fill="x")
        tabla_frame = tk.Frame(self.tab_lexico, bg="white")
        tabla_frame.pack(fill="both", expand=True)
        columnas = ("tipo", "lexema", "linea", "columna")
        self.tabla = ttk.Treeview(tabla_frame, columns=columnas, show="headings")
        for col, titulo in zip(columnas, ("Tipo de token", "Lexema", "Línea", "Col.")):
            self.tabla.heading(col, text=titulo)
        self.tabla.column("tipo", width=175, minwidth=160, stretch=False)
        self.tabla.column("lexema", width=130, minwidth=90, stretch=True)
        self.tabla.column("linea", width=55, minwidth=50, anchor="center", stretch=False)
        self.tabla.column("columna", width=55, minwidth=50, anchor="center", stretch=False)
        sv = ttk.Scrollbar(tabla_frame, orient="vertical", command=self.tabla.yview)
        sh = ttk.Scrollbar(tabla_frame, orient="horizontal", command=self.tabla.xview)
        self.tabla.configure(yscrollcommand=sv.set, xscrollcommand=sh.set)
        sv.pack(side="right", fill="y")
        sh.pack(side="bottom", fill="x")
        self.tabla.pack(fill="both", expand=True, side="left")
        for tipo, color in COLORES_TOKEN.items():
            self.tabla.tag_configure(tipo, foreground=color)

        # Cuarta fase: resultado JavaScript, seleccionable y copiable.
        self.lbl_traduccion = tk.Label(self.tab_trad, text="Presione «Analizar código» para ver la traducción.",
                                      font=("Segoe UI", 11, "bold"), bg="white", fg="#5a6572",
                                      anchor="w", padx=12, pady=12)
        self.lbl_traduccion.pack(fill="x")
        # Barra de acciones de la traducción
        barra_trad = tk.Frame(self.tab_trad, bg="white")
        barra_trad.pack(fill="x", padx=9, pady=(0, 6))
        self.btn_ejecutar = ttk.Button(barra_trad, text="Ejecutar", command=self.ejecutar_js,
                                       state="disabled")
        self.btn_ejecutar.pack(side="left", padx=(0, 6))
        # Esquina derecha, junto al código traducido
        self.btn_guardar = ttk.Button(barra_trad, text="Guardar", command=self.guardar_js, state="disabled")
        self.btn_guardar.pack(side="right")
        self.btn_copiar = ttk.Button(barra_trad, text="Copiar", command=self.copiar_js, state="disabled")
        self.btn_copiar.pack(side="right", padx=(0, 6))
        self.btn_ver_errores = ttk.Button(barra_trad, text="Ver errores →", command=self._ir_a_pestana_error)
        self._pestana_error = None   # el botón solo se muestra cuando la traducción está bloqueada

        # Salida de la ejecución (abajo, se empaqueta antes para reservar su espacio)
        marco_salida = tk.Frame(self.tab_trad, bg="white")   # oculto hasta pulsar «Probar traducción»
        self.marco_salida = marco_salida
        tk.Label(marco_salida, text="Resultado de la prueba", font=("Segoe UI", 9, "bold"),
                 bg="white", fg="#2c3e50", anchor="w").pack(fill="x", pady=(4, 2))
        self.texto_salida = tk.Text(marco_salida, wrap="word", font=("Consolas", 10), height=7,
                                    bg="#1e2530", fg="#e6edf3", bd=0, padx=10, pady=8)
        self.texto_salida.pack(fill="x")
        self.texto_salida.tag_configure("error", foreground="#ff8a80")
        self.texto_salida.tag_configure("tenue", foreground="#9aa5b1")
        self.texto_salida.config(state="disabled")

        marco_js = tk.Frame(self.tab_trad, bg="white")
        self.marco_js = marco_js
        marco_js.pack(fill="both", expand=True, padx=9, pady=(0, 4))
        self.texto_js = tk.Text(marco_js, wrap="none", font=("Consolas", 10),
                                bg="#f8fafc", bd=0, padx=10, pady=9)
        self.texto_js.pack(side="left", fill="both", expand=True)
        sb_js = ttk.Scrollbar(marco_js, orient="vertical", command=self.texto_js.yview)
        sb_js.pack(side="right", fill="y")
        self.texto_js.configure(yscrollcommand=sb_js.set, state="disabled")
        self.texto_js.tag_configure("titulo", font=("Segoe UI", 10, "bold"), foreground="#c0392b")
        self.texto_js.tag_configure("ayuda", foreground="#1b5e20")
        self.notebook.add(self.tab_trad, text=TITULOS_PESTANAS["trad"])
        self.notebook.add(self.tab_ir, text=TITULOS_PESTANAS["ir"])
        self.notebook.add(self.tab_sim, text=TITULOS_PESTANAS["sim"])
        self.notebook.add(self.tab_sem, text=TITULOS_PESTANAS["sem"])
        self.notebook.add(self.tab_sint, text=TITULOS_PESTANAS["sint"])
        self.notebook.add(self.tab_lexico, text=TITULOS_PESTANAS["lex"])
        self.notebook.select(self.tab_trad)
        panel.add(marco_der, stretch="always")

        # Panel inferior de errores léxicos
        self.marco_errores = tk.Frame(self.root, bg="#fff5f5", highlightbackground="#e6b3ae", highlightthickness=1)
        tk.Label(self.marco_errores, text="Errores léxicos (doble clic para ir a la línea)",
                 font=("Segoe UI", 9, "bold"), bg="#fff5f5", fg="#c0392b", anchor="w").pack(fill="x", padx=10, pady=(6, 2))
        self.lista_errores = tk.Listbox(self.marco_errores, height=3, font=("Consolas", 10),
                                        bg="#fff5f5", fg="#c0392b", bd=0, highlightthickness=0,
                                        selectbackground="#f5c6c2", activestyle="none")
        self.lista_errores.pack(fill="x", padx=10, pady=(0, 8))
        self.lista_errores.bind("<Double-Button-1>", self._ir_a_linea_error)

    def _construir_pestana_simbolos(self):
        """Tabla de símbolos generada por el análisis semántico."""
        self.lbl_simbolos = tk.Label(self.tab_sim, text="Aún no se ha ejecutado el análisis.",
                                     font=("Segoe UI", 13, "bold"), bg="white", fg="#5a6572",
                                     anchor="w", justify="left", padx=14, pady=14)
        self.lbl_simbolos.pack(fill="x")
        marco = tk.Frame(self.tab_sim, bg="white")
        marco.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.tabla_simbolos = ttk.Treeview(marco, columns=[c[0] for c in COLUMNAS_SIMBOLOS],
                                           show="headings", selectmode="browse")
        for col, titulo, ancho, ancla in COLUMNAS_SIMBOLOS:
            self.tabla_simbolos.heading(col, text=titulo)
            self.tabla_simbolos.column(col, width=ancho, minwidth=ancho, anchor=ancla,
                                       stretch=(col == "detalle"))
        self.tabla_simbolos.tag_configure("funcion", foreground="#8e44ad")
        self.tabla_simbolos.tag_configure("parametro", foreground="#16a085")
        sv = ttk.Scrollbar(marco, orient="vertical", command=self.tabla_simbolos.yview)
        sh = ttk.Scrollbar(marco, orient="horizontal", command=self.tabla_simbolos.xview)
        self.tabla_simbolos.configure(yscrollcommand=sv.set, xscrollcommand=sh.set)
        sv.pack(side="right", fill="y")
        sh.pack(side="bottom", fill="x")
        self.tabla_simbolos.pack(side="left", fill="both", expand=True)
        self.tabla_simbolos.bind("<Double-Button-1>", self._ir_a_linea_simbolo)
        self._filas_simbolos = {}   # id de fila -> línea

    def _construir_pestana_intermedio(self):
        """Código de tres direcciones: vista de texto y vista de cuádruplas."""
        self.intermedio_texto = ""
        self.lbl_intermedio = tk.Label(self.tab_ir, text="Presione «Analizar código» para ver el código intermedio.",
                                       font=("Segoe UI", 11, "bold"), bg="white", fg="#5a6572",
                                       anchor="w", padx=12, pady=12)
        self.lbl_intermedio.pack(fill="x")
        barra = tk.Frame(self.tab_ir, bg="white")
        barra.pack(fill="x", padx=9, pady=(0, 6))
        self.var_vista_ir = tk.StringVar(value="texto")
        ttk.Radiobutton(barra, text="Texto", value="texto", variable=self.var_vista_ir,
                        command=self._cambiar_vista_intermedio).pack(side="left", padx=(0, 10))
        ttk.Radiobutton(barra, text="Cuádruplas", value="cuadruplas", variable=self.var_vista_ir,
                        command=self._cambiar_vista_intermedio).pack(side="left")
        self.btn_guardar_ir = ttk.Button(barra, text="Guardar", command=self.guardar_intermedio, state="disabled")
        self.btn_guardar_ir.pack(side="right")
        self.btn_copiar_ir = ttk.Button(barra, text="Copiar", command=self.copiar_intermedio, state="disabled")
        self.btn_copiar_ir.pack(side="right", padx=(0, 6))

        self.marco_ir_texto = tk.Frame(self.tab_ir, bg="white")
        self.marco_ir_texto.pack(fill="both", expand=True, padx=9, pady=(0, 6))
        self.texto_ir = tk.Text(self.marco_ir_texto, wrap="none", font=("Consolas", 10),
                                bg="#f8fafc", bd=0, padx=10, pady=9)
        sb_ir = ttk.Scrollbar(self.marco_ir_texto, orient="vertical", command=self.texto_ir.yview)
        sb_ir.pack(side="right", fill="y")
        self.texto_ir.pack(side="left", fill="both", expand=True)
        self.texto_ir.configure(yscrollcommand=sb_ir.set, state="disabled")
        self.texto_ir.tag_configure("func", font=("Consolas", 10, "bold"), foreground="#8e44ad")
        self.texto_ir.tag_configure("etiqueta", font=("Consolas", 10, "bold"), foreground="#2980b9")
        self.texto_ir.tag_configure("salto", foreground="#c0392b")
        self.texto_ir.tag_configure("error", foreground="#c0392b")

        self.marco_ir_tabla = tk.Frame(self.tab_ir, bg="white")   # oculto hasta elegir «Cuádruplas»
        self.tabla_ir = ttk.Treeview(self.marco_ir_tabla, columns=[c[0] for c in COLUMNAS_CUADRUPLAS],
                                     show="headings", selectmode="browse")
        for col, titulo, ancho, ancla in COLUMNAS_CUADRUPLAS:
            self.tabla_ir.heading(col, text=titulo)
            self.tabla_ir.column(col, width=ancho, minwidth=ancho, anchor=ancla, stretch=(col == "res"))
        sv_ir = ttk.Scrollbar(self.marco_ir_tabla, orient="vertical", command=self.tabla_ir.yview)
        self.tabla_ir.configure(yscrollcommand=sv_ir.set)
        sv_ir.pack(side="right", fill="y")
        self.tabla_ir.pack(side="left", fill="both", expand=True)

    def _cambiar_vista_intermedio(self):
        if self.var_vista_ir.get() == "texto":
            self.marco_ir_tabla.pack_forget()
            self.marco_ir_texto.pack(fill="both", expand=True, padx=9, pady=(0, 6))
        else:
            self.marco_ir_texto.pack_forget()
            self.marco_ir_tabla.pack(fill="both", expand=True, padx=9, pady=(0, 6))

    def _crear_panel(self, tab, columnas):
        """Crea título + cuadro de texto + tabla de errores (la tabla solo se ve cuando hay errores)."""
        p = {}
        p["titulo"] = tk.Label(tab, text="Aún no se ha ejecutado el análisis.", font=("Segoe UI", 13, "bold"),
                               bg="white", fg="#5a6572", anchor="w", justify="left", padx=14, pady=14)
        p["titulo"].pack(fill="x")
        p["txt"] = tk.Text(tab, wrap="word", font=("Segoe UI", 10), bg="#fafbfc", bd=0,
                           padx=14, pady=12, height=10)
        p["txt"].pack(fill="both", expand=True, padx=10, pady=(0, 10))
        p["txt"].tag_configure("negrita", font=("Segoe UI", 10, "bold"), foreground="#2c3e50")
        p["txt"].tag_configure("tenue", foreground="#5a6572")
        p["txt"].config(state="disabled")

        p["marco"] = tk.Frame(tab, bg="white")
        p["tree"] = ttk.Treeview(p["marco"], columns=[c[0] for c in columnas],
                                 show="headings", selectmode="browse")
        for col, titulo, ancho, ancla in columnas:
            p["tree"].heading(col, text=titulo)
            p["tree"].column(col, width=ancho, minwidth=ancho, anchor=ancla, stretch=(col == "descripcion"))
        p["tree"].tag_configure("error", foreground="#b71c1c")
        p["tree"].tag_configure("adv", foreground="#8a6d00")
        p["detalle"] = tk.Label(p["marco"], text="", font=("Segoe UI", 10), bg="#fafbfc", fg="#2c3e50",
                                anchor="w", justify="left", wraplength=430, padx=10, pady=8)
        p["detalle"].pack(side="bottom", fill="x")
        sv = ttk.Scrollbar(p["marco"], orient="vertical", command=p["tree"].yview)
        p["tree"].configure(yscrollcommand=sv.set)
        sv.pack(side="right", fill="y")
        p["tree"].pack(side="left", fill="both", expand=True)
        p["pos"] = {}   # id de fila -> (linea, inicio, fin, texto de detalle)
        p["tree"].bind("<<TreeviewSelect>>", lambda e, q=p: self._mostrar_detalle(q))
        p["tree"].bind("<Double-Button-1>", lambda e, q=p: self._ir_a_error(q))
        return p

    # ------------------------------------------------------------------ editor
    def _scroll_editor(self, *args):
        self.editor.yview(*args)
        self._redibujar_numeros()

    def _sync_scroll(self, scrollbar, primero, ultimo):
        scrollbar.set(primero, ultimo)
        self._redibujar_numeros()

    def _redibujar_numeros(self):
        self.numeros.delete("all")
        indice = self.editor.index("@0,0")
        while True:
            info = self.editor.dlineinfo(indice)
            if info is None:
                break
            self.numeros.create_text(36, info[1], anchor="ne", text=str(indice).split(".")[0],
                                     font=("Consolas", 10), fill="#9aa5b1")
            indice = self.editor.index(f"{indice}+1line")

    def _limpiar_marcas(self):
        for tag in ("linea_error", "token_error", "token_adv"):
            self.editor.tag_remove(tag, "1.0", "end")

    @staticmethod
    def _rango_token(token):
        """Rango en índices de Tk para subrayar el token (columnas del lexer empiezan en 1)."""
        col = token.columna - 1
        if token.lexema == "":
            return f"{token.linea}.{max(col - 1, 0)}", f"{token.linea}.{max(col, 1)}"
        return f"{token.linea}.{col}", f"{token.linea}.{col + len(token.lexema)}"

    # ------------------------------------------------------------------ paneles de diagnóstico
    def _alternar(self, p, con_tabla):
        if con_tabla:
            p["txt"].pack_forget()
            p["marco"].pack(fill="both", expand=True, padx=10, pady=(0, 10))
        else:
            p["marco"].pack_forget()
            p["txt"].pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def _poner_texto(self, p, titulo, color, cuerpo=""):
        self._alternar(p, False)
        p["titulo"].config(text=titulo, fg=color)
        p["txt"].config(state="normal")
        p["txt"].delete("1.0", "end")
        p["txt"].insert("1.0", cuerpo)
        p["txt"].config(state="disabled")

    def _vaciar_tabla(self, p):
        for fila in p["tree"].get_children():
            p["tree"].delete(fila)
        p["pos"] = {}
        p["detalle"].config(text="")

    def _mostrar_detalle(self, p):
        sel = p["tree"].selection()
        if sel and sel[0] in p["pos"]:
            p["detalle"].config(text=p["pos"][sel[0]][3])

    def _ir_a_error(self, p):
        sel = p["tree"].selection()
        if not sel or sel[0] not in p["pos"]:
            return
        linea, inicio, _fin, _txt = p["pos"][sel[0]]
        self.editor.see(inicio)
        self.editor.mark_set("insert", inicio)
        self.editor.focus_set()
        self.editor.tag_remove("flash_error", "1.0", "end")
        self.editor.tag_add("flash_error", f"{linea}.0", f"{linea}.end")
        self.root.after(900, lambda: self.editor.tag_remove("flash_error", "1.0", "end"))

    def _agregar_fila(self, p, valores, tag, token, mensaje, tipo=""):
        iid = p["tree"].insert("", "end", values=valores, tags=(tag,))
        inicio, fin = self._rango_token(token)
        detalle = f"Línea {token.linea}, col. {token.columna}: {mensaje}"
        ayuda = sugerencia(tipo, mensaje) if tag == "error" else ""
        if ayuda:
            detalle += f"\n💡 {ayuda}"
        p["pos"][iid] = (token.linea, inicio, fin, detalle)
        if tag == "error":
            self.editor.tag_add("linea_error", f"{token.linea}.0", f"{token.linea}.end")
            self.editor.tag_add("token_error", inicio, fin)
        else:
            self.editor.tag_add("token_adv", inicio, fin)

    def _seleccionar_primera(self, p):
        filas = p["tree"].get_children()
        if filas:
            p["tree"].selection_set(filas[0])
            self._mostrar_detalle(p)

    # ------------------------------------------------------------------ resultados sintácticos
    def _mostrar_errores_sintacticos(self, errores):
        n = len(errores)
        titulo = "1 error sintáctico encontrado" if n == 1 else f"{n} errores sintácticos encontrados"
        self.sin["titulo"].config(text=titulo, fg="#c0392b")
        self._vaciar_tabla(self.sin)
        for i, e in enumerate(errores, 1):
            self._agregar_fila(self.sin, (i, e.token.linea, e.tipo, e.mensaje), "error", e.token, e.mensaje, e.tipo)
        self._alternar(self.sin, True)
        self._seleccionar_primera(self.sin)
        self.editor.see(f"{errores[0].token.linea}.0")

    def _mostrar_exito_sintactico(self, resumen, total_tokens, total_lineas):
        self._poner_texto(self.sin, "Análisis sintáctico correcto ✓", "#2e7d32")
        t = self.sin["txt"]
        t.config(state="normal")
        t.insert("end", "El programa cumple con la gramática del lenguaje. No se encontraron errores sintácticos.\n\n")
        t.insert("end", "Estructuras reconocidas\n", "negrita")
        hubo = False
        for clave, singular, plural in NOMBRES_ESTRUCTURAS:
            n = resumen.get(clave, 0)
            if n:
                hubo = True
                t.insert("end", f"   •  {n} {singular if n == 1 else plural}\n")
        if not hubo:
            t.insert("end", "   (el programa no contiene sentencias)\n", "tenue")
        t.insert("end", f"\n{total_tokens} tokens analizados  ·  {total_lineas} líneas de código", "tenue")
        t.config(state="disabled")

    # ------------------------------------------------------------------ resultados semánticos
    def _analizar_semantica(self, tokens, analisis=None):
        r = analisis if analisis is not None else analizar_semantica_completo(tokens)
        errores, advs, resumen = r["errores"], r["advertencias"], r["resumen"]
        self._vaciar_tabla(self.sem)
        sufijo = f" · {len(advs)} advertencia(s)" if advs else ""

        if errores or advs:
            for i, e in enumerate(errores, 1):
                self._agregar_fila(self.sem, (i, e.token.linea, e.token.columna, e.tipo, e.mensaje),
                                   "error", e.token, e.mensaje, e.tipo)
            for w in advs:
                self._agregar_fila(self.sem, ("⚠", w.token.linea, w.token.columna, w.tipo, w.mensaje),
                                   "adv", w.token, w.mensaje)
            if errores:
                n = len(errores)
                titulo = "1 error semántico encontrado" if n == 1 else f"{n} errores semánticos encontrados"
                color = "#c0392b"
                self.editor.see(f"{errores[0].token.linea}.0")
            else:
                titulo, color = "Análisis semántico correcto ✓ (con advertencias)", "#2e7d32"
            if errores and advs:
                titulo += f" · {len(advs)} advertencia(s)"
            self.sem["titulo"].config(text=titulo, fg=color)
            self._alternar(self.sem, True)
            self._seleccionar_primera(self.sem)
        else:
            self._poner_texto(self.sem, "Análisis semántico correcto ✓", "#2e7d32")
            t = self.sem["txt"]
            t.config(state="normal")
            t.insert("end", "El programa es semánticamente válido. No se encontraron usos incompatibles de "
                            "identificadores, tipos, ámbitos, funciones o retornos.\n\n")
            t.insert("end", "Resumen semántico\n", "negrita")
            for clave, singular, plural in NOMBRES_SEMANTICOS:
                n = resumen.get(clave, 0)
                if n:
                    t.insert("end", f"   •  {n} {singular if n == 1 else plural}\n")
            t.config(state="disabled")

        if errores:
            n = len(errores)
            self.lbl_estado.config(text=("Léxico y sintaxis correctos · 1 error semántico" if n == 1 else
                                         f"Léxico y sintaxis correctos · {n} errores semánticos") + sufijo,
                                   fg="#c0392b")
        else:
            self.lbl_estado.config(text="Léxico correcto · sintaxis válida · semántica válida" + sufijo,
                                   fg="#2e7d32")
        self.notebook.select(self.tab_sem)
        return not errores

    # ------------------------------------------------------------------ léxico
    NOMBRES_AMIGABLES = {
        "PALABRA_RESERVADA": "reservadas", "IDENTIFICADOR": "identificadores",
        "NUMERO_ENTERO": "enteros", "NUMERO_DECIMAL": "decimales", "CADENA": "cadenas", "CARACTER": "caracteres",
        "OP_RELACIONAL": "op. relacionales", "OP_ASIGNACION": "asignaciones",
        "OP_ARITMETICO": "op. aritméticos", "OP_LOGICO": "op. lógicos", "OP_INCREMENTO": "incrementos", "ERROR_LEXICO": "errores léxicos",
    }

    def _actualizar_resumen(self, conteo, total):
        if total == 0:
            self.lbl_resumen.config(text="Sin tokens reconocidos.")
            return
        orden = ["PALABRA_RESERVADA", "IDENTIFICADOR", "NUMERO_ENTERO", "NUMERO_DECIMAL",
                 "CADENA", "CARACTER", "OP_RELACIONAL", "OP_ASIGNACION", "OP_ARITMETICO",
                 "OP_LOGICO", "OP_INCREMENTO", "ERROR_LEXICO"]
        partes = [f"{conteo[t]} {self.NOMBRES_AMIGABLES.get(t, t)}" for t in orden if t in conteo]
        self.lbl_resumen.config(text=f"Total: {total} tokens  ·  " + "  ·  ".join(partes))

    def _ir_a_linea_error(self, event):
        seleccion = self.lista_errores.curselection()
        if not seleccion or not self._lineas_error:
            return
        linea = self._lineas_error[seleccion[0]]
        self.editor.see(f"{linea}.0")
        self.editor.mark_set("insert", f"{linea}.0")
        self.editor.focus_set()
        self.editor.tag_remove("flash_error", "1.0", "end")
        self.editor.tag_add("flash_error", f"{linea}.0", f"{linea}.end")
        self.root.after(900, lambda: self.editor.tag_remove("flash_error", "1.0", "end"))

    def _actualizar_panel_errores(self, errores):
        self.lista_errores.delete(0, "end")
        self._lineas_error = []
        if not errores:
            self.marco_errores.pack_forget()
            return
        for linea, lexema in errores:
            self.lista_errores.insert("end", f"Línea {linea}: carácter no reconocido -> '{lexema}'")
            self._lineas_error.append(int(linea))
            self.editor.tag_add("linea_error", f"{linea}.0", f"{linea}.end")
        self.marco_errores.pack(fill="x", padx=16, pady=(0, 16), side="bottom")

    # ------------------------------------------------------------------ acciones
    def abrir_archivo(self):
        ruta = filedialog.askopenfilename(filetypes=[("Código mini-C", "*.txt *.c"), ("Archivos de texto", "*.txt"), ("Todos", "*.*")])
        if ruta:
            with open(ruta, "r", encoding="utf-8") as f:
                self.editor.delete("1.0", "end")
                self.editor.insert("1.0", f.read())
            self._redibujar_numeros()
            self._limpiar_traduccion()
            self.lbl_estado.config(text=f"Cargado: {os.path.basename(ruta)}", fg="#5a6572")

    def _limpiar_traduccion(self, mensaje="Traducción aún no ejecutada.", correcto=False):
        self.javascript = ""
        self.btn_guardar.config(state="disabled")
        self.btn_ejecutar.config(state="disabled")
        self.btn_copiar.config(state="disabled")
        self.btn_ver_errores.pack_forget()
        self._escribir_salida("")
        self.marco_salida.pack_forget()
        self.lbl_traduccion.config(text=mensaje, fg="#2e7d32" if correcto else "#5a6572")
        self.texto_js.config(state="normal", wrap="none")
        self.texto_js.delete("1.0", "end")
        self.texto_js.config(state="disabled")
        self._limpiar_simbolos_e_intermedio()

    def _limpiar_simbolos_e_intermedio(self):
        self.lbl_simbolos.config(text="Aún no se ha ejecutado el análisis.", fg="#5a6572")
        for fila in self.tabla_simbolos.get_children():
            self.tabla_simbolos.delete(fila)
        self._filas_simbolos = {}
        self.intermedio_texto = ""
        self.lbl_intermedio.config(text="Presione «Analizar código» para ver el código intermedio.", fg="#5a6572")
        self.texto_ir.config(state="normal")
        self.texto_ir.delete("1.0", "end")
        self.texto_ir.config(state="disabled")
        for fila in self.tabla_ir.get_children():
            self.tabla_ir.delete(fila)
        self.btn_guardar_ir.config(state="disabled")
        self.btn_copiar_ir.config(state="disabled")

    # ------------------------------------------------------------------ tabla de símbolos
    def _mostrar_simbolos(self, tabla, parcial=False):
        for fila in self.tabla_simbolos.get_children():
            self.tabla_simbolos.delete(fila)
        self._filas_simbolos = {}
        for s in tabla:
            iid = self.tabla_simbolos.insert(
                "", "end", tags=(s["clase"],),
                values=(s["nombre"], s["clase"], s["tipo"], s["ambito"], s["linea"], s.get("detalle", "")))
            self._filas_simbolos[iid] = s["linea"]
        n = len(tabla)
        if parcial:
            self.lbl_simbolos.config(text=f"Tabla incompleta ({n} símbolos): el análisis semántico encontró errores",
                                     fg="#c0392b")
        elif n == 0:
            self.lbl_simbolos.config(text="Tabla de símbolos vacía: el programa no declara nada", fg="#5a6572")
        else:
            self.lbl_simbolos.config(text=f"Tabla de símbolos generada ✓ ({n} símbolos)", fg="#2e7d32")

    def _ir_a_linea_simbolo(self, event):
        sel = self.tabla_simbolos.selection()
        if not sel or sel[0] not in self._filas_simbolos:
            return
        linea = self._filas_simbolos[sel[0]]
        self.editor.see(f"{linea}.0")
        self.editor.mark_set("insert", f"{linea}.0")
        self.editor.focus_set()
        self.editor.tag_remove("flash_error", "1.0", "end")
        self.editor.tag_add("flash_error", f"{linea}.0", f"{linea}.end")
        self.root.after(900, lambda: self.editor.tag_remove("flash_error", "1.0", "end"))

    # ------------------------------------------------------------------ código intermedio
    def _mostrar_intermedio(self, instrucciones, texto):
        self.intermedio_texto = texto
        self.texto_ir.config(state="normal")
        self.texto_ir.delete("1.0", "end")
        for linea in texto.splitlines():
            limpia = linea.strip()
            if linea.startswith("func ") or linea == "endfunc":
                etiqueta = "func"
            elif limpia.endswith(":") and not linea.startswith(" "):
                etiqueta = "etiqueta"
            elif limpia.startswith(("goto", "ifFalse", "ifTrue")):
                etiqueta = "salto"
            else:
                etiqueta = ""
            self.texto_ir.insert("end", linea + "\n", etiqueta)
        self.texto_ir.config(state="disabled")
        for fila in self.tabla_ir.get_children():
            self.tabla_ir.delete(fila)
        for n, ins in enumerate(instrucciones, 1):
            self.tabla_ir.insert("", "end", values=(n,) + ins.como_tupla())
        self.lbl_intermedio.config(text=f"Código intermedio generado ✓ ({len(instrucciones)} instrucciones)",
                                   fg="#2e7d32")
        self.btn_guardar_ir.config(state="normal")
        self.btn_copiar_ir.config(state="normal")

    def _mostrar_error_intermedio(self, mensaje):
        self.lbl_intermedio.config(text="No se pudo generar el código intermedio.", fg="#c0392b")
        self.texto_ir.config(state="normal")
        self.texto_ir.delete("1.0", "end")
        self.texto_ir.insert("1.0", mensaje, "error")
        self.texto_ir.config(state="disabled")

    def copiar_intermedio(self):
        if self.intermedio_texto:
            self.root.clipboard_clear()
            self.root.clipboard_append(self.intermedio_texto)
            self.lbl_estado.config(text="Código intermedio copiado al portapapeles", fg="#2e7d32")

    def guardar_intermedio(self):
        if not self.intermedio_texto:
            messagebox.showwarning("Sin código intermedio", "Primero analice un programa válido.")
            return
        ruta = filedialog.asksaveasfilename(title="Guardar código intermedio", defaultextension=".tac",
                                            filetypes=[("Código de tres direcciones", "*.tac"),
                                                       ("Texto", "*.txt"), ("Todos los archivos", "*.*")])
        if ruta:
            try:
                with open(ruta, "w", encoding="utf-8") as f:
                    f.write(self.intermedio_texto)
            except OSError as exc:
                messagebox.showerror("Error al guardar", str(exc))
                return
            self.lbl_estado.config(text=f"Código intermedio guardado: {os.path.basename(ruta)}", fg="#2e7d32")

    def _mostrar_traduccion(self, javascript):
        self.javascript = javascript
        self.texto_js.config(state="normal", wrap="none")
        self.texto_js.delete("1.0", "end")
        self.texto_js.insert("1.0", javascript)
        self.texto_js.config(state="disabled")
        self.lbl_traduccion.config(text="Traducción correcta ✓", fg="#2e7d32")
        self.btn_guardar.config(state="normal")
        self.btn_copiar.config(state="normal")
        self.btn_ejecutar.config(state="normal")
        self.notebook.select(self.tab_trad)

    # ------------------------------------------------------------------ traducción: acciones
    def _escribir_salida(self, texto, etiqueta=None):
        self.texto_salida.config(state="normal")
        self.texto_salida.delete("1.0", "end")
        if texto:
            self.texto_salida.insert("1.0", texto, etiqueta or "")
        self.texto_salida.config(state="disabled")

    def ejecutar_js(self):
        if not self.javascript:
            return
        if not self.marco_salida.winfo_ismapped():
            self.marco_salida.pack(side="bottom", fill="x", padx=9, pady=(0, 9), before=self.marco_js)
        if not node_disponible():
            self._escribir_salida(ejecutar_js(self.javascript).aviso, "error")
            return
        self._escribir_salida("Ejecutando...", "tenue")
        self.root.update_idletasks()
        res = ejecutar_js(self.javascript)
        self.texto_salida.config(state="normal")
        self.texto_salida.delete("1.0", "end")
        if res.aviso:
            self.texto_salida.insert("end", res.aviso, "error")
        else:
            self.texto_salida.insert("end", res.salida if res.salida else "(el programa no imprimió nada)\n",
                                     "" if res.salida else "tenue")
            if res.errores:
                self.texto_salida.insert("end", f"\n✗ Error de ejecución: {res.errores}\n", "error")
            self.texto_salida.insert("end", f"\n[terminó con código {res.codigo}]", "tenue")
        self.texto_salida.config(state="disabled")
        self.lbl_estado.config(text="Ejecución correcta" if res.correcto else "Ejecución con errores",
                               fg="#2e7d32" if res.correcto else "#c0392b")

    def copiar_js(self):
        if self.javascript:
            self.root.clipboard_clear()
            self.root.clipboard_append(self.javascript)
            self.lbl_estado.config(text="JavaScript copiado al portapapeles", fg="#2e7d32")

    def _ir_a_pestana_error(self):
        if self._pestana_error is not None:
            self.notebook.select(self._pestana_error)

    def _bloquear_traduccion(self, fase, filas, pestana, tab_destino, indice):
        """Muestra en la pestaña de traducción POR QUÉ no se tradujo.
        filas: lista de (línea, mensaje, sugerencia)."""
        n = len(filas)
        self.lbl_traduccion.config(
            text=(f"Traducción bloqueada: 1 error {fase[0]}" if n == 1
                  else f"Traducción bloqueada: {n} errores {fase[1]}"),
            fg="#c0392b")
        t = self.texto_js
        t.config(state="normal", wrap="word")
        t.delete("1.0", "end")
        t.insert("end", "No se generó JavaScript porque el programa tiene errores.\n\n", "titulo")
        for linea, mensaje, ayuda in filas[:8]:
            t.insert("end", f"Línea {linea}: {mensaje}\n")
            if ayuda:
                t.insert("end", f"   💡 {ayuda}\n", "ayuda")
            t.insert("end", "\n")
        if n > 8:
            t.insert("end", f"... y {n - 8} error(es) más en la pestaña «{pestana}».\n")
        t.config(state="disabled")
        self._pestana_error = tab_destino
        self.btn_ver_errores.config(text=f"Ver errores en {pestana} →")
        self.btn_ver_errores.pack(side="left")
        self._marcar_pestanas(**{indice: "error"})

    def _marcar_pestanas(self, lex=None, sint=None, sem=None, trad=None, sim=None, ir=None):
        """Agrega ✓ / ✗ / – a los títulos para ver de un vistazo qué fase falló.
        Si no se indican, «Símbolos» sigue a «Semántico» e «Intermedio» a «Traducción»."""
        sim = sim if sim is not None else (sem if sem in ("ok", "no") else None)
        ir = ir if ir is not None else (trad if trad in ("ok", "no") else None)
        estados = {"lex": lex, "sint": sint, "sem": sem, "trad": trad, "sim": sim, "ir": ir}
        tabs = {"lex": self.tab_lexico, "sint": self.tab_sint, "sem": self.tab_sem, "trad": self.tab_trad,
                "sim": self.tab_sim, "ir": self.tab_ir}
        for clave, estado in estados.items():
            self.notebook.tab(tabs[clave], text=TITULOS_PESTANAS[clave] + ICONOS[estado])

    def guardar_js(self):
        if not self.javascript:
            messagebox.showwarning("Sin traducción", "Primero analice y traduzca un programa válido.")
            return
        ruta = filedialog.asksaveasfilename(title="Guardar código JavaScript", defaultextension=".js",
                                            filetypes=[("JavaScript", "*.js"), ("Todos los archivos", "*.*")])
        if ruta:
            try:
                with open(ruta, "w", encoding="utf-8") as f:
                    f.write(self.javascript)
            except OSError as exc:
                messagebox.showerror("Error al guardar", str(exc))
                return
            self.lbl_estado.config(text=f"JS guardado: {os.path.basename(ruta)}", fg="#2e7d32")

    def limpiar(self):
        self.editor.delete("1.0", "end")
        self._limpiar_traduccion()
        self._limpiar_marcas()
        self._redibujar_numeros()
        self._actualizar_panel_errores([])
        self.lbl_resumen.config(text="")
        for fila in self.tabla.get_children():
            self.tabla.delete(fila)
        for p in (self.sem, self.sin):
            self._vaciar_tabla(p)
            self._poner_texto(p, "Aún no se ha ejecutado el análisis.", "#5a6572")
        self.lbl_estado.config(text="Listo", fg="#5a6572")
        self._marcar_pestanas()

    def _no_ejecutadas(self, motivo_sin, motivo_sem):
        self._vaciar_tabla(self.sin)
        self._vaciar_tabla(self.sem)
        self._poner_texto(self.sin, "Análisis sintáctico no ejecutado", "#c0392b", motivo_sin)
        self._poner_texto(self.sem, "Análisis semántico no ejecutado", "#c0392b", motivo_sem)

    def analizar(self):
        codigo = self.editor.get("1.0", "end-1c")
        self._limpiar_marcas()
        self._limpiar_traduccion()
        self._marcar_pestanas()

        try:
            resultado = procesar_codigo(codigo)
        except ErrorLexer as exc:
            messagebox.showerror("No se pudo ejecutar el analizador léxico", str(exc))
            self.lbl_estado.config(text="Error al ejecutar el analizador léxico", fg="#c0392b")
            return

        for fila in self.tabla.get_children():
            self.tabla.delete(fila)
        tokens = resultado.tokens
        conteo = {}
        for tipo, lexema, linea, columna in tokens:
            self.tabla.insert("", "end", values=(tipo, lexema, linea, columna), tags=(tipo,))
            conteo[tipo] = conteo.get(tipo, 0) + 1

        errores_lexicos = [(t[2], t[1]) for t in resultado.errores_lexicos]
        total = len(tokens)
        self._actualizar_panel_errores(errores_lexicos)
        self._actualizar_resumen(conteo, total)
        self.tabla.xview_moveto(0)

        if total == 0:
            self._no_ejecutadas("No hay código para analizar. Escriba o abra un programa y presione Analizar.",
                                "No hay código para analizar.")
            self.lbl_estado.config(text="Sin código para analizar", fg="#5a6572")
            return

        if errores_lexicos:
            self._no_ejecutadas("No se ejecutó la sintaxis debido a errores léxicos.",
                                "No se ejecutó la semántica debido a errores léxicos.")
            self._bloquear_traduccion(("léxico", "léxicos"),
                                      [(l, f"carácter no reconocido '{x}'", sugerencia_lexica(x))
                                       for l, x in errores_lexicos], "Léxico", self.tab_lexico, "lex")
            self._marcar_pestanas(lex="error", sint="no", sem="no", trad="no")
            self.notebook.select(self.tab_lexico)
            n = len(errores_lexicos)
            self.lbl_estado.config(text=f"{total} tokens · {n} error(es) léxico(s)", fg="#c0392b")
            return

        if resultado.errores_sintacticos:
            self._vaciar_tabla(self.sem)
            self._poner_texto(self.sem, "Análisis semántico no ejecutado", "#c0392b",
                              "La sintaxis tiene errores; corríjalos para continuar.")
            self._mostrar_errores_sintacticos(resultado.errores_sintacticos)
            self._bloquear_traduccion(("sintáctico", "sintácticos"),
                                      [(e.token.linea, e.mensaje, sugerencia(e.tipo, e.mensaje))
                                       for e in resultado.errores_sintacticos],
                                      "Sintáctico", self.tab_sint, "sint")
            self._marcar_pestanas(lex="ok", sint="error", sem="no", trad="no")
            self.notebook.select(self.tab_sint)
            self.lbl_estado.config(text="Léxico correcto · errores sintácticos", fg="#c0392b")
            return

        self._mostrar_exito_sintactico(resultado.resumen_sintactico, total,
                                      max(t[2] for t in tokens))
        semantica_ok = self._analizar_semantica(tokens, resultado.semantica)
        self._mostrar_simbolos(resultado.tabla_simbolos, parcial=not semantica_ok)
        if not semantica_ok:
            self._bloquear_traduccion(("semántico", "semánticos"),
                                      [(e.token.linea, e.mensaje, sugerencia(e.tipo, e.mensaje))
                                       for e in resultado.semantica["errores"]],
                                      "Semántico", self.tab_sem, "sem")
            self._marcar_pestanas(lex="ok", sint="ok", sem="error", trad="no")
            return
        if resultado.error_intermedio:
            self._mostrar_error_intermedio(resultado.error_intermedio)
        else:
            self._mostrar_intermedio(resultado.intermedio, resultado.intermedio_texto)
        estado_ir = "error" if resultado.error_intermedio else "ok"
        if resultado.error_traduccion:
            self.lbl_traduccion.config(text="No se pudo traducir esta estructura.", fg="#c0392b")
            self.texto_js.config(state="normal", wrap="word")
            self.texto_js.insert("1.0", resultado.error_traduccion)
            self.texto_js.config(state="disabled")
            posicion = posicion_error_traduccion(resultado.error_traduccion)
            if posicion:
                linea = posicion[0]
                self.editor.tag_add("linea_error", f"{linea}.0", f"{linea}.end")
                self.editor.see(f"{linea}.0")
            self._marcar_pestanas(lex="ok", sint="ok", sem="ok", trad="error", ir=estado_ir)
            self.notebook.select(self.tab_trad)
            self.lbl_estado.config(text="Fases 1–3 correctas · error de traducción", fg="#c0392b")
            return
        self._mostrar_traduccion(resultado.javascript)
        self._marcar_pestanas(lex="ok", sint="ok", sem="ok", trad="ok", ir=estado_ir)
        advertencias = len(resultado.semantica.get('advertencias', []))
        extras = f" · {advertencias} advertencia(s)" if advertencias else ""
        self.lbl_estado.config(text="Léxico ✓ · Sintaxis ✓ · Semántica ✓ · Intermedio ✓ · JavaScript ✓" + extras,
                               fg="#2e7d32")


if __name__ == "__main__":
    root = tk.Tk()
    app = AnalizadorCompiladorApp(root)
    root.mainloop()
