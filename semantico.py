"""semantico.py - Analizador semantico para el mini lenguaje tipo C.

Tercera fase del compilador. Recibe los tokens del lexer DESPUES de que el
analizador sintactico haya validado la estructura del programa.

Comprobaciones principales:
- identificadores declarados antes de usarse;
- redeclaraciones dentro del mismo ambito;
- compatibilidad de tipos en inicializaciones y asignaciones;
- tipos de operandos en expresiones aritmeticas y relacionales;
- existencia de funciones, cantidad y tipos de argumentos;
- tipos y presencia de return segun el tipo de la funcion;
- ambitos de bloques, funciones y variables declaradas en for;
- (fase 3b) retorno en TODOS los caminos, division entre cero, uso de variables
  locales sin valor (advertencia) y tabla de simbolos completa.
"""

from dataclasses import dataclass


@dataclass
class Token:
    tipo: str
    lexema: str
    linea: int
    columna: int


@dataclass
class Simbolo:
    nombre: str
    tipo: str
    clase: str          # variable | parametro | funcion
    token: Token
    parametros: tuple = ()
    inicializado: bool = True   # solo se usa para advertencias de variables locales
    local: bool = False


class ErrorSemantico:
    def __init__(self, mensaje, token, tipo="Error semantico"):
        self.mensaje = mensaje
        self.token = token
        self.tipo = tipo

    def __str__(self):
        if self.token is None:
            return self.mensaje
        return f"Linea {self.token.linea}: {self.mensaje}"


class AnalizadorSemantico:
    TIPOS_NUMERICOS = {"int", "float", "double"}
    TIPOS = TIPOS_NUMERICOS | {"char", "bool"}

    def __init__(self, tokens):
        self.tokens = [self._normalizar_token(t) for t in tokens]
        self.pos = 0
        self.errores = []
        self.ambitos = [{}]  # ambito global + pila de ambitos locales
        self.nombres_ambito = ["global"]
        self.tabla = []          # tabla de simbolos (historial completo)
        self.advertencias = []
        self.funciones = {}
        self.funcion_actual = None
        self.resumen = {
            "variables": 0,
            "funciones": 0,
            "parametros": 0,
            "asignaciones": 0,
            "llamadas": 0,
            "retornos": 0,
        }

    @staticmethod
    def _normalizar_token(t):
        if isinstance(t, Token):
            return t
        if isinstance(t, dict):
            return Token(t["tipo"], t["lexema"], int(t["linea"]), int(t["columna"]))
        tipo, lexema, linea, columna = t
        return Token(tipo, lexema, int(linea), int(columna))

    # ---------- utilidades ----------
    def actual(self):
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def mirar(self, n=1):
        i = self.pos + n
        return self.tokens[i] if i < len(self.tokens) else None

    def fin(self):
        return self.pos >= len(self.tokens)

    def avanzar(self):
        tok = self.actual()
        if tok is not None:
            self.pos += 1
        return tok

    def es(self, *lexemas):
        return self.actual() is not None and self.actual().lexema in lexemas

    def aceptar(self, *lexemas):
        if self.es(*lexemas):
            return self.avanzar()
        return None

    def exigir(self, lexema):
        # La sintaxis ya fue validada. Esto es solo para recorrer con seguridad.
        if self.es(lexema):
            return self.avanzar()
        tok = self.actual() or (self.tokens[-1] if self.tokens else None)
        self._error(f"no se pudo continuar el analisis semantico: se esperaba '{lexema}'", tok,
                    "Inconsistencia sintactica")
        return tok

    def _error(self, mensaje, token, tipo="Error semantico"):
        if token is None:
            return
        clave = (token.linea, token.columna, tipo, mensaje)
        if not any((e.token.linea, e.token.columna, e.tipo, e.mensaje) == clave for e in self.errores):
            self.errores.append(ErrorSemantico(mensaje, token, tipo))

    def _advertencia(self, mensaje, token, tipo="Advertencia"):
        if token is None:
            return
        clave = (token.linea, token.columna, mensaje)
        if not any((e.token.linea, e.token.columna, e.mensaje) == clave for e in self.advertencias):
            self.advertencias.append(ErrorSemantico(mensaje, token, tipo))

    def abrir_ambito(self, nombre="bloque"):
        self.ambitos.append({})
        self.nombres_ambito.append(nombre)

    def cerrar_ambito(self):
        if len(self.ambitos) > 1:
            self.ambitos.pop()
            self.nombres_ambito.pop()

    def declarar(self, nombre_tok, tipo, clase="variable", parametros=()):
        ambito = self.ambitos[-1]
        if nombre_tok.lexema in ambito:
            anterior = ambito[nombre_tok.lexema]
            self._error(
                f"'{nombre_tok.lexema}' ya fue declarado en este ambito (declaracion anterior en linea {anterior.token.linea})",
                nombre_tok, "Identificador duplicado")
            return anterior
        simbolo = Simbolo(nombre_tok.lexema, tipo, clase, nombre_tok, tuple(parametros),
                          inicializado=(clase != "variable"), local=len(self.ambitos) > 1)
        ambito[nombre_tok.lexema] = simbolo
        self._registrar_en_tabla(simbolo, self.nombres_ambito[-1])
        if clase == "variable":
            self.resumen["variables"] += 1
        elif clase == "parametro":
            self.resumen["parametros"] += 1
        return simbolo

    def _registrar_en_tabla(self, sim, ambito):
        detalle = ""
        if sim.clase == "funcion":
            detalle = "(" + (", ".join(sim.parametros) if sim.parametros else "void") + ")"
        self.tabla.append({"nombre": sim.nombre, "tipo": sim.tipo, "clase": sim.clase,
                           "ambito": ambito, "linea": sim.token.linea,
                           "columna": sim.token.columna, "detalle": detalle})

    def buscar(self, nombre):
        for ambito in reversed(self.ambitos):
            if nombre in ambito:
                return ambito[nombre]
        return None

    @staticmethod
    def compatible(destino, origen):
        if destino == origen:
            return True
        # Conversión ascendente: int -> float/double y float -> double.
        # 'string' solo puede inicializar un char[], nunca una variable char.
        return (destino == "float" and origen == "int") or (destino == "double" and origen in {"int", "float"})

    @staticmethod
    def combinar_numericos(a, b):
        if a == "error" or b == "error":
            return "error"
        if a not in {"int", "float", "double"} or b not in {"int", "float", "double"}:
            return None
        if "double" in (a, b):
            return "double"
        return "float" if "float" in (a, b) else "int"

    # ---------- prelectura de firmas ----------
    def _registrar_firmas_funciones(self):
        """Registra funciones antes del recorrido principal para permitir llamadas
        a funciones definidas mas adelante en el archivo."""
        i = 0
        n = len(self.tokens)
        while i + 2 < n:
            t0, t1, t2 = self.tokens[i:i+3]
            if t0.lexema in self.TIPOS | {"void"} and t1.tipo == "IDENTIFICADOR" and t2.lexema == "(":
                j = i + 3
                params = []
                valido = True
                if j < n and self.tokens[j].lexema == "void" and j + 1 < n and self.tokens[j+1].lexema == ")":
                    j += 1
                elif j < n and self.tokens[j].lexema != ")":
                    while j < n:
                        if self.tokens[j].lexema not in self.TIPOS:
                            valido = False; break
                        p_tipo = self.tokens[j].lexema; j += 1
                        if j >= n or self.tokens[j].tipo != "IDENTIFICADOR":
                            valido = False; break
                        params.append((p_tipo, self.tokens[j])); j += 1
                        if j < n and self.tokens[j].lexema == ",":
                            j += 1; continue
                        break
                if valido and j < n and self.tokens[j].lexema == ")":
                    if t1.lexema in self.funciones:
                        ant = self.funciones[t1.lexema]
                        self._error(f"la funcion '{t1.lexema}' ya fue definida en la linea {ant.token.linea}",
                                    t1, "Funcion duplicada")
                    else:
                        sim = Simbolo(t1.lexema, t0.lexema, "funcion", t1,
                                      tuple(p for p, _ in params))
                        self.funciones[t1.lexema] = sim
                        self.ambitos[0][t1.lexema] = sim
                        self._registrar_en_tabla(sim, "global")
                        self.resumen["funciones"] += 1
            i += 1

    # ---------- entrada ----------
    def analizar(self):
        self.pos = 0
        self.errores = []
        self.ambitos = [{}]
        self.nombres_ambito = ["global"]
        self.tabla = []
        self.advertencias = []
        self.funciones = {}
        self.funcion_actual = None
        self.resumen = {"variables": 0, "funciones": 0, "parametros": 0,
                        "asignaciones": 0, "llamadas": 0, "retornos": 0}
        self._registrar_firmas_funciones()
        self.pos = 0
        while not self.fin():
            self.sentencia()
        self.tabla.sort(key=lambda r: (r["linea"], r["columna"]))
        return self.errores

    # ---------- sentencias ----------
    def sentencia(self):
        """Analiza una sentencia. Devuelve True si la sentencia GARANTIZA que la
        ejecucion termina en un 'return' (se usa para validar el retorno de funciones)."""
        tok = self.actual()
        if tok is None:
            return False
        if tok.lexema in self.TIPOS | {"void"}:
            self.declaracion_o_funcion()
        elif tok.lexema == "if":
            return self.sentencia_if()
        elif tok.lexema == "while":
            self.sentencia_while()
        elif tok.lexema == "for":
            self.sentencia_for()
        elif tok.lexema == "print":
            self.sentencia_print()
        elif tok.lexema == "return":
            self.sentencia_return()
            return True
        elif tok.lexema == "{":
            return self.bloque(nuevo_ambito=True)
        elif tok.lexema == ";":
            self.avanzar()
        elif tok.tipo == "IDENTIFICADOR":
            self.sentencia_identificador()
        else:
            # En un programa sintacticamente valido no deberia ocurrir.
            self.avanzar()
        return False

    def declaracion_o_funcion(self):
        tipo_tok = self.avanzar()
        nombre = self.avanzar()
        if self.aceptar("("):
            # La firma ya fue registrada en prelectura.
            funcion = self.funciones.get(nombre.lexema)
            params = []
            if self.es("void") and self.mirar() and self.mirar().lexema == ")":
                self.avanzar()
            elif not self.es(")"):
                while True:
                    p_tipo = self.avanzar()
                    p_nombre = self.avanzar()
                    params.append((p_tipo.lexema, p_nombre))
                    if not self.aceptar(","):
                        break
            self.exigir(")")
            anterior_funcion = self.funcion_actual
            self.funcion_actual = funcion or Simbolo(nombre.lexema, tipo_tok.lexema, "funcion", nombre,
                                                     tuple(p for p, _ in params))
            self.exigir("{")
            self.abrir_ambito(f"funcion {nombre.lexema}")
            for p_tipo, p_nombre in params:
                self.declarar(p_nombre, p_tipo, "parametro")
            garantiza_retorno = False
            while not self.fin() and not self.es("}"):
                if self.sentencia():
                    garantiza_retorno = True
            self.exigir("}")
            self.cerrar_ambito()
            if self.funcion_actual.tipo != "void" and not garantiza_retorno:
                self._error(f"la funcion '{self.funcion_actual.nombre}' debe retornar un valor de tipo "
                            f"{self.funcion_actual.tipo} en todos los caminos de ejecucion",
                            nombre, "Retorno faltante")
            self.funcion_actual = anterior_funcion
            return

        if tipo_tok.lexema == "void":
            # La sintaxis ya evita esta declaracion; se ignora defensivamente.
            while not self.fin() and not self.aceptar(";"):
                self.avanzar()
            return

        self._declarar_variable(nombre, tipo_tok.lexema)
        while self.aceptar(","):
            otro = self.avanzar()
            self._declarar_variable(otro, tipo_tok.lexema)
        self.exigir(";")

    def _declarar_variable(self, nombre, tipo):
        if self.aceptar("["):
            # Arreglos de char: cadena terminada en NUL, sin cambios de tamaño.
            tamanio = None
            if not self.es("]"):
                tamanio_tok = self.avanzar()
                tamanio = int(tamanio_tok.lexema)
                if tamanio <= 0:
                    self._error("el arreglo debe tener un tamaño mayor que cero", tamanio_tok,
                                "Tamaño de arreglo inválido")
            self.exigir("]")
            sim = self.declarar(nombre, "char[]", "variable")
            if self.aceptar("="):
                literal = self.avanzar()
                # La longitud literal descuenta las comillas y reserva un byte NUL.
                import ast
                try:
                    longitud = len(ast.literal_eval(literal.lexema))
                except (SyntaxError, ValueError):
                    longitud = len(literal.lexema) - 2
                if tamanio is not None and longitud >= tamanio:
                    self._error(f"la cadena no cabe en el arreglo '{nombre.lexema}' (requiere {longitud + 1} posiciones con NUL)",
                                nombre, "Tamaño de arreglo insuficiente")
                sim.inicializado = True
            elif tamanio is None:
                self._error("char[] requiere tamaño o inicialización con una cadena", nombre,
                            "Tamaño de arreglo faltante")
            return
        sim = self.declarar(nombre, tipo, "variable")
        if self.aceptar("="):
            tipo_expr = self.expresion()
            sim.inicializado = True
            if tipo_expr != "error" and not self.compatible(tipo, tipo_expr):
                self._error(
                    f"no se puede inicializar '{nombre.lexema}' de tipo {tipo} con una expresion de tipo {tipo_expr}",
                    nombre, "Tipos incompatibles")

    def bloque(self, nuevo_ambito=True):
        llave = self.exigir("{")
        if nuevo_ambito:
            self.abrir_ambito(f"bloque (linea {llave.linea})")
        garantiza = False
        while not self.fin() and not self.es("}"):
            if self.sentencia():
                garantiza = True
        self.exigir("}")
        if nuevo_ambito:
            self.cerrar_ambito()
        return garantiza

    def sentencia_if(self):
        self.avanzar(); self.exigir("(")
        cond_tok = self.actual()
        tipo = self.expresion()
        self._validar_condicion(tipo, cond_tok, "if")
        self.exigir(")")
        rama_then = self.sentencia_con_ambito()
        if self.aceptar("else"):
            rama_else = self.sentencia_con_ambito()
            return rama_then and rama_else
        return False

    def sentencia_while(self):
        self.avanzar(); self.exigir("(")
        cond_tok = self.actual()
        tipo = self.expresion()
        self._validar_condicion(tipo, cond_tok, "while")
        self.exigir(")")
        self.sentencia_con_ambito()

    def sentencia_for(self):
        for_tok = self.avanzar(); self.exigir("(")
        self.abrir_ambito(f"for (linea {for_tok.linea})")
        if self.es(*self.TIPOS):
            tipo = self.avanzar().lexema
            nombre = self.avanzar()
            self._declarar_variable(nombre, tipo)
        elif not self.es(";"):
            self.expresion_asignable()
        self.exigir(";")
        if not self.es(";"):
            cond_tok = self.actual()
            tipo_cond = self.expresion()
            self._validar_condicion(tipo_cond, cond_tok, "for")
        self.exigir(";")
        if not self.es(")"):
            self.expresion_asignable()
        self.exigir(")")
        self.sentencia_con_ambito()
        self.cerrar_ambito()

    def sentencia_con_ambito(self):
        if self.es("{"):
            return self.bloque(nuevo_ambito=True)
        # Una sola sentencia no crea ambito adicional en C.
        return self.sentencia()

    def sentencia_print(self):
        self.avanzar(); self.exigir("(")
        if not self.es(")"):
            self.expresion()
            while self.aceptar(","):
                self.expresion()
        self.exigir(")"); self.exigir(";")

    def sentencia_return(self):
        ret_tok = self.avanzar()
        self.resumen["retornos"] += 1
        tiene_expr = not self.es(";")
        tipo_expr = self.expresion() if tiene_expr else None
        self.exigir(";")
        if self.funcion_actual is None:
            self._error("'return' solo puede utilizarse dentro de una funcion", ret_tok,
                        "Return fuera de funcion")
            return
        esperado = self.funcion_actual.tipo
        if esperado == "void" and tiene_expr:
            self._error(f"la funcion '{self.funcion_actual.nombre}' es void y no debe retornar un valor",
                        ret_tok, "Retorno incompatible")
        elif esperado != "void" and not tiene_expr:
            self._error(f"la funcion '{self.funcion_actual.nombre}' debe retornar un valor de tipo {esperado}",
                        ret_tok, "Retorno faltante")
        elif esperado != "void" and tipo_expr != "error" and not self.compatible(esperado, tipo_expr):
            self._error(f"la funcion '{self.funcion_actual.nombre}' retorna {tipo_expr}, pero su tipo declarado es {esperado}",
                        ret_tok, "Retorno incompatible")

    def sentencia_identificador(self):
        ident = self.avanzar()
        if self.aceptar("="):
            self.resumen["asignaciones"] += 1
            simbolo = self.buscar(ident.lexema)
            if simbolo is None or simbolo.clase == "funcion":
                self._error(f"la variable '{ident.lexema}' no ha sido declarada en este ambito",
                            ident, "Variable no declarada")
                destino = "error"
            else:
                destino = simbolo.tipo
            origen = self.expresion()
            if simbolo is not None:
                simbolo.inicializado = True
            if destino != "error" and origen != "error" and not self.compatible(destino, origen):
                self._error(f"no se puede asignar una expresion de tipo {origen} a '{ident.lexema}' de tipo {destino}",
                            ident, "Tipos incompatibles")
            self.exigir(";")
            return
        if self.aceptar("("):
            args = self.argumentos()
            self.exigir(")"); self.exigir(";")
            self._validar_llamada(ident, args)   # ya cuenta la llamada en el resumen
            return
        if self.aceptar("++", "--"):
            sim = self.buscar(ident.lexema)
            if sim is None or sim.clase == "funcion":
                self._error(f"la variable '{ident.lexema}' no ha sido declarada en este ambito",
                            ident, "Variable no declarada")
            elif sim.tipo not in self.TIPOS_NUMERICOS:
                self._error(f"++/-- requiere variable numerica, no {sim.tipo}", ident, "Operacion incompatible")
            else:
                sim.inicializado = True
            self.exigir(";")
            return

    def expresion_asignable(self):
        if self.actual() and self.actual().tipo == "IDENTIFICADOR" and self.mirar() and self.mirar().lexema in {"=", "++", "--"}:
            ident = self.avanzar(); operador = self.avanzar().lexema
            simbolo = self.buscar(ident.lexema)
            if simbolo is None or simbolo.clase == "funcion":
                self._error(f"la variable '{ident.lexema}' no ha sido declarada en este ambito",
                            ident, "Variable no declarada")
                destino = "error"
            else:
                destino = simbolo.tipo
            if operador == "=":
                origen = self.expresion()
                if destino != "error" and origen != "error" and not self.compatible(destino, origen):
                    self._error(f"no se puede asignar una expresion de tipo {origen} a '{ident.lexema}' de tipo {destino}",
                                ident, "Tipos incompatibles")
            elif destino != "error" and destino not in self.TIPOS_NUMERICOS:
                self._error(f"++/-- requiere variable numerica, no {destino}", ident, "Operacion incompatible")
            if simbolo is not None:
                simbolo.inicializado = True
        else:
            self.expresion()

    # ---------- expresiones y tipos ----------
    def expresion(self):
        return self.logico_o()

    def logico_o(self):
        tipo = self.logico_y()
        while self.es("||"):
            op = self.avanzar()
            otro = self.logico_y()
            for t in (tipo, otro):
                if t not in self.TIPOS_NUMERICOS | {"bool", "error"}:
                    self._error(f"el operador '||' requiere booleanos o numeros, no {t}", op,
                                "Operacion incompatible")
            tipo = "bool"
        return tipo

    def logico_y(self):
        tipo = self.relacional()
        while self.es("&&"):
            op = self.avanzar()
            otro = self.relacional()
            for t in (tipo, otro):
                if t not in self.TIPOS_NUMERICOS | {"bool", "error"}:
                    self._error(f"el operador '&&' requiere booleanos o numeros, no {t}", op,
                                "Operacion incompatible")
            tipo = "bool"
        return tipo

    def relacional(self):
        izq = self.aditiva()
        if self.es("==", "!=", "<", ">", "<=", ">="):
            op = self.avanzar()
            der = self.aditiva()
            if izq != "error" and der != "error":
                if op.lexema in {"<", ">", "<=", ">="}:
                    if izq not in self.TIPOS_NUMERICOS or der not in self.TIPOS_NUMERICOS:
                        self._error(f"el operador '{op.lexema}' requiere operandos numericos, no {izq} y {der}",
                                    op, "Operacion incompatible")
                elif izq != der and not ({izq, der} <= self.TIPOS_NUMERICOS):
                    self._error(f"no se pueden comparar valores de tipo {izq} y {der}",
                                op, "Comparacion incompatible")
            return "bool"
        return izq

    def aditiva(self):
        tipo = self.multiplicativa()
        while self.es("+", "-"):
            op = self.avanzar()
            der = self.multiplicativa()
            combinado = self.combinar_numericos(tipo, der)
            if combinado is None:
                self._error(f"el operador '{op.lexema}' requiere operandos numericos, no {tipo} y {der}",
                            op, "Operacion incompatible")
                tipo = "error"
            else:
                tipo = combinado
        return tipo

    def multiplicativa(self):
        tipo = self.unaria()
        while self.es("*", "/", "%"):
            op = self.avanzar()
            sig = self.actual()
            if (op.lexema in {"/", "%"} and sig is not None
                    and sig.tipo in {"NUMERO_ENTERO", "NUMERO_DECIMAL"} and float(sig.lexema) == 0):
                self._error("division entre cero (el divisor es la constante 0)", sig, "Division entre cero")
            der = self.unaria()
            combinado = self.combinar_numericos(tipo, der)
            if op.lexema == "%" and (tipo != "int" or der != "int"):
                self._error("el operador '%' requiere dos enteros (int)", op, "Operacion incompatible")
                tipo = "error"
            elif combinado is None:
                self._error(f"el operador '{op.lexema}' requiere operandos numericos, no {tipo} y {der}",
                            op, "Operacion incompatible")
                tipo = "error"
            else:
                tipo = combinado
        return tipo

    def unaria(self):
        if self.es("+", "-", "!"):
            op = self.avanzar()
            tipo = self.unaria()
            if op.lexema == "!":
                if tipo not in self.TIPOS_NUMERICOS | {"bool", "error"}:
                    self._error(f"el operador '!' requiere un valor numerico o booleano, no {tipo}", op,
                                "Operacion incompatible")
                    return "error"
                return "bool"
            if tipo not in self.TIPOS_NUMERICOS and tipo != "error":
                self._error(f"el operador unario '{op.lexema}' requiere un valor numerico, no {tipo}",
                            op, "Operacion incompatible")
                return "error"
            return tipo
        return self.primaria()

    def primaria(self):
        tok = self.actual()
        if tok is None:
            return "error"
        if tok.tipo == "NUMERO_ENTERO":
            self.avanzar(); return "int"
        if tok.tipo == "NUMERO_DECIMAL":
            self.avanzar(); return "float"
        if tok.tipo == "CADENA":
            self.avanzar(); return "string"
        if tok.tipo == "CARACTER":
            self.avanzar(); return "char"
        if tok.lexema in ("true", "false"):
            self.avanzar(); return "bool"
        if tok.tipo == "IDENTIFICADOR":
            ident = self.avanzar()
            if self.aceptar("("):
                args = self.argumentos()
                self.exigir(")")
                return self._validar_llamada(ident, args)
            indice = None
            if self.aceptar("["):
                indice = self.expresion()
                self.exigir("]")
            sim = self.buscar(ident.lexema)
            if sim is None or sim.clase == "funcion":
                self._error(f"la variable '{ident.lexema}' no ha sido declarada en este ambito",
                            ident, "Variable no declarada")
                return "error"
            if sim.clase == "variable" and sim.local and not sim.inicializado:
                self._advertencia(f"la variable local '{ident.lexema}' se usa sin haberle asignado un valor antes",
                                  ident, "Variable sin inicializar")
            if indice is not None:
                if sim.tipo != "char[]":
                    self._error(f"'{ident.lexema}' no es un arreglo de char", ident,
                                "Indice incompatible")
                    return "error"
                if indice != "int" and indice != "error":
                    self._error("el indice de un arreglo debe ser int", ident, "Indice incompatible")
                return "char"
            return sim.tipo
        if self.aceptar("("):
            tipo = self.expresion(); self.exigir(")"); return tipo
        self.avanzar()
        return "error"

    def argumentos(self):
        tipos = []
        if self.es(")"):
            return tipos
        tipos.append(self.expresion())
        while self.aceptar(","):
            tipos.append(self.expresion())
        return tipos

    def _validar_llamada(self, ident, argumentos):
        fun = self.funciones.get(ident.lexema)
        if fun is None:
            self._error(f"la funcion '{ident.lexema}' no ha sido definida",
                        ident, "Funcion no declarada")
            return "error"
        self.resumen["llamadas"] += 1
        esperados = list(fun.parametros)
        if len(argumentos) != len(esperados):
            self._error(f"la funcion '{ident.lexema}' espera {len(esperados)} argumento(s), pero se recibieron {len(argumentos)}",
                        ident, "Cantidad de argumentos incorrecta")
        else:
            for i, (esp, rec) in enumerate(zip(esperados, argumentos), 1):
                if rec != "error" and not self.compatible(esp, rec):
                    self._error(f"argumento {i} de '{ident.lexema}': se esperaba {esp}, pero se obtuvo {rec}",
                                ident, "Tipo de argumento incompatible")
        return fun.tipo

    def _validar_condicion(self, tipo, tok, estructura):
        # En este mini lenguaje se aceptan expresiones relacionales (bool) o numericas,
        # como en C. Cadenas no son condiciones validas.
        if tipo not in self.TIPOS_NUMERICOS | {"bool", "error"}:
            self._error(f"la condicion de '{estructura}' debe ser numerica o relacional, no de tipo {tipo}",
                        tok, "Condicion incompatible")


def analizar_semantica(tokens):
    analizador = AnalizadorSemantico(tokens)
    errores = analizador.analizar()
    return errores, analizador.resumen


def analizar_semantica_completo(tokens):
    """Version ampliada: devuelve un diccionario con errores, advertencias,
    resumen y la tabla de simbolos completa."""
    a = AnalizadorSemantico(tokens)
    errores = a.analizar()
    return {"errores": errores, "advertencias": a.advertencias,
            "resumen": a.resumen, "tabla": a.tabla}
