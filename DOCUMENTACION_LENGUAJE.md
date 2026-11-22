# Documentación técnica — Compilador mini-C ampliado

**Versión de entrega:** compilador completo en una sola aplicación: análisis léxico, sintáctico y semántico, tabla de símbolos, generación de código intermedio (tres direcciones), traducción a JavaScript y ejecución con Node.js. Proyecto educativo, no implementación total del lenguaje C.

## 1. Objetivo y solución

El usuario escribe un programa mini-C. El **léxico** produce tokens con clase, lexema, línea y columna. El **sintáctico** valida las estructuras gramaticales; el **semántico** verifica declaraciones, ámbitos, tipos, llamadas, parámetros y retornos, y construye la **tabla de símbolos**. Solo un programa que supera esas tres etapas pasa al **generador de código intermedio** (código de tres direcciones) y al **traductor**, que produce JavaScript; la GUI permite guardar los resultados o ejecutar el JavaScript con Node.js. Todas las etapas se llaman desde `motor.py`.

**Diagrama:** `código mini-C → tokens → sintaxis → semántica + tabla de símbolos → código intermedio → traductor JS → Node.js`.

| Requisito del ejercicio | Dónde está |
|---|---|
| Analizador léxico | `lexico_portable.py`, `lexico_extendido.c`, `lexer.l` |
| Analizador sintáctico | `sintactico.py` |
| Analizador semántico | `semantico.py` |
| Tabla de símbolos | `semantico.py` (se genera) · pestaña «Símbolos» · opción `--simbolos` |
| Código intermedio | `intermedio.py` · pestaña «Intermedio» · opción `--intermedio` |
| Lenguaje destino de la traducción | JavaScript (`traductor.py`) |
| Todo en una sola aplicación | `motor.py` y `gui.py` |

## 2. Tipos soportados

| Tipo | Ejemplo | Observación |
|---|---|---|
| `int` | `int edad = 22;` | Enteros aproximados a 32 bits en JS |
| `float` | `float peso = 72.5;` | Valor numérico, semántica de tipo diferenciada |
| `double` | `double promedio = 92.75;` | Tipo numérico de mayor precisión conceptual |
| `char` | `char letra = 'A';` | Un carácter; también `\n` y otros escapes |
| `char[]` | `char nombre[] = "Ana";` | Arreglo de caracteres utilizado para texto |
| `bool` | `bool listo = true;` | Comodidad del dialecto educativo |
| `void` | `void saludar(void) { print("Hola"); }` | Retorno de función sin valor |

**No se admiten `string` ni `decimal` como tipos declarables.** En C estándar, los textos se representan habitualmente con arreglos de `char` o punteros `char*`; este proyecto implementa solo la primera alternativa y operaciones básicas sobre ella. `decimal` no es un tipo primitivo de C. Mantener `float` y `double` evita agregar un tipo inventado.

## 3. Estructuras implementadas

- Declaraciones simples, inicializaciones y asignaciones; varios identificadores separados por comas.
- Funciones, parámetros, argumentos y `return`, incluida `main(void)`.
- Condiciones `if/else`, bucles `while` y `for`, y bloques `{...}`.
- Operadores `+`, `-`, `*`, `/`, `%` (solo enteros), `==`, `!=`, `<`, `>`, `<=`, `>=`.
- Operadores lógicos `&&`, `||`, `!`, con precedencia y cortocircuito.
- `i++` e `i--` como instrucciones y en las secciones del ciclo `for`.
- Textos `char nombre[] = "Ana";` y `char nombre[10] = "Ana";`, acceso de lectura `nombre[0]`.
- Impresión de valores y textos: `print("Hola", nombre, edad);`.
- Comentarios de línea (`//`) y bloque (`/* ... */`).

Las conversiones semánticas seguras admitidas son `int → float`, `int → double`, `float → double`. La asignación de tipos incompatibles es un error. El analizador detecta desbordamiento de capacidad al inicializar `char[]` con cadenas literales, contando la posición final `\0` requerida por C.

## 4. Ejemplo completo

```c
int main(void) {
    char nombre[] = "Maria";
    char inicial = 'M';
    double promedio = 92.75;
    bool aprobo = promedio >= 70;
    print("Estudiante:", nombre);
    print("Inicial:", inicial);
    if (aprobo && !false) {
        print("Aprobada con", promedio);
    }
    for (int i = 0; i < 3; i++) {
        print("Iteracion", i);
    }
    return 0;
}
```

Resultado esperado: nombre e inicial, nota, condición y las iteraciones 0, 1 y 2. El código traducido llama a `console.log()` para imprimir y a la función `main()` al finalizar, si está definida.

## 5. Tabla de símbolos

El análisis semántico registra cada símbolo con su nombre, clase, tipo, ámbito y línea de declaración. La interfaz la muestra en la pestaña **Símbolos** (doble clic en una fila lleva a la línea del editor) y la consola con `--simbolos`.

| Columna | Contenido |
|---|---|
| Nombre | Identificador declarado |
| Clase | `funcion`, `parametro` o `variable` |
| Tipo | `int`, `float`, `double`, `char`, `char[]`, `bool` o el tipo de retorno de la función |
| Ámbito | `global`, `funcion nombre` o `for (linea N)` |
| Línea | Línea de la declaración |
| Detalle | Para funciones, los tipos de sus parámetros, por ejemplo `(double, double)` |

## 6. Código intermedio (tres direcciones)

Después del análisis semántico se genera un código de tres direcciones: cada instrucción tiene como máximo un operador y tres direcciones, y los valores intermedios se guardan en temporales (`t1`, `t2`, ...). El flujo de control se expresa con etiquetas (`L1`, `L2`, ...) y saltos. La pestaña **Intermedio** lo muestra como texto y como tabla de cuádruplas (operador, argumento 1, argumento 2, resultado); se puede copiar o guardar como `.tac`.

| Instrucción | Significado |
|---|---|
| `x = y` | Asignación |
| `t = a op b` | Operación binaria: `+ - * / %` y comparaciones `< > <= >= == !=` |
| `t = -a`, `t = !a` | Operaciones unarias |
| `t = (float) a` | Conversión explícita de `int` a `float`/`double` |
| `t = a[i]` | Lectura de una posición de `char[]` |
| `L:` · `goto L` | Etiqueta y salto incondicional |
| `ifFalse a goto L` · `ifTrue a goto L` | Saltos condicionales |
| `param a` · `t = call f, n` · `call f, n` | Paso de argumentos y llamada con `n` argumentos |
| `return a` · `return` | Retorno de función |
| `print a, b` | Impresión (extensión del mini-lenguaje) |
| `func f(a, b):` · `endfunc` | Inicio y fin de una función |

Reglas de la generación: `&&` y `||` se traducen con saltos (cortocircuito) y dejan `true` o `false` en un temporal; `i++` e `i--` se convierten en `i + 1` o `i - 1`; en un `for`, el paso se ejecuta después del cuerpo; una variable que oculta a otra visible recibe un nombre distinto en el código (por ejemplo `x_1`); si el programa define `main` y no la llama, se agrega `call main, 0` al final.

Programa de ejemplo:

```c
int main(void) {
    int total = 0;
    for (int i = 1; i <= 3; i++) {
        total = total + i;
    }
    print("Total:", total);
    return 0;
}
```

Código intermedio generado:

```
func main():
    total = 0
    i = 1
L1:
    t1 = i <= 3
    ifFalse t1 goto L2
    t3 = total + i
    total = t3
    t2 = i + 1
    i = t2
    goto L1
L2:
    print "Total:", total
    return 0
endfunc

    call main, 0
```

La salida de este programa es `Total: 6`, tanto al ejecutar el JavaScript traducido como al ejecutar el código intermedio con el intérprete de pruebas.

## 7. Ejecución, instalación y pruebas

**Windows:** extraer ZIP → abrir `INICIAR_EN_WINDOWS.bat` → analizar el ejemplo → pestaña «Traducción JS» → botón «Probar traducción». Requiere Python 3; para ejecutar JS requiere Node.js. El lexer portátil funciona sin GCC. **Linux/macOS:** `python gui.py` utiliza `lexico_extendido.c` si GCC está disponible o el lexer Python como respaldo.

**Consola:** `python traducir.py ejemplos/16_programa_ampliado.c -o salida.js --intermedio salida.tac --simbolos` y después `node salida.js`. Sin `--intermedio` ni `--simbolos` solo se genera el JavaScript.

**Pruebas:** `python pruebas_semanticas.py` y `python -m unittest -v pruebas_traduccion.py pruebas_diagnosticos.py pruebas_ampliacion.py pruebas_intermedio.py`. Incluyen traducción real, ejecución y errores negativos. `pruebas_intermedio.py` ejecuta el código intermedio con un pequeño intérprete de cuádruplas y comprueba que su salida coincide con la del JavaScript traducido en más de veinte programas.

## 8. Arquitectura y archivos

- **Fase 1:** `lexer.l` (reglas Flex de referencia), `lexico_extendido.c` (ejecutable C99), `lexico_portable.py` (Windows y respaldo).
- **Fase 2:** `sintactico.py` (parser recursivo con recuperación de errores).
- **Fase 3:** `semantico.py` (ámbitos, tabla de símbolos, verificación de tipos y retornos).
- **Código intermedio:** `intermedio.py` (generador de código de tres direcciones).
- **Fase 4:** `traductor.py` (generador estructurado a JS).
- **Integración:** `motor.py` y `gui.py`; **ejecución:** `diagnosticos.py` (proceso Node con límite de tiempo).
- **Ejemplos:** `ejemplos/` (entradas), `ejemplos_intermedio/` (código intermedio generado) y `ejemplos_js/` (JavaScript generado).

Los ejecutables y el código generado de la implementación anterior se conservan en `lexer_original_no_usar/`, pero no deben usarse para analizar el nuevo lenguaje.

## 9. Limitaciones declaradas

1. **No compila todo C.** No admite punteros, `malloc`, `struct`, bibliotecas estándar, directivas `#include`, `printf`, `scanf`, macros, `switch`, `do...while` ni arreglos numéricos.
2. `bool` y `print` son comodidades educativas. En C99–C17, `bool` requiere normalmente `#include <stdbool.h>`; el mini-C lo permite sin esa directiva.
3. `char[]` sirve para imprimir y leer posiciones mediante `[]`; **no** permite asignaciones posteriores al arreglo completo, escritura `nombre[i]='x'` ni manejo completo de memoria/terminador nulo.
4. `float` y `double` se conservan como tipos en semántica, pero ambos usan `Number` de JS durante la ejecución; no hay diferencias exactas de redondeo C entre ambos. Las constantes con punto se tratan como `float` por compatibilidad con la versión inicial del proyecto, a diferencia del C estándar donde suelen ser `double`.
5. Solo están implementadas conversiones numéricas ascendentes sencillas; no se cubren conversiones explícitas ni todas las coerciones implícitas de C.
6. `++`/`--` están admitidos como sentencias y en `for`, no como subexpresiones. `%` exige enteros. La división/módulo entre cero se detectan cuando es posible y en ejecución para operaciones enteras.
7. Las entradas interactivas del usuario (`scanf`) no se contemplan. Se utiliza `print()` para mostrar salidas.
8. El programa necesita Python 3 y Node.js para ejecutar el JS traducido; analizar/traducir no requiere Node.js. El ejecutable de Windows (`CompiladorMiniC_JS.exe`) se genera con `build_exe.bat` (PyInstaller); el ejecutable incluye Python, pero no Node.js.
9. El código intermedio y el JavaScript se generan por separado a partir de los mismos tokens ya validados: el JavaScript no se produce desde el código intermedio. El código intermedio no se optimiza (no hay propagación de constantes ni eliminación de código muerto) y no se ejecuta dentro de la aplicación; se comprueba con el intérprete de `pruebas_intermedio.py`.

## 10. Entrega a UTESA

Comprimir y subir **la carpeta completa** sin eliminar `motor.py`, el lexer, las fases, la GUI, los ejemplos, las pruebas y los documentos. Para defender el ejercicio 1, mostrar un programa válido, las pestañas de cada fase (léxico, sintáctico, semántico, símbolos, intermedio), el JS generado y su ejecución con Node.js; después, un programa con errores para ver cómo se bloquea la traducción. La entrega en `nube.utesa` corresponde al estudiante.
