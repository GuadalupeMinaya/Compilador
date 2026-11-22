"""Pruebas de la lógica de apoyo de la interfaz (no requieren tkinter).

Ejecutar: python -m unittest -v pruebas_diagnosticos.py
"""
import unittest

from diagnosticos import (ejecutar_js, node_disponible, posicion_error_traduccion,
                          sugerencia, sugerencia_lexica)
from motor import procesar_codigo


class DiagnosticosTest(unittest.TestCase):
    def test_sugerencias_conocidas(self):
        casos = {
            'int x = 5\nprint(x);': ';',
            'int x = 5; x = 2.5;': 'float',
            'x = 1;': 'Declare',
            'int a; int a;': 'nombre',
            'int f(void) { return 1.5; }': 'retornado',
            'int f(void) { }': 'return',
            'int x = 4 / 0;': 'divisor',
        }
        for codigo, palabra in casos.items():
            r = procesar_codigo(codigo)
            errores = list(r.errores_sintacticos) + list(r.semantica.get('errores', []))
            self.assertTrue(errores, codigo)
            ayuda = sugerencia(errores[0].tipo, errores[0].mensaje)
            self.assertIn(palabra, ayuda, f'{codigo!r}: {errores[0].tipo} -> {ayuda!r}')

    def test_sin_sugerencia_para_desconocido(self):
        self.assertEqual(sugerencia('Otro tipo', 'otro mensaje'), '')

    def test_sugerencia_lexica(self):
        self.assertIn('@', sugerencia_lexica('@'))

    def test_posicion_error_traduccion(self):
        r = procesar_codigo('int x;\nif(1) int a;')
        self.assertEqual(posicion_error_traduccion(r.error_traduccion)[0], 2)
        self.assertIsNone(posicion_error_traduccion('sin posición'))

    @unittest.skipUnless(node_disponible(), 'Node.js no está instalado')
    def test_ejecutar_js_correcto(self):
        res = ejecutar_js(procesar_codigo('print("hola", 2 + 3);').javascript)
        self.assertTrue(res.correcto)
        self.assertEqual(res.salida.strip(), 'hola 5')

    @unittest.skipUnless(node_disponible(), 'Node.js no está instalado')
    def test_ejecutar_js_division_cero(self):
        res = ejecutar_js(procesar_codigo('int a = 1; int b = 0; print(a / b);').javascript)
        self.assertFalse(res.correcto)
        self.assertIn('División entre cero', res.errores)

    @unittest.skipUnless(node_disponible(), 'Node.js no está instalado')
    def test_ejecutar_js_ciclo_infinito(self):
        res = ejecutar_js(procesar_codigo('while (1) { }').javascript, limite=1)
        self.assertFalse(res.correcto)
        self.assertIn('ciclo infinito', res.aviso)


if __name__ == '__main__':
    unittest.main()
