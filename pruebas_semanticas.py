"""pruebas_semanticas.py - Pruebas automaticas del analizador semantico.

Ejecutar:  python pruebas_semanticas.py
No necesita Flex ni el .exe: incluye un tokenizador equivalente a lexer.l SOLO para
poder probar de forma portatil (la GUI sigue usando el lexer real en C).
Cada caso indica los tipos de error esperados ([] = programa correcto).
"""
import re
from sintactico import analizar_programa
from semantico import analizar_semantica_completo

KW = {"if", "else", "while", "for", "int", "float", "return", "void", "print"}
SPEC = [("WS", r"[ \t\r]+"), ("NL", r"\n"), ("LC", r"//.*"), ("BC", r"/\*([^*]|\*+[^*/])*\*+/"),
        ("CADENA", r'"[^"\n]*"'), ("NUMERO_DECIMAL", r"\d+\.\d+"), ("NUMERO_ENTERO", r"\d+"),
        ("ID", r"[A-Za-z_]\w*"), ("OP_RELACIONAL", r"==|!=|<=|>=|<|>"), ("OP_ASIGNACION", r"="),
        ("OP_ARITMETICO", r"[+\-*/]"), ("PUNTO_COMA", r";"), ("COMA", r","), ("PAR_IZQ", r"\("),
        ("PAR_DER", r"\)"), ("LLAVE_IZQ", r"\{"), ("LLAVE_DER", r"\}"), ("ERROR_LEXICO", r".")]
RX = re.compile("|".join(f"(?P<{n}>{p})" for n, p in SPEC))


def tokenizar(src):
    toks, ln, col = [], 1, 1
    for m in RX.finditer(src):
        k, t, c = m.lastgroup, m.group(), col
        if k == "NL":
            ln += 1; col = 1; continue
        if k == "BC":
            if "\n" in t:
                ln += t.count("\n"); col = len(t.split("\n")[-1]) + 1
            else:
                col += len(t)
            continue
        col += len(t)
        if k in ("WS", "LC"):
            continue
        if k == "ID":
            k = "PALABRA_RESERVADA" if t in KW else "IDENTIFICADOR"
        toks.append((k, t, ln, c))
    return toks


def analizar(src):
    toks = tokenizar(src)
    assert not any(t[0] == "ERROR_LEXICO" for t in toks), "error lexico en el caso de prueba"
    errs, _ = analizar_programa(toks)
    assert not errs, f"error sintactico en el caso de prueba: {errs[0]}"
    return analizar_semantica_completo(toks)


CASOS = [
 # (nombre, codigo, errores_esperados, advertencias_esperadas)
 ("programa correcto", "int c;\nfloat p;\nint s(int a,int b){return a+b;}\nc=s(3,4);\np=c+2.5;\nprint(\"R\",p);", [], []),
 ("variable no declarada", "int c;\nr = c + 1;", ["Variable no declarada"], []),
 ("float a int", "int c;\nc = 3.5;", ["Tipos incompatibles"], []),
 ("init float a int", "int x = 2.5;", ["Tipos incompatibles"], []),
 ("int a float (permitido)", "float f;\nf = 3;", [], []),
 ("identificador duplicado", "int t;\nint t;", ["Identificador duplicado"], []),
 ("parametro duplicado", "int f(int a, int a){ return a; }", ["Identificador duplicado"], []),
 ("local repite parametro", "int f(int a){ int a; return a; }", ["Identificador duplicado"], []),
 ("sombreado valido", "int x;\nint f(int a){ int x; x = a; return x; }", [], []),
 ("fuera de ambito (if)", "if (1) { int t; t = 2; }\nt = 5;", ["Variable no declarada"], []),
 ("variable de for fuera del for", "for (int i = 0; i < 3; i = i + 1) { print(i); }\nprint(i);", ["Variable no declarada"], []),
 ("argumento incompatible", "int s(int a,int b){return a+b;}\nint r;\nr = s(1.5, 2);", ["Tipo de argumento incompatible"], []),
 ("cantidad de argumentos", "void f(int a){ a = a + 1; }\nf(1, 2);", ["Cantidad de argumentos incorrecta"], []),
 ("funcion inexistente", "int x;\nx = g(1);", ["Funcion no declarada"], []),
 ("variable llamada como funcion", "int x;\nx(3);", ["Funcion no declarada"], []),
 ("funcion usada como variable", "int f(void){return 1;}\nint y;\ny = f + 1;", ["Variable no declarada"], []),
 ("funcion duplicada", "int f(void){return 1;}\nint f(void){return 2;}", ["Funcion duplicada"], []),
 ("llamada antes de definir", "int x;\nx = g(1);\nint g(int a){ return a; }", [], []),
 ("recursion", "int fact(int n){ if (n<=1) { return 1; } return n*fact(n-1); }", [], []),
 ("void en expresion", "void f(void){ return; }\nint x;\nx = f();", ["Tipos incompatibles"], []),
 ("return incompatible", "int c(void){ return 3.5; }", ["Retorno incompatible"], []),
 ("return con valor en void", "void c(void){ return 1; }", ["Retorno incompatible"], []),
 ("return faltante", "int c(int x){ x = x + 1; }", ["Retorno faltante"], []),
 ("return solo dentro de if (NUEVO)", "int s(int a){ if (a > 0) { return 1; } }", ["Retorno faltante"], []),
 ("return en if y else (NUEVO)", "int s(int a){ if (a > 0) { return 1; } else { return 2; } }", [], []),
 ("return fuera de funcion", "return 1;", ["Return fuera de funcion"], []),
 ("cadena en aritmetica", "int x;\nx = \"hola\" + 1;", ["Operacion incompatible"], []),
 ("condicion con cadena", "if (\"a\") { print(1); }", ["Condicion incompatible"], []),
 ("division entre cero (NUEVO)", "int x;\nx = 5 / 0;", ["Division entre cero"], []),
 ("division normal", "int x;\nx = 5 / 2;", [], []),
 ("local sin inicializar (NUEVO)", "int f(void){ int a; int b; b = a + 1; return b; }", [], ["Variable sin inicializar"]),
 ("local inicializada", "int f(void){ int a = 1; int b; b = a + 1; return b; }", [], []),
 ("global sin inicializar (C la pone en 0)", "int a;\nint b;\nb = a + 1;", [], []),
 ("llamada como sentencia cuenta 1", "void f(void){ return; }\nf();", [], []),
]


def main():
    fallos = 0
    for nombre, src, esp_e, esp_w in CASOS:
        r = analizar(src)
        got_e = [e.tipo for e in r["errores"]]
        got_w = [w.tipo for w in r["advertencias"]]
        ok = got_e == esp_e and got_w == esp_w
        if nombre.startswith("llamada como sentencia"):
            ok = ok and r["resumen"]["llamadas"] == 1
        print(("OK    " if ok else "FALLA ") + nombre)
        if not ok:
            fallos += 1
            print("      esperado:", esp_e, esp_w, " obtenido:", got_e, got_w)
    print(f"\n{len(CASOS) - fallos}/{len(CASOS)} pruebas correctas")
    return fallos


if __name__ == "__main__":
    raise SystemExit(main())
