"""Analizador lexico equivalente, portatil para Windows sin compilador C.
En Linux/macOS el motor usa lexico_extendido.c (fase 1 en C).
"""
import re

RESERVADAS = set("if else while for int float double char bool true false return void print".split())
# El orden es importante: primero operadores y literales de mayor longitud.
PATRONES = [
    ('COMENTARIO_BLOQUE', r'/\*[\s\S]*?\*/'),
    ('COMENTARIO_LINEA', r'//[^\n]*'),
    ('ESPACIO', r'[ \t\r\n]+'),
    ('CADENA', r'"(?:[^"\\\n]|\\.)*"'),
    ('CARACTER', r"'(?:[^'\\\n]|\\.)'"),
    ('NUMERO_DECIMAL', r'[0-9]+\.[0-9]+'),
    ('NUMERO_ENTERO', r'[0-9]+'),
    ('IDENTIFICADOR', r'[A-Za-z_][A-Za-z_0-9]*'),
    ('OP_RELACIONAL', r'==|!=|<=|>=|<|>'),
    ('OP_LOGICO', r'&&|\|\||!'),
    ('OP_INCREMENTO', r'\+\+|--'),
    ('OP_ASIGNACION', r'='),
    ('OP_ARITMETICO', r'[+\-*/%]'),
    ('PUNTO_COMA', r';'), ('COMA', r','),
    ('PAR_IZQ', r'\('), ('PAR_DER', r'\)'),
    ('LLAVE_IZQ', r'\{'), ('LLAVE_DER', r'\}'),
    ('CORCHETE_IZQ', r'\['), ('CORCHETE_DER', r'\]'),
    ('ERROR_LEXICO', r'[^\s]'),
]
RX = re.compile('|'.join(f'(?P<{tipo}>{patron})' for tipo, patron in PATRONES))


def tokenizar(codigo):
    tokens = []
    linea, columna = 1, 1
    indice = 0
    while indice < len(codigo):
        match = RX.match(codigo, indice)
        if not match:
            # Mantiene la progresion ante cualquier caracter no reconocido.
            match = re.match(r'.', codigo[indice:])
            if not match:
                indice += 1
                continue
            lexema, tipo = match.group(), 'ERROR_LEXICO'
        else:
            lexema, tipo = match.group(), match.lastgroup
        if tipo not in {'COMENTARIO_BLOQUE', 'COMENTARIO_LINEA', 'ESPACIO'}:
            if tipo == 'IDENTIFICADOR' and lexema in RESERVADAS:
                tipo = 'PALABRA_RESERVADA'
            tokens.append((tipo, lexema, linea, columna))
        if '\n' in lexema:
            linea += lexema.count('\n')
            columna = len(lexema.rsplit('\n', 1)[-1]) + 1
        else:
            columna += len(lexema)
        indice += len(lexema)
    return tokens
