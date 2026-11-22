"""Orquestador compartido por GUI, línea de comandos y pruebas.

Flujo: léxico -> sintáctico -> semántico (tabla de símbolos) -> código intermedio
(tres direcciones) -> traductor JS.
"""
from collections import Counter
from pathlib import Path
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field

from sintactico import analizar_programa
from semantico import analizar_semantica_completo
from traductor import traducir_tokens, ErrorTraduccion
from intermedio import generar_intermedio, formatear_intermedio, ErrorIntermedio
from lexico_portable import tokenizar as tokenizar_portable

CARPETA = Path(__file__).resolve().parent


class ErrorLexer(RuntimeError):
    pass


@dataclass
class Resultado:
    tokens: list = field(default_factory=list)
    errores_lexicos: list = field(default_factory=list)
    errores_sintacticos: list = field(default_factory=list)
    resumen_sintactico: dict = field(default_factory=dict)
    semantica: dict = field(default_factory=dict)
    intermedio: list = field(default_factory=list)     # cuádruplas (fase de código intermedio)
    intermedio_texto: str = ''
    error_intermedio: str = ''
    javascript: str = ''
    error_traduccion: str = ''

    @property
    def exitoso(self):
        return (bool(self.tokens) and not self.errores_lexicos and
                not self.errores_sintacticos and not self.semantica.get('errores') and
                not self.error_intermedio and not self.error_traduccion and bool(self.javascript))

    @property
    def tabla_simbolos(self):
        """Tabla de símbolos generada por el análisis semántico (lista de diccionarios)."""
        return self.semantica.get('tabla', [])


def _ruta_base():
    return Path(getattr(sys, '_MEIPASS', CARPETA))


def _ejecutable_lexer():
    archivo = _ruta_base() / ('analizador_extendido.exe' if os.name == 'nt' else 'analizador_extendido')
    if archivo.exists():
        return archivo
    # En Linux/macOS se compila el lexer extendido escrito en C99.
    # El analizador.exe original se conserva solo como referencia histórica.
    if os.name != 'nt':
        cc = shutil.which('gcc') or shutil.which('cc')
        fuente = _ruta_base() / 'lexico_extendido.c'
        if cc and fuente.exists():
            compilacion = subprocess.run([cc, '-O2', str(fuente), '-o', str(archivo)],
                                         capture_output=True, text=True, timeout=30)
            if compilacion.returncode == 0:
                return archivo
            raise ErrorLexer('No se pudo compilar el analizador léxico:\n' + compilacion.stderr)
    raise ErrorLexer('No se encontró compilador C para el analizador extendido.')


def tokenizar(codigo):
    """Ejecuta el lexer real en C y devuelve los tokens del mini-lenguaje."""
    # En Windows el analizador.exe original (Flex) es antiguo. Para evitar
    # ejecutarlo con palabras nuevas, se usa el lexer Python equivalente;
    # en Unix se compila y ejecuta la implementación actualizada en C.
    if os.name == 'nt':
        return tokenizar_portable(codigo)
    try:
        ruta = _ejecutable_lexer()
    except ErrorLexer:
        # Permite ejecutar la aplicación incluso sin compilador C instalado.
        return tokenizar_portable(codigo)
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', suffix='.txt', delete=False) as f:
        f.write(codigo)
        temporal = f.name
    try:
        resultado = subprocess.run([str(ruta), temporal], capture_output=True,
                                   text=True, encoding='utf-8', errors='replace', timeout=10,
                                   creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    except OSError:
        # Binario ausente, sin permiso de ejecución o de otra plataforma: se usa el lexer portátil.
        return tokenizar_portable(codigo)
    except subprocess.TimeoutExpired as exc:
        raise ErrorLexer(f'No se pudo ejecutar el lexer: {exc}') from exc
    finally:
        try:
            os.remove(temporal)
        except OSError:
            pass
    if resultado.returncode != 0:
        raise ErrorLexer(resultado.stderr.strip() or 'El analizador léxico terminó con error')
    tokens = []
    for linea_salida in resultado.stdout.splitlines():
        try:
            parte, numero_linea, numero_col = linea_salida.rsplit('|', 2)
            tipo, lexema = parte.split('|', 1)  # cadenas pueden contener '|'
            tokens.append((tipo, lexema, int(numero_linea), int(numero_col)))
        except (ValueError, TypeError) as exc:
            raise ErrorLexer(f'Formato inválido del lexer: {linea_salida!r}') from exc
    return tokens


def procesar_codigo(codigo):
    salida = Resultado(tokens=tokenizar(codigo))
    salida.errores_lexicos = [t for t in salida.tokens if t[0] == 'ERROR_LEXICO']
    if salida.errores_lexicos or not salida.tokens:
        return salida
    salida.errores_sintacticos, salida.resumen_sintactico = analizar_programa(salida.tokens)
    if salida.errores_sintacticos:
        return salida
    salida.semantica = analizar_semantica_completo(salida.tokens)
    if salida.semantica['errores']:
        return salida
    try:
        salida.intermedio = generar_intermedio(salida.tokens)
        salida.intermedio_texto = formatear_intermedio(salida.intermedio)
    except ErrorIntermedio as exc:
        salida.error_intermedio = str(exc)
    try:
        salida.javascript = traducir_tokens(salida.tokens)
    except ErrorTraduccion as exc:
        salida.error_traduccion = str(exc)
    return salida
