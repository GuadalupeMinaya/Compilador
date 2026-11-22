"""Generador de código intermedio: código de tres direcciones (cuádruplas).

Se ejecuta después del análisis semántico y antes de la traducción a JavaScript.
Recibe los mismos tokens ya validados que el resto de las fases y produce una
lista de instrucciones (operador, argumento 1, argumento 2, resultado).

Convenciones del código generado:
  - Cada instrucción tiene como máximo un operador y tres direcciones.
  - Los valores intermedios se guardan en temporales (t1, t2, ...).
  - El control de flujo usa etiquetas (L1, L2, ...), `goto`, `ifFalse` e `ifTrue`.
  - Las conversiones implícitas int -> float/double se hacen explícitas.
  - `&&` y `||` se traducen con saltos (cortocircuito).
"""
import re
from dataclasses import dataclass
from typing import Optional

TIPOS = ('int', 'float', 'double', 'char', 'bool', 'void')
TIPOS_REALES = ('float', 'double')

OPS_BINARIOS = ('+', '-', '*', '/', '%', '<', '>', '<=', '>=', '==', '!=')


class ErrorIntermedio(Exception):
    """Construcción que no se puede convertir de forma segura."""

    def __init__(self, mensaje, token=None):
        self.mensaje = mensaje
        self.token = token
        posicion = f"Línea {token.linea}, columna {token.columna}: " if token else ""
        super().__init__(posicion + mensaje)


@dataclass
class Cuadrupla:
    """Una instrucción de tres direcciones."""
    op: str
    arg1: Optional[str] = None
    arg2: Optional[str] = None
    res: Optional[str] = None

    def texto(self):
        op, a, b, r = self.op, self.arg1, self.arg2, self.res
        if op == 'label':
            return f'{r}:'
        if op == 'func':
            return f'func {r}({a or ""}):'
        if op == 'endfunc':
            return 'endfunc'
        if op == '=':
            return f'{r} = {a}'
        if op in OPS_BINARIOS:
            return f'{r} = {a} {op} {b}'
        if op == 'minus':
            return f'{r} = -{a}'
        if op == '!':
            return f'{r} = !{a}'
        if op == 'itof':
            return f'{r} = (float) {a}'
        if op == '[]':
            return f'{r} = {a}[{b}]'
        if op == 'goto':
            return f'goto {r}'
        if op == 'iffalse':
            return f'ifFalse {a} goto {r}'
        if op == 'iftrue':
            return f'ifTrue {a} goto {r}'
        if op == 'param':
            return f'param {a}'
        if op == 'call':
            llamada = f'call {a}, {b}'
            return f'{r} = {llamada}' if r else llamada
        if op == 'return':
            return f'return {a}' if a is not None else 'return'
        if op == 'print':
            return f'print {a}'
        raise ValueError(f'operador desconocido: {op}')

    def como_tupla(self):
        """(operador, arg1, arg2, resultado) para mostrar en tabla."""
        def v(x):
            return '' if x is None else str(x)
        op = {'iffalse': 'ifFalse', 'iftrue': 'ifTrue', 'minus': 'neg', 'itof': '(float)'}.get(self.op, self.op)
        if self.op == 'func':
            op = 'func'
        return (op, v(self.arg1), v(self.arg2), v(self.res))


@dataclass
class Operando:
    valor: str
    tipo: str


def _es_literal_entero(texto):
    return re.fullmatch(r'-?\d+', texto) is not None


class GeneradorIntermedio:
    def __init__(self, tokens):
        self.tokens = [self._convertir_token(t) for t in tokens]
        self.pos = 0
        self.codigo = []
        self.ambitos = [{}]          # nombre -> (nombre en el código, tipo)
        self.funciones = {}          # nombre -> (tipo de retorno, [tipos de parámetros])
        self.n_temp = 0
        self.n_etiqueta = 0
        self.tipo_retorno = None
        self.en_funcion = 0
        self.main_llamado_explicitamente = False
        identificadores = {t.lexema for t in self.tokens if t.tipo == 'IDENTIFICADOR'}
        self.prefijo_temp = self._prefijo_libre('t', identificadores)
        self.prefijo_etiq = self._prefijo_libre('L', identificadores)
        self._preparar_funciones()

    # ------------------------------------------------------------ utilidades
    @staticmethod
    def _convertir_token(t):
        if isinstance(t, dict):
            return type('TokenIR', (), dict(tipo=t['tipo'], lexema=t['lexema'],
                                            linea=int(t['linea']), columna=int(t['columna'])))()
        if hasattr(t, 'lexema'):
            return t
        from sintactico import Token
        return Token(*t)

    @staticmethod
    def _prefijo_libre(base, identificadores):
        """Evita que un temporal o etiqueta choque con un identificador del usuario."""
        prefijo = base
        while any(re.fullmatch(re.escape(prefijo) + r'\d+', i) for i in identificadores):
            prefijo = '_' + prefijo
        return prefijo

    def _preparar_funciones(self):
        """Prelectura de firmas: permite llamar a funciones definidas más abajo."""
        i, n = 0, len(self.tokens)
        while i < n - 2:
            a, b, c = self.tokens[i:i + 3]
            if a.lexema in TIPOS and b.tipo == 'IDENTIFICADOR' and c.lexema == '(':
                j = i + 3
                tipos = []
                if (j + 1 < n and self.tokens[j].lexema == 'void' and self.tokens[j + 1].lexema == ')'):
                    j += 1
                else:
                    while j < n and self.tokens[j].lexema != ')':
                        if self.tokens[j].lexema in TIPOS:
                            tipos.append(self.tokens[j].lexema)
                        j += 1
                self.funciones[b.lexema] = (a.lexema, tipos)
                i = j
            i += 1

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
            raise ErrorIntermedio(f"se esperaba '{lexema}' (inconsistencia con el análisis sintáctico)",
                                  self.actual())
        return t

    def identificador(self):
        t = self.siguiente()
        if t is None or t.tipo != 'IDENTIFICADOR':
            raise ErrorIntermedio('se esperaba un identificador', t)
        return t

    def emitir(self, op, arg1=None, arg2=None, res=None):
        self.codigo.append(Cuadrupla(op, arg1, arg2, res))

    def nuevo_temp(self):
        self.n_temp += 1
        return f'{self.prefijo_temp}{self.n_temp}'

    def nueva_etiqueta(self):
        self.n_etiqueta += 1
        return f'{self.prefijo_etiq}{self.n_etiqueta}'

    # ------------------------------------------------------------ ámbitos
    def abrir_ambito(self):
        self.ambitos.append({})

    def cerrar_ambito(self):
        self.ambitos.pop()

    def declarar(self, nombre, tipo):
        """Registra la variable; si oculta a otra visible, usa un nombre distinto en el código."""
        interno = nombre
        visibles = {v[0] for ambito in self.ambitos for v in ambito.values()}
        k = 0
        while interno in visibles:
            k += 1
            interno = f'{nombre}_{k}'
        self.ambitos[-1][nombre] = (interno, tipo)
        return interno

    def buscar(self, nombre):
        for ambito in reversed(self.ambitos):
            if nombre in ambito:
                return ambito[nombre]
        raise ErrorIntermedio(f"variable '{nombre}' no reconocida", self.actual())

    @staticmethod
    def _tipo_resultado(a, b):
        if 'double' in (a, b):
            return 'double'
        if 'float' in (a, b):
            return 'float'
        return 'int'

    def convertir(self, op, destino):
        """Conversión implícita int -> float/double hecha explícita."""
        if destino in TIPOS_REALES and op.tipo == 'int':
            if _es_literal_entero(op.valor):
                return Operando(op.valor + '.0', destino)
            t = self.nuevo_temp()
            self.emitir('itof', op.valor, None, t)
            return Operando(t, destino)
        return op

    # ------------------------------------------------------------ programa
    def generar(self):
        while self.actual() is not None:
            self.sentencia()
        if 'main' in self.funciones and not self.main_llamado_explicitamente:
            self.emitir('call', 'main', '0')
        return self.codigo

    # ------------------------------------------------------------ sentencias
    def sentencia(self):
        t = self.actual()
        if t is None:
            raise ErrorIntermedio('sentencia incompleta')
        x = t.lexema
        if x in TIPOS:
            return self.declaracion_o_funcion()
        if x == '{':
            return self.bloque()
        if x == 'if':
            self.siguiente()
            self.exigir('(')
            cond = self.expresion()
            self.exigir(')')
            falso = self.nueva_etiqueta()
            self.emitir('iffalse', cond.valor, None, falso)
            self.cuerpo()
            if self.aceptar('else'):
                fin = self.nueva_etiqueta()
                self.emitir('goto', res=fin)
                self.emitir('label', res=falso)
                self.cuerpo()
                self.emitir('label', res=fin)
            else:
                self.emitir('label', res=falso)
            return
        if x == 'while':
            self.siguiente()
            self.exigir('(')
            inicio, fin = self.nueva_etiqueta(), self.nueva_etiqueta()
            self.emitir('label', res=inicio)
            cond = self.expresion()
            self.exigir(')')
            self.emitir('iffalse', cond.valor, None, fin)
            self.cuerpo()
            self.emitir('goto', res=inicio)
            self.emitir('label', res=fin)
            return
        if x == 'for':
            return self.sentencia_for()
        if x == 'print':
            self.siguiente()
            self.exigir('(')
            args = self.argumentos()
            self.exigir(')')
            self.exigir(';')
            self.emitir('print', ', '.join(a.valor for a in args))
            return
        if x == 'return':
            self.siguiente()
            if self.es(';'):
                self.siguiente()
                self.emitir('return')
                return
            valor = self.expresion()
            self.exigir(';')
            if self.tipo_retorno:
                valor = self.convertir(valor, self.tipo_retorno)
            self.emitir('return', valor.valor)
            return
        if x == ';':
            self.siguiente()
            return
        if t.tipo == 'IDENTIFICADOR':
            return self.sentencia_simple()
        raise ErrorIntermedio(f"estructura '{x}' no soportada", t)

    def sentencia_simple(self, esperar_punto_coma=True):
        """Asignación, incremento/decremento o llamada como sentencia."""
        nombre = self.identificador().lexema
        if self.aceptar('='):
            interno, tipo = self.buscar(nombre)
            valor = self.convertir(self.expresion(), tipo)
            self.emitir('=', valor.valor, None, interno)
        elif self.aceptar('++', '--'):
            op = '+' if self.tokens[self.pos - 1].lexema == '++' else '-'
            interno, _tipo = self.buscar(nombre)
            t = self.nuevo_temp()
            self.emitir(op, interno, '1', t)
            self.emitir('=', t, None, interno)
        else:
            self.exigir('(')
            args = self.argumentos()
            self.exigir(')')
            self.llamada(nombre, args, con_resultado=False)
            if self.en_funcion == 0 and nombre == 'main':
                self.main_llamado_explicitamente = True
        if esperar_punto_coma:
            self.exigir(';')

    def sentencia_for(self):
        self.siguiente()
        self.exigir('(')
        self.abrir_ambito()
        try:
            if self.es('int', 'float', 'double', 'char', 'bool'):
                tipo = self.siguiente().lexema
                nombre = self.identificador().lexema
                interno = self.declarar(nombre, tipo)
                if self.aceptar('='):
                    valor = self.convertir(self.expresion(), tipo)
                    self.emitir('=', valor.valor, None, interno)
            elif not self.es(';'):
                self.parte_for()
            self.exigir(';')
            inicio, fin = self.nueva_etiqueta(), self.nueva_etiqueta()
            self.emitir('label', res=inicio)
            if not self.es(';'):
                cond = self.expresion()
                self.emitir('iffalse', cond.valor, None, fin)
            self.exigir(';')
            # El paso se escribe antes del cuerpo pero se ejecuta después: se guarda aparte.
            principal = self.codigo
            self.codigo = []
            if not self.es(')'):
                self.parte_for()
            paso = self.codigo
            self.codigo = principal
            self.exigir(')')
            self.cuerpo()
            self.codigo.extend(paso)
            self.emitir('goto', res=inicio)
            self.emitir('label', res=fin)
        finally:
            self.cerrar_ambito()

    def parte_for(self):
        t = self.actual()
        sig = self.tokens[self.pos + 1] if self.pos + 1 < len(self.tokens) else None
        if t.tipo == 'IDENTIFICADOR' and sig is not None and sig.lexema in ('=', '++', '--'):
            self.sentencia_simple(esperar_punto_coma=False)
        else:
            self.expresion()

    def declaracion_o_funcion(self):
        tipo = self.siguiente().lexema
        nombre_token = self.identificador()
        nombre = nombre_token.lexema
        if self.aceptar('('):
            if len(self.ambitos) != 1:
                raise ErrorIntermedio('las funciones deben declararse en el nivel global', nombre_token)
            parametros = []
            if self.es('void') and self.pos + 1 < len(self.tokens) and self.tokens[self.pos + 1].lexema == ')':
                self.siguiente()
            elif not self.es(')'):
                while True:
                    p_tipo = self.siguiente().lexema
                    p_nombre = self.identificador().lexema
                    if p_tipo not in ('int', 'float', 'double', 'char', 'bool'):
                        raise ErrorIntermedio('tipo de parámetro no soportado', nombre_token)
                    parametros.append((p_tipo, p_nombre))
                    if not self.aceptar(','):
                        break
            self.exigir(')')
            self.abrir_ambito()
            anterior = self.tipo_retorno
            try:
                internos = [self.declarar(p_nombre, p_tipo) for p_tipo, p_nombre in parametros]
                self.tipo_retorno = tipo
                self.emitir('func', ', '.join(internos), None, nombre)
                self.en_funcion += 1
                try:
                    self.bloque(nuevo_ambito=False)
                finally:
                    self.en_funcion -= 1
                self.emitir('endfunc')
            finally:
                self.tipo_retorno = anterior
                self.cerrar_ambito()
            return
        if tipo == 'void':
            raise ErrorIntermedio('void no puede utilizarse en una variable', nombre_token)
        while True:
            if self.aceptar('['):
                if tipo != 'char':
                    raise ErrorIntermedio('solo se admiten arreglos de char', nombre_token)
                if not self.es(']'):
                    self.siguiente()  # tamaño, verificado por el análisis semántico
                self.exigir(']')
                interno = self.declarar(nombre, 'char[]')
                if self.aceptar('='):
                    self.emitir('=', self.siguiente().lexema, None, interno)
                elif len(self.ambitos) == 1:
                    self.emitir('=', '""', None, interno)
            else:
                interno = self.declarar(nombre, tipo)
                if self.aceptar('='):
                    valor = self.convertir(self.expresion(), tipo)
                    self.emitir('=', valor.valor, None, interno)
                elif len(self.ambitos) == 1:
                    # En C las variables globales sin valor inicial valen cero.
                    cero = {'char': "'\\0'", 'bool': 'false', 'float': '0.0', 'double': '0.0'}.get(tipo, '0')
                    self.emitir('=', cero, None, interno)
            if not self.aceptar(','):
                break
            nombre = self.identificador().lexema
        self.exigir(';')

    def bloque(self, nuevo_ambito=True):
        self.exigir('{')
        if nuevo_ambito:
            self.abrir_ambito()
        try:
            while not self.es('}'):
                if self.actual() is None:
                    raise ErrorIntermedio('bloque sin cerrar')
                self.sentencia()
            self.exigir('}')
        finally:
            if nuevo_ambito:
                self.cerrar_ambito()

    def cuerpo(self):
        if self.es('{'):
            return self.bloque()
        if self.es(*TIPOS):
            raise ErrorIntermedio('coloque llaves alrededor de una declaración usada como cuerpo de if/while/for',
                                  self.actual())
        return self.sentencia()

    # ------------------------------------------------------------ expresiones
    def expresion(self):
        return self.logico_o()

    def logico_o(self):
        izq = self.logico_y()
        while self.es('||'):
            self.siguiente()
            verdadero, fin = self.nueva_etiqueta(), self.nueva_etiqueta()
            self.emitir('iftrue', izq.valor, None, verdadero)
            der = self.logico_y()
            self.emitir('iftrue', der.valor, None, verdadero)
            res = self.nuevo_temp()
            self.emitir('=', 'false', None, res)
            self.emitir('goto', res=fin)
            self.emitir('label', res=verdadero)
            self.emitir('=', 'true', None, res)
            self.emitir('label', res=fin)
            izq = Operando(res, 'bool')
        return izq

    def logico_y(self):
        izq = self.relacional()
        while self.es('&&'):
            self.siguiente()
            falso, fin = self.nueva_etiqueta(), self.nueva_etiqueta()
            self.emitir('iffalse', izq.valor, None, falso)
            der = self.relacional()
            self.emitir('iffalse', der.valor, None, falso)
            res = self.nuevo_temp()
            self.emitir('=', 'true', None, res)
            self.emitir('goto', res=fin)
            self.emitir('label', res=falso)
            self.emitir('=', 'false', None, res)
            self.emitir('label', res=fin)
            izq = Operando(res, 'bool')
        return izq

    def relacional(self):
        izq = self.aditiva()
        if self.es('==', '!=', '<', '>', '<=', '>='):
            op = self.siguiente().lexema
            der = self.aditiva()
            t = self.nuevo_temp()
            self.emitir(op, izq.valor, der.valor, t)
            return Operando(t, 'bool')
        return izq

    def _binaria(self, izq, op, der):
        tipo = self._tipo_resultado(izq.tipo, der.tipo)
        izq, der = self.convertir(izq, tipo), self.convertir(der, tipo)
        t = self.nuevo_temp()
        self.emitir(op, izq.valor, der.valor, t)
        return Operando(t, tipo)

    def aditiva(self):
        izq = self.multiplicativa()
        while self.es('+', '-'):
            op = self.siguiente().lexema
            izq = self._binaria(izq, op, self.multiplicativa())
        return izq

    def multiplicativa(self):
        izq = self.unaria()
        while self.es('*', '/', '%'):
            op = self.siguiente().lexema
            izq = self._binaria(izq, op, self.unaria())
        return izq

    def unaria(self):
        if self.es('+', '-', '!'):
            op = self.siguiente().lexema
            operando = self.unaria()
            if op == '+':
                return operando
            if op == '-' and operando.tipo in ('int', 'float', 'double') and \
                    re.fullmatch(r'\d+(\.\d+)?', operando.valor):
                return Operando('-' + operando.valor, operando.tipo)   # literal negativo
            t = self.nuevo_temp()
            if op == '!':
                self.emitir('!', operando.valor, None, t)
                return Operando(t, 'bool')
            self.emitir('minus', operando.valor, None, t)
            return Operando(t, operando.tipo)
        return self.primaria()

    def primaria(self):
        t = self.siguiente()
        if t is None:
            raise ErrorIntermedio('expresión incompleta')
        if t.tipo == 'NUMERO_ENTERO':
            return Operando(str(int(t.lexema, 10)), 'int')
        if t.tipo == 'NUMERO_DECIMAL':
            return Operando(t.lexema, 'float')
        if t.tipo == 'CADENA':
            return Operando(t.lexema, 'string')
        if t.tipo == 'CARACTER':
            return Operando(t.lexema, 'char')
        if t.lexema in ('true', 'false'):
            return Operando(t.lexema, 'bool')
        if t.tipo == 'IDENTIFICADOR':
            if self.aceptar('('):
                args = self.argumentos()
                self.exigir(')')
                return self.llamada(t.lexema, args, con_resultado=True)
            interno, tipo = self.buscar(t.lexema)
            if self.aceptar('['):
                indice = self.expresion()
                self.exigir(']')
                r = self.nuevo_temp()
                self.emitir('[]', interno, indice.valor, r)
                return Operando(r, 'char')
            return Operando(interno, tipo)
        if t.lexema == '(':
            e = self.expresion()
            self.exigir(')')
            return e
        raise ErrorIntermedio('expresión no soportada', t)

    def argumentos(self):
        args = []
        if not self.es(')'):
            args.append(self.expresion())
            while self.aceptar(','):
                args.append(self.expresion())
        return args

    def llamada(self, nombre, args, con_resultado):
        retorno, tipos = self.funciones.get(nombre, ('int', []))
        for i, arg in enumerate(args):
            if i < len(tipos):
                arg = self.convertir(arg, tipos[i])
            self.emitir('param', arg.valor)
        if con_resultado and retorno != 'void':
            t = self.nuevo_temp()
            self.emitir('call', nombre, str(len(args)), t)
            return Operando(t, retorno)
        self.emitir('call', nombre, str(len(args)))
        return Operando('', retorno)


def generar_intermedio(tokens):
    """Devuelve la lista de cuádruplas. El llamador debe validar las fases 1-3."""
    return GeneradorIntermedio(tokens).generar()


def formatear_intermedio(instrucciones):
    """Texto legible: `func`, `endfunc` y etiquetas al margen; el resto con sangría."""
    lineas = []
    anterior = None
    for ins in instrucciones:
        if ins.op == 'func' and lineas:
            lineas.append('')                   # línea en blanco antes de cada función
        elif anterior == 'endfunc' and ins.op != 'func':
            lineas.append('')                   # y entre las funciones y el código global
        margen = ins.op in ('label', 'func', 'endfunc')
        lineas.append(('' if margen else '    ') + ins.texto())
        anterior = ins.op
    return '\n'.join(lineas) + ('\n' if lineas else '')
