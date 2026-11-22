"""sintactico.py - Analizador sintactico descendente recursivo con recuperacion de errores.

Recibe los tokens producidos por el analizador lexico Flex. Cada token debe tener:
    tipo, lexema, linea, columna

El parser no reemplaza al lexer: es la segunda fase y trabaja sobre su salida.
Cuando encuentra un error lo registra, se "sincroniza" (salta hasta un punto seguro)
y sigue analizando, de modo que puede reportar varios errores en una sola pasada.
"""

import difflib
from dataclasses import dataclass


@dataclass
class Token:
    tipo: str
    lexema: str
    linea: int
    columna: int


class ErrorSintactico(Exception):
    def __init__(self, mensaje, token=None, tipo="Error de sintaxis"):
        self.mensaje = mensaje
        self.token = token
        self.tipo = tipo
        super().__init__(mensaje)

    def __str__(self):
        if self.token is None:
            return self.mensaje
        return f"Linea {self.token.linea}: {self.mensaje}"


class AnalizadorSintactico:
    """Parser LL sencillo (descendente recursivo) para el mini lenguaje."""

    TIPOS = {"int", "float", "double", "char", "bool", "void"}
    TIPOS_PARAM = TIPOS - {"void"}
    PALABRAS = ["if", "else", "while", "for", "int", "float", "double", "char", "bool", "return", "void", "print"]
    INICIO_SENTENCIA = TIPOS | {"if", "while", "for", "print", "return"}

    def __init__(self, tokens):
        self.tokens = [self._normalizar_token(t) for t in tokens]
        self.pos = 0
        self.errores = []
        self.resumen = {}

    @staticmethod
    def _normalizar_token(t):
        if isinstance(t, Token):
            return t
        if isinstance(t, dict):
            return Token(t["tipo"], t["lexema"], int(t["linea"]), int(t["columna"]))
        tipo, lexema, linea, columna = t
        return Token(tipo, lexema, int(linea), int(columna))

    # -------------------- utilidades --------------------
    def _contar(self, clave):
        """Cuenta una estructura reconocida (se muestra en el resumen si no hay errores)."""
        self.resumen[clave] = self.resumen.get(clave, 0) + 1

    def actual(self):
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def anterior(self):
        return self.tokens[self.pos - 1] if self.pos > 0 else None

    def fin(self):
        return self.pos >= len(self.tokens)

    def avanzar(self):
        tok = self.actual()
        if not self.fin():
            self.pos += 1
        return tok

    def coincide_lexema(self, *lexemas):
        tok = self.actual()
        return tok is not None and tok.lexema in lexemas

    def coincide_tipo(self, *tipos):
        tok = self.actual()
        return tok is not None and tok.tipo in tipos

    def aceptar_lexema(self, *lexemas):
        if self.coincide_lexema(*lexemas):
            return self.avanzar()
        return None

    def _ubicar_falta(self, tok_actual):
        """Si el token encontrado esta en una linea posterior al ultimo token
        consumido, el simbolo faltante pertenece al final de la linea anterior.
        Se devuelve un token 'FALTA' (lexema vacio) justo despues del ultimo token."""
        prev = self.anterior()
        if prev is not None and (tok_actual is None or tok_actual.linea > prev.linea):
            return Token("FALTA", "", prev.linea, prev.columna + len(prev.lexema))
        return tok_actual or prev

    def exigir_lexema(self, lexema, contexto=None):
        if self.coincide_lexema(lexema):
            return self.avanzar()
        actual = self.actual()
        tok = self._ubicar_falta(actual)
        extra = f" {contexto}" if contexto else ""
        if tok is not actual:  # el simbolo realmente falta (no hay nada en su lugar)
            tipo = "Bloque sin cerrar" if lexema == "}" else "Símbolo faltante"
            raise ErrorSintactico(f"falta '{lexema}'{extra}", tok, tipo)
        raise ErrorSintactico(
            f"token inesperado '{actual.lexema}'; se esperaba '{lexema}'{extra}",
            tok, "Token inesperado")

    def exigir_tipo(self, tipo, descripcion=None):
        if self.coincide_tipo(tipo):
            return self.avanzar()
        actual = self.actual()
        tok = self._ubicar_falta(actual)
        esperado = descripcion or tipo
        if tok is not actual:
            raise ErrorSintactico(f"falta {esperado}", tok, "Identificador esperado")
        raise ErrorSintactico(
            f"se esperaba {esperado}, pero se encontró '{actual.lexema}'",
            tok, "Identificador esperado")

    # -------------------- entrada principal --------------------
    def analizar(self):
        """Analiza todo el programa. Devuelve la lista de errores (vacia si es correcto)."""
        self.errores = []
        self.resumen = {}
        self.pos = 0

        lexicos = [t for t in self.tokens if t.tipo == "ERROR_LEXICO"]
        if lexicos:
            self.errores.append(ErrorSintactico(
                "no se puede iniciar el análisis sintáctico mientras existan errores léxicos",
                lexicos[0], "Error léxico previo"))
            return self.errores

        while not self.fin():
            self._sentencia_segura()
        return self.errores

    # -------------------- recuperacion de errores --------------------
    def _registrar(self, error):
        clave = (error.token.linea, error.token.columna, error.mensaje) if error.token else None
        if clave is not None and any(
                e.token and (e.token.linea, e.token.columna, e.mensaje) == clave for e in self.errores):
            return
        self.errores.append(error)

    def _sentencia_segura(self):
        """Analiza una sentencia; si falla, registra el error y se sincroniza."""
        inicio = self.pos
        try:
            self.sentencia()
        except ErrorSintactico as e:
            self._registrar(e)
            self._sincronizar(inicio)

    def _sincronizar(self, inicio):
        """Modo panico: descarta tokens hasta un punto seguro donde pueda empezar
        una nueva sentencia (despues de ';', al cerrar un bloque, ante una palabra
        clave de inicio de sentencia, o ante un '}' del bloque que nos contiene)."""
        profundidad = 0
        forzar = (self.pos == inicio)  # garantiza que siempre se avance al menos un token
        while not self.fin():
            tok = self.actual()
            prev = self.anterior()
            if not forzar and profundidad == 0:
                if tok.lexema == "}" or tok.lexema in self.INICIO_SENTENCIA:
                    return
                if tok.tipo == "IDENTIFICADOR" and prev is not None and tok.linea > prev.linea:
                    return
            forzar = False
            self.avanzar()
            if tok.lexema == "{":
                profundidad += 1
            elif tok.lexema == "}" and profundidad > 0:
                profundidad -= 1
                if profundidad == 0 and not self.coincide_lexema("else"):
                    return
            elif tok.lexema == ";" and profundidad == 0:
                return

    def _saltar_hasta_cierre(self, con_punto_coma=False):
        """Tras un error dentro de la cabecera de if/while/for: salta hasta el ')' que
        la cierra (lo consume) o hasta el inicio del cuerpo, para poder seguir con el cuerpo."""
        paradas = ("{", "}") if con_punto_coma else ("{", "}", ";")
        prof = 0
        while not self.fin():
            lex = self.actual().lexema
            if lex in paradas:
                return
            if lex == "(":
                prof += 1
            elif lex == ")":
                if prof == 0:
                    self.avanzar()
                    return
                prof -= 1
            self.avanzar()

    # -------------------- sentencias --------------------
    def sentencia(self):
        tok = self.actual()
        if tok is None:
            return

        if tok.lexema in self.TIPOS:
            self.declaracion_o_funcion()
        elif tok.lexema == "if":
            self.sentencia_if()
        elif tok.lexema == "while":
            self.sentencia_while()
        elif tok.lexema == "for":
            self.sentencia_for()
        elif tok.lexema == "print":
            self.sentencia_print()
        elif tok.lexema == "return":
            self.sentencia_return()
        elif tok.lexema == "{":
            self.bloque()
        elif tok.lexema == ";":
            self.avanzar()  # sentencia vacia
        elif tok.lexema == "else":
            raise ErrorSintactico("'else' sin un 'if' previo", tok, "Estructura inválida")
        elif tok.lexema == "}":
            raise ErrorSintactico("'}' sin su '{' correspondiente", tok, "Llave sin abrir")
        elif tok.tipo == "IDENTIFICADOR":
            self.sentencia_identificador()
        else:
            raise ErrorSintactico(f"inicio de sentencia no válido: '{tok.lexema}'", tok, "Sentencia no válida")

    def bloque_o_sentencia(self):
        if self.coincide_lexema("{"):
            self.bloque()
        else:
            self.sentencia()

    def bloque(self):
        abre = self.exigir_lexema("{", "al iniciar el bloque")
        while not self.fin() and not self.coincide_lexema("}"):
            self._sentencia_segura()
        if not self.coincide_lexema("}"):
            raise ErrorSintactico(
                f"falta '}}' para cerrar el bloque abierto en la línea {abre.linea}",
                self._ubicar_falta(None), "Bloque sin cerrar")
        self.avanzar()

    def declaracion_o_funcion(self):
        tipo = self.avanzar()  # int / float / void
        nombre = self.exigir_tipo("IDENTIFICADOR", "un identificador después del tipo")

        # Funcion: tipo nombre(parametros) { ... }
        if self.aceptar_lexema("("):
            self.parametros()
            self.exigir_lexema(")", "después de los parámetros")
            if not self.coincide_lexema("{"):
                tok = self._ubicar_falta(self.actual()) or nombre
                raise ErrorSintactico("se esperaba un bloque '{ ... }' para el cuerpo de la función",
                                      tok, "Bloque esperado")
            self.bloque()
            self._contar("funciones")
            return

        if tipo.lexema == "void":
            raise ErrorSintactico("'void' solo puede usarse como tipo de retorno de una función",
                                  tipo, "Declaración inválida")

        self.resto_declaracion(tipo.lexema)
        while self.aceptar_lexema(","):
            self.exigir_tipo("IDENTIFICADOR", "un identificador después de ','")
            self.resto_declaracion(tipo.lexema)
        self.exigir_lexema(";", "al final de la declaración")
        self._contar("declaraciones")

    def resto_declaracion(self, tipo):
        if self.aceptar_lexema("["):
            if tipo != "char":
                raise ErrorSintactico("solo se admiten arreglos de char para texto", self.anterior(), "Arreglo no soportado")
            if not self.coincide_lexema("]"):
                self.exigir_tipo("NUMERO_ENTERO", "tamaño entero del arreglo")
            self.exigir_lexema("]", "para cerrar el arreglo")
            if self.aceptar_lexema("="):
                self.exigir_tipo("CADENA", "una cadena para inicializar el arreglo de char")
            return
        if self.aceptar_lexema("="):
            self.expresion()

    def parametros(self):
        if self.coincide_lexema(")"):
            return
        # Permite main(void)
        if self.coincide_lexema("void"):
            self.avanzar()
            if self.coincide_lexema(")"):
                return
            self.exigir_tipo("IDENTIFICADOR", "un nombre de parámetro")
        else:
            if not self.actual() or self.actual().lexema not in self.TIPOS_PARAM:
                tok = self._ubicar_falta(self.actual())
                raise ErrorSintactico("se esperaba un tipo de parámetro (int, float, double, char o bool)", tok, "Parámetro inválido")
            self.avanzar()
            self.exigir_tipo("IDENTIFICADOR", "un nombre de parámetro")

        while self.aceptar_lexema(","):
            tok = self.actual()
            if tok is None or tok.lexema not in self.TIPOS_PARAM:
                raise ErrorSintactico("se esperaba un tipo de parámetro después de ','",
                                      self._ubicar_falta(tok), "Parámetro inválido")
            self.avanzar()
            self.exigir_tipo("IDENTIFICADOR", "un nombre de parámetro")

    def sentencia_if(self):
        self.exigir_lexema("if")
        self._contar("condicionales")
        try:
            self.exigir_lexema("(", "después de 'if'")
            self.expresion()
            self.exigir_lexema(")", "para cerrar la condición de 'if'")
        except ErrorSintactico as e:
            self._registrar(e)
            self._saltar_hasta_cierre()
        self.bloque_o_sentencia()
        if self.aceptar_lexema("else"):
            self.bloque_o_sentencia()

    def sentencia_while(self):
        self.exigir_lexema("while")
        self._contar("ciclos_while")
        try:
            self.exigir_lexema("(", "después de 'while'")
            self.expresion()
            self.exigir_lexema(")", "para cerrar la condición de 'while'")
        except ErrorSintactico as e:
            self._registrar(e)
            self._saltar_hasta_cierre()
        self.bloque_o_sentencia()

    def sentencia_for(self):
        self.exigir_lexema("for")
        self._contar("ciclos_for")
        try:
            self.exigir_lexema("(", "después de 'for'")

            # inicializacion
            if self.coincide_lexema(*self.TIPOS_PARAM):
                self.avanzar()
                self.exigir_tipo("IDENTIFICADOR", "un identificador en la inicialización del for")
                if self.aceptar_lexema("="):
                    self.expresion()
            elif not self.coincide_lexema(";"):
                self.expresion_asignable()
            self.exigir_lexema(";", "en la primera parte del 'for'")

            # condicion
            if not self.coincide_lexema(";"):
                self.expresion()
            self.exigir_lexema(";", "en la segunda parte del 'for'")

            # incremento/asignacion
            if not self.coincide_lexema(")"):
                self.expresion_asignable()
            self.exigir_lexema(")", "para cerrar el 'for'")
        except ErrorSintactico as e:
            self._registrar(e)
            self._saltar_hasta_cierre(con_punto_coma=True)
        self.bloque_o_sentencia()

    def sentencia_print(self):
        self.exigir_lexema("print")
        self._contar("prints")
        self.exigir_lexema("(", "después de 'print'")
        if not self.coincide_lexema(")"):
            self.expresion()
            while self.aceptar_lexema(","):
                self.expresion()
        self.exigir_lexema(")", "después del contenido de 'print'")
        self.exigir_lexema(";", "al final de 'print'")

    def sentencia_return(self):
        self.exigir_lexema("return")
        self._contar("returns")
        if not self.coincide_lexema(";"):
            self.expresion()
        self.exigir_lexema(";", "al final de 'return'")

    def _sugerir_palabra(self, lexema):
        """Si el identificador se parece a una palabra reservada, la devuelve."""
        for p in self.PALABRAS:
            if p != lexema and sorted(p) == sorted(lexema):
                return p
        cercanas = difflib.get_close_matches(lexema, self.PALABRAS, n=1, cutoff=0.75)
        return cercanas[0] if cercanas else None

    def _error_palabra_mal_escrita(self, identificador):
        sug = self._sugerir_palabra(identificador.lexema)
        if sug:
            raise ErrorSintactico(
                f"'{identificador.lexema}' no es una palabra reservada válida. ¿Quiso decir '{sug}'?",
                identificador, "Palabra reservada mal escrita")

    def sentencia_identificador(self):
        identificador = self.avanzar()
        if self.aceptar_lexema("="):
            self.expresion()
            self.exigir_lexema(";", "al final de la asignación")
            self._contar("asignaciones")
            return
        if self.aceptar_lexema("("):
            self.argumentos()
            self.exigir_lexema(")", "después de los argumentos")
            if not self.coincide_lexema(";"):
                sug = self._sugerir_palabra(identificador.lexema)
                if sug:
                    # Se registra el error pero se sigue con el cuerpo, para no ocultar
                    # los errores que haya dentro del bloque.
                    self._registrar(ErrorSintactico(
                        f"'{identificador.lexema}' no es una palabra reservada válida. ¿Quiso decir '{sug}'?",
                        identificador, "Palabra reservada mal escrita"))
                    if self.coincide_lexema("{"):
                        self.bloque()
                        if sug == "if" and self.aceptar_lexema("else"):
                            self.bloque_o_sentencia()
                    return
            self.exigir_lexema(";", "al final de la llamada a función")
            self._contar("llamadas")
            return
        if self.aceptar_lexema("++", "--"):
            self.exigir_lexema(";", "después del incremento/decremento")
            self._contar("incrementos")
            return
        self._error_palabra_mal_escrita(identificador)
        raise ErrorSintactico(
            f"después del identificador '{identificador.lexema}' se esperaba '=', '++', '--' o '('",
            self._ubicar_falta(self.actual()) or identificador, "Sentencia no válida")

    def expresion_asignable(self):
        # En las partes del for permitimos i = expresion o una expresion normal.
        if self.coincide_tipo("IDENTIFICADOR") and self.pos + 1 < len(self.tokens) and self.tokens[self.pos + 1].lexema in ("=", "++", "--"):
            self.avanzar()
            operador = self.avanzar()
            if operador.lexema == "=":
                self.expresion()
        else:
            self.expresion()

    # -------------------- expresiones --------------------
    def expresion(self):
        self.logico_o()

    def logico_o(self):
        self.logico_y()
        while self.aceptar_lexema("||"):
            self.logico_y()

    def logico_y(self):
        self.relacional()
        while self.aceptar_lexema("&&"):
            self.relacional()

    def relacional(self):
        self.aditiva()
        if self.coincide_lexema("==", "!=", "<", ">", "<=", ">="):
            self.avanzar()
            self.aditiva()

    def aditiva(self):
        self.multiplicativa()
        while self.coincide_lexema("+", "-"):
            self.avanzar()
            self.multiplicativa()

    def multiplicativa(self):
        self.unaria()
        while self.coincide_lexema("*", "/", "%"):
            self.avanzar()
            self.unaria()

    def unaria(self):
        if self.coincide_lexema("+", "-", "!"):
            self.avanzar()
            self.unaria()
        else:
            self.primaria()

    def primaria(self):
        tok = self.actual()
        if tok is None:
            raise ErrorSintactico("se esperaba una expresión, pero se alcanzó el fin del archivo",
                                  self.anterior(), "Expresión incompleta")

        if tok.tipo in {"NUMERO_ENTERO", "NUMERO_DECIMAL", "CADENA", "CARACTER"} or tok.lexema in {"true", "false"}:
            self.avanzar()
            return

        if tok.tipo == "IDENTIFICADOR":
            self.avanzar()
            if self.aceptar_lexema("("):
                self.argumentos()
                self.exigir_lexema(")", "después de los argumentos")
            elif self.aceptar_lexema("["):
                self.expresion()
                self.exigir_lexema("]", "después del índice")
            return

        if self.aceptar_lexema("("):
            self.expresion()
            self.exigir_lexema(")", "para cerrar la expresión")
            return

        raise ErrorSintactico(f"se esperaba una expresión válida, pero se encontró '{tok.lexema}'",
                              self._ubicar_falta(tok), "Expresión incompleta")

    def argumentos(self):
        if self.coincide_lexema(")"):
            return
        self.expresion()
        while self.aceptar_lexema(","):
            self.expresion()


def analizar_programa(tokens):
    """Devuelve (errores, resumen). 'resumen' cuenta las estructuras reconocidas."""
    parser = AnalizadorSintactico(tokens)
    errores = parser.analizar()
    return errores, parser.resumen


def analizar_tokens_completo(tokens):
    """Devuelve la lista de errores sintacticos (vacia si el programa es correcto)."""
    return AnalizadorSintactico(tokens).analizar()


def analizar_tokens(tokens):
    """Version anterior: lanza el primer error. Se conserva por compatibilidad."""
    errores = AnalizadorSintactico(tokens).analizar()
    if errores:
        raise errores[0]
    return True
