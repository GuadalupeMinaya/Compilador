"""Pruebas fase 4: usa lexer real en C + fases 2, 3 y ejecución de JS con Node.

Ejecutar: python -m unittest -v pruebas_traduccion.py
"""
import shutil
import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from motor import procesar_codigo


class TraduccionTest(unittest.TestCase):
    def comprobar(self, fuente, esperado):
        r = procesar_codigo(fuente)
        self.assertTrue(r.exitoso, self._diagnosticos(r))
        self.assertTrue(r.javascript.strip())
        if shutil.which('node'):
            with TemporaryDirectory() as tmp:
                ruta = Path(tmp, 'programa.js')
                ruta.write_text(r.javascript, encoding='utf-8')
                ejecucion = subprocess.run(['node', str(ruta)], capture_output=True,
                                            text=True, timeout=5)
                self.assertEqual(ejecucion.returncode, 0, ejecucion.stderr)
                self.assertEqual(ejecucion.stdout.strip(), esperado)
        return r

    @staticmethod
    def _diagnosticos(r):
        return (f'léxicos={r.errores_lexicos}, sintácticos={r.errores_sintacticos}, '
                f'semánticos={r.semantica.get("errores")}, traducción={r.error_traduccion}')

    def test_ejemplo_original(self):
        codigo = Path('ejemplos/01_semantica_correcta.txt').read_text(encoding='utf-8')
        self.comprobar(codigo, 'Resultado 9.5')

    def test_programa_completo(self):
        codigo = Path('ejemplos/12_programa_completo_correcto.txt').read_text(encoding='utf-8')
        self.comprobar(codigo, 'i = 5\ni = 4\ni = 3\npromedio 5.5')

    def test_division_entera(self):
        r = self.comprobar('int a = 5 / 2; int b = -5 / 2; float c = 5.0 / 2; '
                          'print(a, b, c);', '2 -2 2.5')
        self.assertIn('Math.trunc', r.javascript)

    def test_division_entera_anidada(self):
        self.comprobar('int a = 11 / 2 / 2; print(a);', '2')

    def test_recursion_y_main(self):
        self.comprobar('int factorial(int n) { if(n <= 1) { return 1; } '
                      'return n * factorial(n - 1); } '
                      'int main(void) { print(factorial(5)); return 0; }', '120')

    def test_main_explicito_no_doble_llamado(self):
        self.comprobar('void main(void) { print(10); return; } main();', '10')

    def test_avance_for_y_while(self):
        self.comprobar('int i = 0; while(i < 2) { print(i); i = i + 1; } '
                      'for (int j = 2; j < 4; j = j + 1) print(j);', '0\n1\n2\n3')

    def test_condicional_y_else_sin_llaves(self):
        self.comprobar('int x = 8; if(x < 3) print(1); else print(2);', '2')

    def test_sombreado_variable(self):
        self.comprobar('int a = 2; { int a = 8; print(a); } print(a);', '8\n2')

    def test_funcion_definida_despues(self):
        self.comprobar('int a = f(3); int f(int x) { return x + 2; } print(a);', '5')

    def test_reservado_js(self):
        r = self.comprobar('int let = 1; int console = 3; int Math = 4; '
                          'print(let, console, Math);', '1 3 4')
        self.assertIn('__ml_let', r.javascript)

    def test_cadena_con_separador_lexer(self):
        self.comprobar('print("a|b", 7);', 'a|b 7')

    def test_comentarios(self):
        self.comprobar('/* varios\nrenglones */ int a = 1; // uno\nprint(a);', '1')

    def test_asignacion_en_for(self):
        self.comprobar('int i; for (i = 0; i < 3; i = i + 1) { print(i); }', '0\n1\n2')

    def test_sin_codigo(self):
        self.assertFalse(procesar_codigo(' \n // comentario').exitoso)

    def test_bloqueo_lexico(self):
        r = procesar_codigo('int x = 1; @')
        self.assertTrue(r.errores_lexicos)
        self.assertFalse(r.javascript)

    def test_bloqueo_sintactico(self):
        r = procesar_codigo('int x = 1')
        self.assertTrue(r.errores_sintacticos)
        self.assertFalse(r.javascript)

    def test_bloqueo_semantico(self):
        r = procesar_codigo('int x = 1; x = 1.5;')
        self.assertTrue(r.semantica['errores'])
        self.assertFalse(r.javascript)

    def test_advertencias_no_bloquean(self):
        r = procesar_codigo('int f(void) { int a; return a; }')
        self.assertTrue(r.exitoso)
        self.assertTrue(r.semantica['advertencias'])

    def test_construccion_con_declaracion_sin_llaves(self):
        r = procesar_codigo('if(1) int a;')
        self.assertFalse(r.exitoso)
        self.assertIn('llaves', r.error_traduccion)

    def test_desbordamiento_32_bits(self):
        # En C (int de 32 bits, con envoltura): 2000000000 + 2000000000 = -294967296
        self.comprobar('int a = 2000000000; int b = a + a; int c = a * 3; print(b, c);',
                       '-294967296 1705032704')

    def test_division_entre_cero_en_ejecucion(self):
        r = procesar_codigo('int a = 1; int b = 0; print(a / b);')
        self.assertTrue(r.exitoso)
        self.assertIn('__mini_div', r.javascript)
        if shutil.which('node'):
            with TemporaryDirectory() as tmp:
                ruta = Path(tmp, 'p.js')
                ruta.write_text(r.javascript, encoding='utf-8')
                ej = subprocess.run(['node', str(ruta)], capture_output=True, text=True, timeout=5)
                self.assertNotEqual(ej.returncode, 0)
                self.assertIn('División entre cero', ej.stderr)

    def test_division_variable_trunca(self):
        self.comprobar('int a = 7; int b = 2; int c = -7; print(a / b, c / b);', '3 -3')

    def test_parentesis_minimos_y_precedencia(self):
        r = self.comprobar('int a = 2; int b = 3; int c = 4; '
                           'print(a - (b - c), (a + b) * c, a - b - c, -(-a));',
                           '3 20 -5 2')
        r2 = self.comprobar('int x = 5; if (x > 3) { print(1); }', '1')
        self.assertIn('if (x > 3)', r2.javascript)

    def test_float_sin_envoltura(self):
        self.comprobar('float a = 1.5; float b = a * 2.0 + 0.5; print(b);', '3.5')


if __name__ == '__main__':
    unittest.main()
