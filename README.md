# Compilador mini-C ampliado — todas las etapas integradas

Proyecto educativo de compiladores que **analiza (léxico, sintaxis, semántica), genera la tabla de símbolos y el código intermedio de tres direcciones, traduce a JavaScript y ejecuta el código traducido**, todo en una sola aplicación. Conserva el proyecto original y amplía su gramática con tipos y operadores útiles. Se traduce un **subconjunto de C**, no todo C.

## Iniciar la interfaz en Windows

1. **Descomprime todo el ZIP**. No ejecutes archivos dentro del ZIP.
2. Instala **Python 3** (con `tkinter`, normalmente incluido en Windows).
3. Para analizar y traducir: doble clic en `INICIAR_EN_WINDOWS.bat` o ejecutar `py gui.py`.
4. Para **Probar traducción** y ver la salida, instala **Node.js**, disponible en https://nodejs.org, y comprueba `node --version`.
5. Pega o abre `ejemplos/16_programa_ampliado.c` (el cuadro de **Abrir archivo** acepta `.txt` y `.c`), pulsa **Analizar código**, recorre las pestañas **Intermedio** y **Símbolos**, entra en **Traducción JS** y pulsa **Ejecutar**.

**La aplicación de Windows no necesita compilar archivos C**: usa `lexico_portable.py`, compatible con la gramática ampliada. En Linux/macOS, el motor usa `lexico_extendido.c` compilado automáticamente con GCC; si no hay compilador, pasa al lexer portátil. `lexer.l` conserva las reglas Flex como referencia y `lexer_original_no_usar/` conserva artefactos originales sin usar.

## Línea de comandos

```bash
python traducir.py ejemplos/16_programa_ampliado.c -o resultado.js --intermedio resultado.tac --simbolos
node resultado.js
```

## Comprobación automática

```bash
python pruebas_semanticas.py
python -m unittest -v pruebas_traduccion.py pruebas_diagnosticos.py pruebas_ampliacion.py pruebas_intermedio.py
```

## Archivos principales

- `lexer.l` (reglas Flex de referencia), `lexico_extendido.c`, `lexico_portable.py`: fase 1, léxico.
- `sintactico.py`: fase 2, sintaxis.
- `semantico.py`: fase 3, tipos, ámbitos, funciones y errores; genera la **tabla de símbolos**.
- `intermedio.py`: **código intermedio** de tres direcciones (cuádruplas), con etiquetas, saltos, `param`/`call` y conversiones explícitas.
- `traductor.py`: fase 4, generación de JavaScript.
- `motor.py`: ejecución integrada de todas las etapas.
- `gui.py`: interfaz con una pestaña por etapa (léxico, sintáctico, semántico, símbolos, intermedio, traducción JS), ejecución y exportación.
- `diagnosticos.py`: ejecución controlada con Node.js y ayuda ante errores.
- `ejemplos/`: casos de demostración y errores esperados. `ejemplos_intermedio/` y `ejemplos_js/` contienen el código intermedio y el JavaScript generados.
- `DOCUMENTACION_LENGUAJE.md` / `.docx`: alcance, instrucciones y gramática.

## Nota técnica importante

`char letra = 'A';` guarda un carácter. Las **cadenas de texto en C se almacenan en arreglos de caracteres**, como `char nombre[] = "Ana";`. Ni `string` ni `decimal` son tipos incorporados de C y **no** forman parte de este mini-C. `float` y `double` sí se admiten, pero su traducción a `Number` de JavaScript es una aproximación numérica, no un modelo exacto del redondeo IEEE-754 de cada tipo C. `bool`, `true` y `false` se admiten directamente como comodidad educativa; en C anterior a C23 normalmente se utiliza `<stdbool.h>`. `print` es una extensión del mini-lenguaje, no una función estándar de C. Más detalles en `DOCUMENTACION_LENGUAJE.md`.
