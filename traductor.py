"""Cuarta fase: traducción del mini-lenguaje tipo C a JavaScript.

Recibe los mismos tokens Flex/C que las fases previas, previamente validados.
Un parser descendente construye implícitamente la estructura del programa
mientras genera JavaScript; no utiliza sustituciones de texto plano.
"""
from dataclasses import dataclass


class ErrorTraduccion(Exception):
    """Error de una construcción que no se puede convertir de forma segura."""

    def __init__(self, mensaje, token=None):
        self.mensaje = mensaje
        self.token = token
        posicion = f"Línea {token.linea}, columna {token.columna}: " if token else ""
        super().__init__(posicion + mensaje)


# Precedencias para generar solo los paréntesis necesarios.
P_OR, P_AND, P_REL, P_ADD, P_MUL, P_UNARIO, P_ATOMO = 30, 40, 50, 70, 80, 90, 100


@dataclass
class Expr:
    codigo: str
    tipo: str
    prec: int = P_ATOMO


def _libre(e):
    """Código sin el paréntesis de envoltura `(a + b | 0)` cuando va solo (asignación, argumento, condición...)."""
    c = e.codigo
    if e.prec == P_ATOMO and c.startswith('(') and c.endswith(' | 0)'):
        return c[1:-1]
    return c


def _con(e, minimo):
    """Código de la expresión, entre paréntesis si su precedencia es menor a `minimo`."""
    return e.codigo if e.prec >= minimo else f'({e.codigo})'


# Evitar nombres con significado distinto en JS; mapearlos sin colisiones.
RESERVADOS_JS = set('''
    await break case catch class const continue debugger default delete do else
    enum export extends false finally for function if import in instanceof let new
    null return super switch this throw true try typeof var void while with yield
    implements interface package private protected public static arguments eval globalThis
    console Math undefined NaN Infinity
'''.split())


class TraductorJavaScript:
    """Parser-generador a partir de los tokens de un programa ya validado."""

    def __init__(self, tokens):
        self.tokens = [self._convertir_token(t) for t in tokens]
        self.pos = 0
        self.ambitos = [{}]
        self.funciones = {}
        self.nombres_js = {}
        self._preparar_nombres()
        self._preparar_funciones()
        self.main_llamado_explicitamente = False
        self.en_funcion = 0
        self.usa_division = False
        self.usa_modulo = False

    @staticmethod
    def _convertir_token(t):
        if isinstance(t, dict):
            return type('TokenJS', (), dict(tipo=t['tipo'], lexema=t['lexema'],
                                            linea=int(t['linea']), columna=int(t['columna'])))()
        if hasattr(t, 'lexema'):
            return t
        from sintactico import Token
        return Token(*t)

    def _preparar_nombres(self):
        nombres = {t.lexema for t in self.tokens if t.tipo == 'IDENTIFICADOR'}
        usados = set()
        for nombre in sorted(nombres):
            salida = nombre
            if salida in RESERVADOS_JS or salida.startswith('__mini_'):
                salida = '__ml_' + nombre
            while salida in nombres - {nombre} or salida in usados or salida in RESERVADOS_JS:
                salida = '_' + salida
            self.nombres_js[nombre] = salida
            usados.add(salida)

    def _preparar_funciones(self):
        # Coincide con la prelectura de firmas de la fase semántica, por lo que
        # admite llamadas a funciones definidas después de su uso.
        for i in range(len(self.tokens) - 2):
            a, b, c = self.tokens[i:i + 3]
            if a.lexema in ('int', 'float', 'double', 'char', 'bool', 'void') and b.tipo == 'IDENTIFICADOR' and c.lexema == '(':
                self.funciones[b.lexema] = a.lexema

    def actual(self):
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def siguiente(self):
        t = self.actual()
        if t:
            self.pos += 1
        return t

    def es(self, *lexemas):
        return self.actual() is not None and self.actual().lexema in lexemas

    def aceptar(self, *lexemas):
        if self.es(*lexemas):
            return self.siguiente()
        return None

    def exigir(self, lexema):
        t = self.aceptar(lexema)
        if t is None:
            raise ErrorTraduccion(f"se esperaba '{lexema}' (inconsistencia con el análisis sintáctico)", self.actual())
        return t

    def identificador(self):
        t = self.siguiente()
        if t is None or t.tipo != 'IDENTIFICADOR':
            raise ErrorTraduccion('se esperaba un identificador', t)
        return t

    def js(self, nombre):
        return self.nombres_js.get(nombre, nombre)

    @staticmethod
    def pad(n):
        return '    ' * n

    def abrir_ambito(self):
        self.ambitos.append({})

    def cerrar_ambito(self):
        self.ambitos.pop()

    def declarar(self, nombre, tipo):
        self.ambitos[-1][nombre] = tipo

    def tipo_de(self, nombre):
        for ambito in reversed(self.ambitos):
            if nombre in ambito:
                return ambito[nombre]
        raise ErrorTraduccion(f"variable '{nombre}' no reconocida por el traductor", self.actual())

    def traducir(self):
        lineas = []
        while self.actual() is not None:
            lineas.append(self.sentencia(0))
        if self.usa_modulo:
            lineas[0:0] = [
                'function __mini_mod(a, b) {',
                "    if (b === 0) { throw new Error('Módulo entre cero'); }",
                '    return a % b;',
                '}',
                '',
            ]
        if self.usa_division:
            lineas[0:0] = [
                'function __mini_div(a, b) {',
                "    if (b === 0) { throw new Error('División entre cero'); }",
                '    return (a / b) | 0;',
                '}',
                '',
            ]
        if 'main' in self.funciones and not self.main_llamado_explicitamente:
            lineas.extend(['', f'{self.js("main")}();'])
        return '\n'.join(lineas).rstrip() + '\n'

    def sentencia(self, n):
        t = self.actual()
        if t is None:
            raise ErrorTraduccion('sentencia incompleta')
        x = t.lexema
        if x in ('int', 'float', 'double', 'char', 'bool', 'void'):
            return self.declaracion_o_funcion(n)
        if x == '{':
            return self.bloque(n)
        if x == 'if':
            self.siguiente()
            self.exigir('(')
            condicion = _libre(self.expresion())
            self.exigir(')')
            cuerpo = self.cuerpo(n)
            salida = f'{self.pad(n)}if ({condicion}) {cuerpo}'
            if self.aceptar('else'):
                salida += f' else {self.cuerpo(n)}'
            return salida
        if x == 'while':
            self.siguiente()
            self.exigir('(')
            condicion = _libre(self.expresion())
            self.exigir(')')
            return f'{self.pad(n)}while ({condicion}) {self.cuerpo(n)}'
        if x == 'for':
            self.siguiente()
            self.exigir('(')
            self.abrir_ambito()
            try:
                if self.es('int', 'float', 'double', 'char', 'bool'):
                    tipo = self.siguiente().lexema
                    nombre = self.identificador().lexema
                    self.declarar(nombre, tipo)
                    inicio = f'let {self.js(nombre)}'
                    if self.aceptar('='):
                        inicio += ' = ' + _libre(self.expresion())
                elif not self.es(';'):
                    inicio = self.expresion_asignable()
                else:
                    inicio = ''
                self.exigir(';')
                condicion = '' if self.es(';') else _libre(self.expresion())
                self.exigir(';')
                paso = '' if self.es(')') else self.expresion_asignable()
                self.exigir(')')
                cuerpo = self.cuerpo(n)
                return f'{self.pad(n)}for ({inicio}; {condicion}; {paso}) {cuerpo}'
            finally:
                self.cerrar_ambito()
        if x == 'print':
            self.siguiente()
            self.exigir('(')
            argumentos = self.argumentos()
            self.exigir(')')
            self.exigir(';')
            return f'{self.pad(n)}console.log({", ".join(_libre(e) for e in argumentos)});'
        if x == 'return':
            self.siguiente()
            valor = '' if self.es(';') else ' ' + _libre(self.expresion())
            self.exigir(';')
            return f'{self.pad(n)}return{valor};'
        if x == ';':
            self.siguiente()
            return self.pad(n) + ';'
        if t.tipo == 'IDENTIFICADOR':
            nombre = self.identificador().lexema
            if self.aceptar('='):
                rhs = _libre(self.expresion())
                self.exigir(';')
                return f'{self.pad(n)}{self.js(nombre)} = {rhs};'
            if self.aceptar('++', '--'):
                operador = self.tokens[self.pos - 1].lexema
                self.exigir(';')
                return f'{self.pad(n)}{self.js(nombre)}{operador};'
            self.exigir('(')
            args = self.argumentos()
            self.exigir(')')
            self.exigir(';')
            if self.en_funcion == 0 and nombre == 'main':
                self.main_llamado_explicitamente = True
            return f'{self.pad(n)}{self.js(nombre)}({", ".join(_libre(a) for a in args)});'
        raise ErrorTraduccion(f"estructura '{x}' no soportada", t)

    def declaracion_o_funcion(self, n):
        tipo = self.siguiente().lexema
        nombre_token = self.identificador()
        nombre = nombre_token.lexema
        if self.aceptar('('):
            if len(self.ambitos) != 1:
                raise ErrorTraduccion('las funciones deben declararse en el nivel global', nombre_token)
            parametros = []
            if self.es('void') and self.pos + 1 < len(self.tokens) and self.tokens[self.pos + 1].lexema == ')':
                self.siguiente()
            elif not self.es(')'):
                while True:
                    parametro_tipo = self.siguiente().lexema
                    parametro = self.identificador().lexema
                    if parametro_tipo not in ('int', 'float', 'double', 'char', 'bool'):
                        raise ErrorTraduccion('tipo de parámetro no soportado', nombre_token)
                    parametros.append((parametro_tipo, parametro))
                    if not self.aceptar(','):
                        break
            self.exigir(')')
            self.abrir_ambito()
            try:
                for p_tipo, p_nombre in parametros:
                    self.declarar(p_nombre, p_tipo)
                self.en_funcion += 1
                try:
                    cuerpo = self.bloque(n, nuevo_ambito=False)
                finally:
                    self.en_funcion -= 1
            finally:
                self.cerrar_ambito()
            nombres = ', '.join(self.js(nom) for _, nom in parametros)
            return f'{self.pad(n)}function {self.js(nombre)}({nombres}) {cuerpo}'
        if tipo == 'void':
            raise ErrorTraduccion('void no puede utilizarse en una variable', nombre_token)
        declarados = []
        while True:
            if self.aceptar('['):
                if tipo != 'char':
                    raise ErrorTraduccion('solo se admiten arreglos de char', nombre_token)
                if not self.es(']'):
                    self.siguiente()  # tamaño, comprobado por el analizador semántico
                self.exigir(']')
                self.declarar(nombre, 'char[]')
                inicial = self.siguiente().lexema if self.aceptar('=') else '""'
            else:
                self.declarar(nombre, tipo)
                if self.aceptar('='):
                    inicial = _libre(self.expresion())
                elif len(self.ambitos) == 1:
                    inicial = {'char': "'\\0'", 'bool': 'false'}.get(tipo, '0')
                else:
                    inicial = None
            declarados.append(f'{self.pad(n)}let {self.js(nombre)}' +
                             (f' = {inicial}' if inicial is not None else '') + ';')
            if not self.aceptar(','):
                break
            nombre = self.identificador().lexema
        self.exigir(';')
        return '\n'.join(declarados)

    def bloque(self, n, nuevo_ambito=True):
        self.exigir('{')
        if nuevo_ambito:
            self.abrir_ambito()
        try:
            lineas = []
            while not self.es('}'):
                if self.actual() is None:
                    raise ErrorTraduccion('bloque sin cerrar')
                lineas.append(self.sentencia(n + 1))
            self.exigir('}')
            if not lineas:
                return '{}'
            return '{\n' + '\n'.join(lineas) + '\n' + self.pad(n) + '}'
        finally:
            if nuevo_ambito:
                self.cerrar_ambito()

    def cuerpo(self, n):
        if self.es('{'):
            return self.bloque(n)
        # Las declaraciones como sentencias sin llaves no son válidas en C estándar
        # y agregar llaves introduciría un ámbito distinto del original.
        if self.es('int', 'float', 'double', 'char', 'bool', 'void'):
            raise ErrorTraduccion('coloque llaves alrededor de una declaración usada como cuerpo de if/while/for', self.actual())
        return '{\n' + self.sentencia(n + 1) + '\n' + self.pad(n) + '}'

    def expresion_asignable(self):
        t = self.actual()
        if t and t.tipo == 'IDENTIFICADOR' and self.pos + 1 < len(self.tokens) and self.tokens[self.pos + 1].lexema in ('=', '++', '--'):
            nombre = self.siguiente().lexema
            if self.aceptar('++', '--'):
                operador = self.tokens[self.pos - 1].lexema
                return self.js(nombre) + operador
            self.exigir('=')
            return self.js(nombre) + ' = ' + _libre(self.expresion())
        return _libre(self.expresion())

    def expresion(self):
        return self.logico_o()

    def logico_o(self):
        izquierda = self.logico_y()
        while self.aceptar('||'):
            derecha = self.logico_y()
            izquierda = Expr(f'Boolean({_con(izquierda, P_OR)} || {_con(derecha, P_OR + 1)})', 'bool')
        return izquierda

    def logico_y(self):
        izquierda = self.relacional()
        while self.aceptar('&&'):
            derecha = self.relacional()
            izquierda = Expr(f'Boolean({_con(izquierda, P_AND)} && {_con(derecha, P_AND + 1)})', 'bool')
        return izquierda

    def relacional(self):
        izquierda = self.aditiva()
        if self.es('==', '!=', '<', '>', '<=', '>='):
            operador = self.siguiente().lexema
            derecha = self.aditiva()
            operador = {'==': '===', '!=': '!=='}.get(operador, operador)
            return Expr(f'{_con(izquierda, P_REL + 1)} {operador} {_con(derecha, P_REL + 1)}', 'bool', P_REL)
        return izquierda

    def aditiva(self):
        izquierda = self.multiplicativa()
        while self.es('+', '-'):
            op = self.siguiente().lexema
            derecha = self.multiplicativa()
            resultado_tipo = ('double' if 'double' in (izquierda.tipo, derecha.tipo) else
                              'float' if 'float' in (izquierda.tipo, derecha.tipo) else 'int')
            calculo = f'{_con(izquierda, P_ADD)} {op} {_con(derecha, P_ADD + 1)}'
            if resultado_tipo == 'int':
                # Los int de C son de 32 bits: `| 0` emula el desbordamiento.
                izquierda = Expr(f'({calculo} | 0)', 'int')
            else:
                izquierda = Expr(calculo, 'float', P_ADD)
        return izquierda

    def multiplicativa(self):
        izquierda = self.unaria()
        while self.es('*', '/', '%'):
            op = self.siguiente().lexema
            derecha = self.unaria()
            resultado_tipo = ('double' if 'double' in (izquierda.tipo, derecha.tipo) else
                              'float' if 'float' in (izquierda.tipo, derecha.tipo) else 'int')
            if resultado_tipo != 'int':
                izquierda = Expr(f'{_con(izquierda, P_MUL)} {op} {_con(derecha, P_MUL + 1)}', resultado_tipo, P_MUL)
            elif op == '%':
                self.usa_modulo = True
                izquierda = Expr(f'__mini_mod({_libre(izquierda)}, {_libre(derecha)})', 'int')
            elif op == '*':
                izquierda = Expr(f'Math.imul({_libre(izquierda)}, {_libre(derecha)})', 'int')
            elif derecha.codigo.isdigit() and int(derecha.codigo) != 0:
                # Divisor constante distinto de cero: no hace falta el auxiliar.
                izquierda = Expr(f'Math.trunc({_con(izquierda, P_MUL)} / {derecha.codigo})', 'int')
            else:
                self.usa_division = True
                izquierda = Expr(f'__mini_div({_libre(izquierda)}, {_libre(derecha)})', 'int')
        return izquierda

    def unaria(self):
        if self.es('+', '-', '!'):
            op = self.siguiente().lexema
            operand = self.unaria()
            interior = _con(operand, P_UNARIO)
            if op == '!':
                return Expr(f'!{interior}', 'bool', P_UNARIO)
            if interior.startswith(op):  # evita `--x` / `++x`
                interior = f'({interior})'
            return Expr(f'{op}{interior}', operand.tipo, P_UNARIO)
        return self.primaria()

    def primaria(self):
        t = self.siguiente()
        if t is None:
            raise ErrorTraduccion('expresión incompleta')
        if t.tipo == 'NUMERO_ENTERO':
            return Expr(str(int(t.lexema, 10)), 'int')
        if t.tipo == 'NUMERO_DECIMAL':
            return Expr(t.lexema, 'float')
        if t.tipo == 'CADENA':
            return Expr(t.lexema, 'string')
        if t.tipo == 'CARACTER':
            return Expr(t.lexema, 'char')
        if t.lexema in ('true', 'false'):
            return Expr(t.lexema, 'bool')
        if t.tipo == 'IDENTIFICADOR':
            if self.aceptar('('):
                argumentos = self.argumentos()
                self.exigir(')')
                return Expr(f'{self.js(t.lexema)}({", ".join(_libre(arg) for arg in argumentos)})',
                            self.funciones.get(t.lexema, 'error'))
            codigo = self.js(t.lexema)
            tipo = self.tipo_de(t.lexema)
            if self.aceptar('['):
                indice = self.expresion()
                self.exigir(']')
                return Expr(f'{codigo}[{_libre(indice)}]', 'char')
            return Expr(codigo, tipo)
        if t.lexema == '(':
            expresion = self.expresion()
            self.exigir(')')
            return expresion  # los paréntesis se regeneran solo cuando hacen falta
        raise ErrorTraduccion('expresión no soportada', t)

    def argumentos(self):
        args = []
        if not self.es(')'):
            args.append(self.expresion())
            while self.aceptar(','):
                args.append(self.expresion())
        return args


def traducir_tokens(tokens):
    """Genera código JavaScript. El llamador debe validar léxico/sintaxis/semántica."""
    return TraductorJavaScript(tokens).traducir()
