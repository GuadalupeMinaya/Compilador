"""Pruebas de regresión para el mini-C ampliado (4 fases + Node)."""
import shutil
import unittest
from motor import procesar_codigo, tokenizar
from lexico_portable import tokenizar as tokenizar_python
from diagnosticos import ejecutar_js


class NuevasFuncionalidades(unittest.TestCase):
    def ok(self, fuente, salida=None):
        r = procesar_codigo(fuente)
        self.assertFalse(r.errores_lexicos, f'Errores léxicos: {r.errores_lexicos}')
        self.assertFalse(r.errores_sintacticos, f'Errores sintácticos: {r.errores_sintacticos}')
        self.assertFalse(r.semantica.get('errores'), f'Errores semánticos: {[str(e) for e in r.semantica.get("errores", [])]}')
        self.assertTrue(r.exitoso, r.error_traduccion)
        if salida is not None and shutil.which('node'):
            e = ejecutar_js(r.javascript)
            self.assertTrue(e.correcto, e.errores or e.aviso)
            self.assertEqual(e.salida.strip(), salida)
        return r

    def error(self, fuente, tipo=None):
        r = procesar_codigo(fuente)
        self.assertFalse(r.exitoso, f'Se aceptó un programa inválido: {fuente}')
        if tipo:
            lista = [e.tipo for e in r.semantica.get('errores', [])]
            if not lista: lista = [e.tipo for e in r.errores_sintacticos]
            self.assertIn(tipo, lista, lista)

    def test_char_y_texto(self):
        self.ok('int main(void){ char letra = \'A\'; char nombre[]="Ana"; print(nombre, letra); return 0; }','Ana A')

    def test_char_escapado(self):
        self.ok('int main(void){ char letra=\'\\n\'; print("fin", letra); return 0; }', 'fin')

    def test_arreglo_con_tamano(self):
        self.ok('int main(void){ char nombre[10] = "Jose"; print(nombre[0],nombre); return 0; }', 'J Jose')

    def test_doble_y_flotante(self):
        self.ok('int main(void){ float f=1.5; double x=2.25; double resultado=f+x; print(resultado);return 0;}', '3.75')

    def test_funciones_nuevos_tipos(self):
        self.ok('char primera(char x){return x;} double doble(double x){return x*2;} int main(void){print(primera(\'R\'), doble(4.5));return 0;}', 'R 9')

    def test_bool_y_logicos(self):
        self.ok('int main(void){bool si=true;bool no=false;if(si && !no || false){print("SI");}return 0;}', 'SI')

    def test_logico_con_numeros_retorna_bool(self):
        self.ok('int main(void){bool si=2 && 3; print(si);return 0;}', 'true')

    def test_incremento_decremento(self):
        self.ok('int main(void){int x=2; x++; x--; print(x); return 0;}', '2')

    def test_for_incremento(self):
        self.ok('int main(void){int t=0;for(int i=0;i<4;i++){t=t+i;}print(t);return 0;}', '6')

    def test_for_double(self):
        self.ok('int main(void){double t=0.5;for(double i=0.5;i<2.0;i++){t=t+i;}print(t);return 0;}', '2.5')

    def test_modulo(self):
        self.ok('int main(void){int a=8;print(a%3);return 0;}', '2')

    def test_prioridad(self):
        self.ok('int main(void){bool b=true || false && false; print(b);return 0;}', 'true')

    def test_char_texto_exceso(self):
        self.error('int main(void){char nombre[3]="Ana";return 0;}', 'Tamaño de arreglo insuficiente')

    def test_arreglo_sin_tamano_ni_texto(self):
        self.error('int main(void){char nombre[];return 0;}', 'Tamaño de arreglo faltante')

    def test_char_no_admite_cadena(self):
        self.error('int main(void){char nombre="Ana";return 0;}', 'Tipos incompatibles')

    def test_string_no_es_tipo(self):
        self.error('int main(void){string nombre="Ana";return 0;}')

    def test_decimal_no_es_tipo(self):
        self.error('int main(void){decimal peso=8.5;return 0;}')

    def test_porcentaje_exige_enteros(self):
        self.error('int main(void){int r=5%2.0;return 0;}', 'Operacion incompatible')

    def test_incremento_bool_rechazado(self):
        self.error('int main(void){bool b=true; b++;return 0;}', 'Operacion incompatible')

    def test_indice_no_int(self):
        self.error('int main(void){char t[]="Ana"; print(t[1.5]);return 0;}', 'Indice incompatible')

    def test_asignacion_a_arreglo_no_valida(self):
        self.error('int main(void){char t[]="Ana"; t="Luz";return 0;}', 'Tipos incompatibles')

    def test_lexer_python_mismos_tokens(self):
        fuente='char nombre[]="Jo\\\\se"; char letra=\'A\'; bool ok=true && false; int i=2%1; i++; //hi\n'
        self.assertEqual(tokenizar(fuente), tokenizar_python(fuente))

    def test_cero_modulo_en_tiempo_ejecucion(self):
        r=self.ok('int main(void){int x=0; print(2%x);return 0;}')
        if shutil.which('node'):
            e=ejecutar_js(r.javascript)
            self.assertFalse(e.correcto)
            self.assertIn('Módulo entre cero',e.errores)


if __name__ == '__main__':
    unittest.main(verbosity=2)
