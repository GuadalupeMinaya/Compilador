"""Pruebas de la fase de código intermedio (tres direcciones).

Además de revisar la estructura del código generado, se ejecuta con un pequeño
intérprete de cuádruplas y se compara su salida con la del JavaScript traducido
(ejecutado con Node.js). Si ambos coinciden, el código intermedio conserva el
significado del programa.

Ejecutar: python -m unittest -v pruebas_intermedio.py
"""
import math
import re
import shutil
import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from intermedio import OPS_BINARIOS
from motor import procesar_codigo

CARPETA = Path(__file__).resolve().parent


# --------------------------------------------------------------------------
# Intérprete mínimo de código de tres direcciones (solo para las pruebas)
# --------------------------------------------------------------------------
class ErrorEjecucion(Exception):
    pass


ESCAPES = {'n': '\n', 't': '\t', 'r': '\r', '0': '\0', '\\': '\\', '"': '"', "'": "'"}
RE_OPERANDO = re.compile(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|[^,\s]+')


def _desescapar(texto):
    return re.sub(r'\\(.)', lambda m: ESCAPES.get(m.group(1), m.group(1)), texto)


def _wrap32(n):
    n &= 0xFFFFFFFF
    return n - (1 << 32) if n & 0x80000000 else n


def _formato(v):
    if isinstance(v, bool):
        return 'true' if v else 'false'
    if isinstance(v, float) and v == int(v) and abs(v) < 1e21:
        return str(int(v))
    return str(v)


class MaquinaTresDirecciones:
    def __init__(self, instrucciones):
        self.ins = instrucciones
        self.etiquetas = {i.res: n for n, i in enumerate(instrucciones) if i.op == 'label'}
        self.funciones = {}
        for n, i in enumerate(instrucciones):
            if i.op == 'func':
                fin = next(k for k in range(n, len(instrucciones)) if instrucciones[k].op == 'endfunc')
                params = [p.strip() for p in (i.arg1 or '').split(',') if p.strip()]
                self.funciones[i.res] = (n, fin, params)
        # Nombres globales: los asignados fuera del cuerpo de cualquier función.
        self.globales = {}
        self.nombres_globales = set()
        dentro = False
        for i in instrucciones:
            if i.op == 'func':
                dentro = True
            elif i.op == 'endfunc':
                dentro = False
            elif not dentro and i.op not in ('label', 'goto', 'iffalse', 'iftrue', 'param', 'call',
                                             'return', 'print') and i.res:
                self.nombres_globales.add(i.res)
        self.salida = []
        self.pasos = 0

    def valor(self, texto, marco):
        if texto in ('true', 'false'):
            return texto == 'true'
        if texto.startswith('"'):
            return _desescapar(texto[1:-1])
        if texto.startswith("'"):
            return _desescapar(texto[1:-1])
        if re.fullmatch(r'-?\d+', texto):
            return int(texto)
        if re.fullmatch(r'-?\d+\.\d+', texto):
            return float(texto)
        if texto in marco:
            return marco[texto]
        if texto in self.globales:
            return self.globales[texto]
        raise ErrorEjecucion(f'operando sin valor: {texto}')

    def asignar(self, nombre, valor, marco, es_global_ctx):
        if nombre in self.nombres_globales:
            self.globales[nombre] = valor
        else:
            marco[nombre] = valor

    def operar(self, op, a, b):
        if op in ('<', '>', '<=', '>=', '==', '!='):
            return {'<': a < b, '>': a > b, '<=': a <= b, '>=': a >= b,
                    '==': a == b, '!=': a != b}[op]
        enteros = (isinstance(a, int) and not isinstance(a, bool) and
                   isinstance(b, int) and not isinstance(b, bool))
        if op == '+':
            return _wrap32(a + b) if enteros else a + b
        if op == '-':
            return _wrap32(a - b) if enteros else a - b
        if op == '*':
            return _wrap32(a * b) if enteros else a * b
        if op == '/':
            if enteros:
                if b == 0:
                    raise ErrorEjecucion('División entre cero')
                return _wrap32(int(a / b)) if abs(a) < 2 ** 52 else _wrap32(math.trunc(a / b))
            return a / b
        if op == '%':
            if b == 0:
                raise ErrorEjecucion('Módulo entre cero')
            return int(math.fmod(a, b))
        raise ErrorEjecucion(f'operador {op}')

    def ejecutar_funcion(self, nombre, argumentos):
        inicio, fin, params = self.funciones[nombre]
        marco = dict(zip(params, argumentos))
        return self.correr(inicio + 1, fin, marco)

    def correr(self, pc, fin, marco):
        pila_param = []
        while pc < fin:
            self.pasos += 1
            if self.pasos > 200000:
                raise ErrorEjecucion('demasiados pasos')
            i = self.ins[pc]
            op = i.op
            pc += 1
            if op == 'func':               # al ejecutar el código global se saltan las funciones
                pc = self.funciones[i.res][1] + 1
            elif op == 'label' or op == 'endfunc':
                continue
            elif op == '=':
                self.asignar(i.res, self.valor(i.arg1, marco), marco, False)
            elif op in OPS_BINARIOS:
                self.asignar(i.res, self.operar(op, self.valor(i.arg1, marco), self.valor(i.arg2, marco)),
                             marco, False)
            elif op == 'minus':
                self.asignar(i.res, -self.valor(i.arg1, marco), marco, False)
            elif op == '!':
                self.asignar(i.res, not self.valor(i.arg1, marco), marco, False)
            elif op == 'itof':
                self.asignar(i.res, float(self.valor(i.arg1, marco)), marco, False)
            elif op == '[]':
                self.asignar(i.res, self.valor(i.arg1, marco)[self.valor(i.arg2, marco)], marco, False)
            elif op == 'goto':
                pc = self.etiquetas[i.res]
            elif op == 'iffalse':
                if not self.valor(i.arg1, marco):
                    pc = self.etiquetas[i.res]
            elif op == 'iftrue':
                if self.valor(i.arg1, marco):
                    pc = self.etiquetas[i.res]
            elif op == 'param':
                pila_param.append(self.valor(i.arg1, marco))
            elif op == 'call':
                n = int(i.arg2)
                argumentos = pila_param[len(pila_param) - n:] if n else []
                del pila_param[len(pila_param) - n:]
                resultado = self.ejecutar_funcion(i.arg1, argumentos)
                if i.res:
                    self.asignar(i.res, resultado, marco, False)
            elif op == 'return':
                return self.valor(i.arg1, marco) if i.arg1 is not None else None
            elif op == 'print':
                self.salida.append(' '.join(_formato(self.valor(t, marco))
                                            for t in RE_OPERANDO.findall(i.arg1)))
            else:
                raise ErrorEjecucion(f'instrucción desconocida: {op}')
        return None

    def ejecutar(self):
        self.correr(0, len(self.ins), {})
        return '\n'.join(self.salida)


def ejecutar_intermedio(instrucciones):
    return MaquinaTresDirecciones(instrucciones).ejecutar()


def ejecutar_js(javascript):
    with TemporaryDirectory() as tmp:
        ruta = Path(tmp, 'programa.js')
        ruta.write_text(javascript, encoding='utf-8')
        r = subprocess.run(['node', str(ruta)], capture_output=True, text=True, timeout=10)
        return r.returncode, r.stdout.strip(), r.stderr


# --------------------------------------------------------------------------
# Pruebas
# --------------------------------------------------------------------------
PROGRAMAS = {
    'aritmetica_enteros': 'int a = 7; int b = 2; print(a + b, a - b, a * b, a / b, a % b, -a / b);',
    'mezcla_int_float': 'int a = 3; float f = a; double d = f / 2; print(f, d, a + 0.5);',
    'division_constante': 'int a = 11 / 2 / 2; int b = -5 / 2; float c = 5.0 / 2; print(a, b, c);',
    'recursion': 'int fact(int n) { if (n <= 1) { return 1; } return n * fact(n - 1); } '
                 'int main(void) { print(fact(5)); return 0; }',
    'recursion_doble': 'int fib(int n) { if (n < 2) { return n; } return fib(n - 1) + fib(n - 2); } '
                       'print(fib(10));',
    'while_for': 'int i = 0; while (i < 3) { print(i); i = i + 1; } '
                 'for (int j = 0; j < 3; j++) { print("j", j); }',
    'for_paso_decremento': 'for (int k = 3; k > 0; k--) { print(k); }',
    'anidados': 'int s = 0; for (int i = 0; i < 3; i++) { for (int j = 0; j < 3; j++) '
                '{ if (i == j) { s = s + 10; } else { s = s + 1; } } } print(s);',
    'logicos': 'bool a = true; bool b = false; print(a && b, a || b, !a, a && !b, (a || b) && !b);',
    'cortocircuito': 'int cont = 0; int sube(void) { cont = cont + 1; return 1; } '
                     'bool r = false && sube() == 1; bool q = true || sube() == 1; print(cont, r, q);',
    'condicion_compuesta': 'int x = 5; if (x > 1 && x < 10 || x == 99) { print("dentro"); } else { print("fuera"); }',
    'cadenas_y_char': 'char nombre[] = "Ana"; char c = \'Z\'; print("Hola", nombre, c, nombre[0], nombre[2]);',
    'sombra_de_variable': 'int x = 1; int f(void) { int x = 5; return x + 1; } print(f(), x);',
    'parametros_conversion': 'float mitad(float n) { return n / 2; } print(mitad(9));',
    'void_y_return': 'void saluda(int veces) { for (int i = 0; i < veces; i++) { print("hola", i); } return; } '
                     'saluda(2);',
    'funcion_definida_despues': 'int main(void) { print(doble(4)); return 0; } int doble(int n) { return n * 2; }',
    'main_explicito': 'void main(void) { print(10); return; } main();',
    'global_sin_inicializar': 'int g; float h; bool b; print(g, h, b); g = 4; print(g);',
    'argumentos_anidados': 'int suma(int a, int b) { return a + b; } int doble(int n) { return n * 2; } '
                           'print(suma(doble(3), suma(1, 2)));',
    'desbordamiento_entero': 'int a = 2147483647; int b = a + 1; print(b);',
}


class IntermedioTest(unittest.TestCase):
    def procesar(self, fuente):
        r = procesar_codigo(fuente)
        diag = (f'lex={r.errores_lexicos} sin={r.errores_sintacticos} '
                f'sem={r.semantica.get("errores")} ir={r.error_intermedio} js={r.error_traduccion}')
        self.assertTrue(r.exitoso, diag)
        self.assertTrue(r.intermedio, 'no se generó código intermedio')
        return r

    # ---- estructura del código generado
    def test_formato_de_tres_direcciones(self):
        r = self.procesar('int a = 1; int b = 2; int c = a + b * 3; print(c);')
        self.assertEqual(r.intermedio_texto.splitlines(),
                         ['    a = 1', '    b = 2', '    t1 = b * 3', '    t2 = a + t1', '    c = t2', '    print c'])

    def test_cada_instruccion_tiene_a_lo_sumo_tres_direcciones(self):
        r = self.procesar(PROGRAMAS['anidados'])
        for ins in r.intermedio:
            self.assertLessEqual(len([x for x in (ins.arg1, ins.arg2, ins.res) if x is not None]), 3)
            if ins.op in OPS_BINARIOS:
                self.assertTrue(ins.arg1 and ins.arg2 and ins.res)

    def test_if_else_usa_etiquetas(self):
        r = self.procesar('int x = 1; if (x > 0) { print(1); } else { print(2); }')
        ops = [i.op for i in r.intermedio]
        self.assertEqual(ops.count('iffalse'), 1)
        self.assertEqual(ops.count('label'), 2)
        self.assertEqual(ops.count('goto'), 1)

    def test_while_y_for_cierran_con_salto_atras(self):
        for fuente in ('int i = 0; while (i < 2) { i = i + 1; }',
                       'for (int i = 0; i < 2; i++) { print(i); }'):
            r = self.procesar(fuente)
            ins = r.intermedio
            salto = next(k for k, i in enumerate(ins) if i.op == 'goto')
            destino = next(k for k, i in enumerate(ins) if i.op == 'label' and i.res == ins[salto].res)
            self.assertLess(destino, salto, 'el salto del ciclo debe volver al inicio')

    def test_conversion_int_a_float_explicita(self):
        r = self.procesar('int a = 3; float f = a; print(f);')
        self.assertIn('(float) a', r.intermedio_texto)
        r = self.procesar('float f = 2; print(f);')
        self.assertIn('f = 2.0', r.intermedio_texto)

    def test_llamada_con_param_y_call(self):
        r = self.procesar('int suma(int a, int b) { return a + b; } print(suma(1, 2));')
        texto = r.intermedio_texto
        self.assertIn('func suma(a, b):', texto)
        self.assertIn('param 1\n    param 2\n    t2 = call suma, 2', texto)
        self.assertIn('endfunc', texto)

    def test_main_se_invoca_una_sola_vez(self):
        r = self.procesar('int main(void) { return 0; }')
        self.assertEqual(r.intermedio_texto.count('call main, 0'), 1)
        r = self.procesar('void main(void) { return; } main();')
        self.assertEqual(r.intermedio_texto.count('call main, 0'), 1)

    def test_identificadores_t1_y_L1_no_chocan_con_temporales(self):
        r = self.procesar('int t1 = 4; int L1 = 5; int c = t1 + L1 * 2; print(c);')
        self.assertIn('_t1 = L1 * 2', r.intermedio_texto)
        self.assertEqual(ejecutar_intermedio(r.intermedio), '14')

    def test_variable_oculta_recibe_nombre_distinto(self):
        r = self.procesar(PROGRAMAS['sombra_de_variable'])
        self.assertIn('x_1 = 5', r.intermedio_texto)

    def test_tuplas_para_la_tabla_de_la_interfaz(self):
        r = self.procesar('int a = 1 + 2; if (a > 1) { print(a); }')
        for ins in r.intermedio:
            t = ins.como_tupla()
            self.assertEqual(len(t), 4)
            self.assertTrue(all(isinstance(x, str) for x in t))

    # ---- no se genera nada si hay errores previos
    def test_programas_con_errores_no_generan_intermedio(self):
        for fuente in ('int x = ;', 'int x = 1; y = 2;', 'int x = 1; int x = 2;', 'int x = @;'):
            r = procesar_codigo(fuente)
            self.assertFalse(r.exitoso)
            self.assertFalse(r.intermedio, fuente)

    # ---- equivalencia con el JavaScript traducido
    @unittest.skipUnless(shutil.which('node'), 'Node.js no disponible')
    def test_equivalencia_con_javascript_en_programas_de_prueba(self):
        for nombre, fuente in PROGRAMAS.items():
            with self.subTest(programa=nombre):
                r = self.procesar(fuente)
                codigo, js, err = ejecutar_js(r.javascript)
                self.assertEqual(codigo, 0, err)
                self.assertEqual(ejecutar_intermedio(r.intermedio), js)

    @unittest.skipUnless(shutil.which('node'), 'Node.js no disponible')
    def test_equivalencia_con_javascript_en_ejemplos_del_proyecto(self):
        validos = 0
        for ruta in sorted((CARPETA / 'ejemplos').iterdir()):
            fuente = ruta.read_text(encoding='utf-8')
            r = procesar_codigo(fuente)
            if not r.exitoso:
                continue
            validos += 1
            with self.subTest(ejemplo=ruta.name):
                codigo, js, err = ejecutar_js(r.javascript)
                self.assertEqual(codigo, 0, err)
                self.assertEqual(ejecutar_intermedio(r.intermedio), js)
        self.assertGreaterEqual(validos, 4)

    def test_division_entre_cero_se_detecta_tambien_en_el_intermedio(self):
        r = self.procesar('int a = 0; int b = 5 / a; print(b);')
        with self.assertRaises(ErrorEjecucion):
            ejecutar_intermedio(r.intermedio)


if __name__ == '__main__':
    unittest.main()
