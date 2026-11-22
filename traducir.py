"""CLI del compilador. Ej.: python traducir.py ejemplos/16_programa_ampliado.c -o resultado.js --intermedio resultado.tac

Ejecuta léxico, sintaxis, semántica, código intermedio y traducción a JavaScript."""
import argparse
from pathlib import Path
from motor import procesar_codigo, ErrorLexer


def main():
    cli = argparse.ArgumentParser(description='Traduce el mini-lenguaje tipo C a JavaScript')
    cli.add_argument('entrada', help='archivo .txt con código del mini-lenguaje')
    cli.add_argument('-o', '--salida', help='archivo .js generado (predeterminado: nombre de entrada .js)')
    cli.add_argument('--intermedio', metavar='ARCHIVO', help='guarda además el código intermedio (tres direcciones)')
    cli.add_argument('--simbolos', action='store_true', help='muestra la tabla de símbolos en pantalla')
    args = cli.parse_args()
    entrada = Path(args.entrada)
    destino = Path(args.salida) if args.salida else entrada.with_suffix('.js')
    try:
        r = procesar_codigo(entrada.read_text(encoding='utf-8'))
    except (OSError, UnicodeError, ErrorLexer) as e:
        cli.exit(1, f'ERROR: {e}\n')
    if r.errores_lexicos:
        for t in r.errores_lexicos:
            print(f'Error léxico, línea {t[2]}, columna {t[3]}: {t[1]!r}')
    if r.errores_sintacticos:
        for e in r.errores_sintacticos:
            print(f'Error sintáctico: {e}')
    if r.semantica.get('errores'):
        for e in r.semantica['errores']:
            print(f'Error semántico: {e}')
    if r.error_intermedio:
        print(f'Error de código intermedio: {r.error_intermedio}')
    if r.error_traduccion:
        print(f'Error de traducción: {r.error_traduccion}')
    if not r.exitoso:
        cli.exit(1, 'Traducción cancelada: corrija los errores anteriores.\n')
    for advertencia in r.semantica.get('advertencias', []):
        print(f'Advertencia: {advertencia}')
    if args.simbolos:
        print(f"{'Nombre':<20}{'Clase':<11}{'Tipo':<8}{'Ámbito':<26}{'Línea':<7}Detalle")
        for s in r.tabla_simbolos:
            print(f"{s['nombre']:<20}{s['clase']:<11}{s['tipo']:<8}{s['ambito']:<26}{s['linea']:<7}{s.get('detalle', '')}")
    try:
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(r.javascript, encoding='utf-8')
        if args.intermedio:
            ruta_ir = Path(args.intermedio)
            ruta_ir.parent.mkdir(parents=True, exist_ok=True)
            ruta_ir.write_text(r.intermedio_texto, encoding='utf-8')
    except OSError as e:
        cli.exit(1, f'No se pudo guardar el archivo: {e}\n')
    print(f'Traducción realizada: {destino} ({len(r.tokens)} tokens)')
    if args.intermedio:
        print(f'Código intermedio guardado: {args.intermedio} ({len(r.intermedio)} instrucciones)')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
