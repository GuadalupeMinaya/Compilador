/* =========================================================
   lexer.l - Gramatica Flex de referencia para el mini-C ampliado
   =========================================================
*/

%{
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* Contador de linea y columna, usados para reportar la posicion
   exacta de cada token (util para depurar y para la GUI). */
int num_linea = 1;
int num_columna = 1;
int col_inicio = 1;

/* YY_USER_ACTION se ejecuta automaticamente ANTES de la accion de
   cada regla que hace match. Aqui la usamos para calcular en que
   columna EMPIEZA el token actual, antes de avanzar el contador. */
#define YY_USER_ACTION { col_inicio = num_columna; num_columna += yyleng; }

/* Funcion auxiliar: imprime el token en un formato fijo
   TIPO|LEXEMA|LINEA|COLUMNA  que luego la interfaz grafica en
   Python leera facilmente linea por linea. */
void emitir(const char *tipo, const char *lexema) {
    printf("%s|%s|%d|%d\n", tipo, lexema, num_linea, col_inicio);
}
%}

/* ---------- Definiciones (macros de expresiones regulares) ---------- */
DIGITO      [0-9]
LETRA       [a-zA-Z_]
ENTERO      {DIGITO}+
DECIMAL     {DIGITO}+"."{DIGITO}+
ID          {LETRA}({LETRA}|{DIGITO})*

%%
 /* ---------- Reglas: PATRON { ACCION } ---------- */

"if"|"else"|"while"|"for"|"int"|"float"|"double"|"char"|"bool"|"true"|"false"|"return"|"void"|"print" {
    emitir("PALABRA_RESERVADA", yytext);
}

{DECIMAL} { emitir("NUMERO_DECIMAL", yytext); }
\'([^'\n\\]|\\.)\' { emitir("CARACTER", yytext); }
{ENTERO}  { emitir("NUMERO_ENTERO", yytext);  }
{ID}      { emitir("IDENTIFICADOR", yytext);  }

\"([^\"\n\\]|\\.)*\" { emitir("CADENA", yytext); }

"=="|"!="|"<="|">=" { emitir("OP_RELACIONAL", yytext); }
"&&"|"||"|"!" { emitir("OP_LOGICO", yytext); }
"++"|"--" { emitir("OP_INCREMENTO", yytext); }
"<"|">"             { emitir("OP_RELACIONAL", yytext); }
"="                 { emitir("OP_ASIGNACION", yytext); }
"+"|"-"|"*"|"/"|"%" { emitir("OP_ARITMETICO", yytext); }
"[" { emitir("CORCHETE_IZQ", yytext); }
"]" { emitir("CORCHETE_DER", yytext); }

";" { emitir("PUNTO_COMA", yytext); }
","  { emitir("COMA", yytext); }
"(" { emitir("PAR_IZQ", yytext); }
")" { emitir("PAR_DER", yytext); }
"{" { emitir("LLAVE_IZQ", yytext); }
"}" { emitir("LLAVE_DER", yytext); }

"//".*                { /* comentario de linea: se ignora */ }
"/*"([^*]|\*+[^*/])*\*+"/" {
    /* comentario de bloque: puede abarcar varias lineas.
       Recalculamos linea y columna recorriendo el texto capturado. */
    int columna_tras_salto = 0;
    int hubo_salto = 0;
    for (int i = 0; yytext[i]; i++) {
        if (yytext[i] == '\n') { num_linea++; hubo_salto = 1; columna_tras_salto = 0; }
        else columna_tras_salto++;
    }
    if (hubo_salto) num_columna = columna_tras_salto + 1;
}

\n { num_linea++; num_columna = 1; }
[ \t\r]+ { /* espacios en blanco: se ignoran */ }

 /* Caracter especial de varios bytes (tildes, enye, simbolos Unicode, etc.)
    Se agrupa como UN SOLO error, en vez de reportar cada byte por separado. */
[\xC0-\xFF][\x80-\xBF]* { emitir("ERROR_LEXICO", yytext); }

. { emitir("ERROR_LEXICO", yytext); }

%%

int yywrap(void) { return 1; }

int main(int argc, char **argv) {
    if (argc > 1) {
        FILE *f = fopen(argv[1], "r");
        if (!f) { fprintf(stderr, "No se pudo abrir %s\n", argv[1]); return 1; }
        yyin = f;
    }
    yylex();
    return 0;
}
