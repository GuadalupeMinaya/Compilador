"""Lógica de apoyo de la interfaz (sin tkinter, para poder probarla):
sugerencias de corrección, posición de errores de traducción y ejecución del JS con Node.
"""
import os
import re
import shutil
import subprocess
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory


def _normalizar(texto):
    sin_tildes = unicodedata.normalize('NFD', texto)
    return ''.join(c for c in sin_tildes if unicodedata.category(c) != 'Mn').lower()


# (texto que debe aparecer en el tipo de error normalizado, o en el mensaje) -> sugerencia
_REGLAS = [
    ('falta \';\'', "Agregue ';' al final de la instrucción. Si el error apunta a la línea siguiente, "
                    "el ';' falta en la línea anterior."),
    ('simbolo faltante', 'Falta un símbolo de cierre o separación (; ) } ,). Revise la línea indicada y la anterior.'),
    ('expresion incompleta', 'Complete la expresión: falta un número, variable o llamada a función.'),
    ('token inesperado', 'Revise que los paréntesis y las llaves estén balanceados y que no sobre ningún símbolo.'),
    ('variable no declarada', "Declare la variable antes de usarla (por ejemplo 'int nombre;'), "
                              'revise que esté escrita igual y que esté dentro de su ámbito.'),
    ('tipos incompatibles', 'Use el mismo tipo en ambos lados: cambie la variable a float '
                            'o evite asignar un decimal a un int.'),
    ('identificador duplicado', 'Cambie el nombre de la segunda declaración o elimínela.'),
    ('tipo de argumento incompatible', 'Envíe un argumento del tipo que declara la función '
                                       '(int, float, double, char o bool) en esa posición.'),
    ('retorno incompatible', 'Haga que el valor retornado coincida con el tipo de la función, '
                             'o cambie el tipo declarado de la función.'),
    ('retorno faltante', "Agregue un 'return' al final de la función y en cada rama de if/else."),
    ('division entre cero', 'Use un divisor distinto de cero.'),
    ('numero de argumentos', 'Revise cuántos parámetros declara la función y cuántos argumentos envía.'),
]


def sugerencia(tipo, mensaje=''):
    """Devuelve una sugerencia de corrección para un error conocido, o '' si no hay."""
    texto = _normalizar(f'{tipo} {mensaje}')
    for clave, ayuda in _REGLAS:
        if clave in texto:
            return ayuda
    return ''


def sugerencia_lexica(lexema):
    return f"Elimine o reemplace el carácter '{lexema}', que no pertenece al lenguaje."


_POSICION = re.compile(r'L[ií]nea (\d+), columna (\d+)')


def posicion_error_traduccion(texto):
    """(línea, columna) si el mensaje de ErrorTraduccion trae posición; si no, None."""
    m = _POSICION.search(texto or '')
    return (int(m.group(1)), int(m.group(2))) if m else None


@dataclass
class ResultadoEjecucion:
    salida: str = ''
    errores: str = ''
    codigo: int = 0
    aviso: str = ''      # motivo si no se pudo ejecutar con normalidad

    @property
    def correcto(self):
        return not self.aviso and self.codigo == 0


def node_disponible():
    return shutil.which('node') is not None


def ejecutar_js(javascript, limite=5.0):
    """Ejecuta el JavaScript con Node.js (límite de tiempo para ciclos infinitos)."""
    node = shutil.which('node')
    if not node:
        return ResultadoEjecucion(codigo=-1, aviso=(
            'Node.js no está instalado o no está en el PATH. Instálelo desde nodejs.org '
            'o guarde el JS y ejecútelo en otro entorno.'))
    with TemporaryDirectory() as tmp:
        ruta = Path(tmp, 'programa.js')
        ruta.write_text(javascript, encoding='utf-8')
        extra = {'creationflags': subprocess.CREATE_NO_WINDOW} if os.name == 'nt' else {}
        try:
            r = subprocess.run([node, str(ruta)], capture_output=True, text=True,
                               encoding='utf-8', timeout=limite, **extra)
        except subprocess.TimeoutExpired:
            return ResultadoEjecucion(codigo=-1, aviso=(
                f'Ejecución detenida: el programa tardó más de {limite:g} s (¿ciclo infinito?).'))
    errores = _limpiar_traza(r.stderr)
    return ResultadoEjecucion(salida=r.stdout, errores=errores, codigo=r.returncode)


def _limpiar_traza(stderr):
    """Deja solo la línea del error (Error: mensaje), sin rutas temporales ni pila de Node."""
    for linea in stderr.splitlines():
        if re.match(r'^\w*Error:', linea):
            return linea.strip()
    return stderr.strip()
