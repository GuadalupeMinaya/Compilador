/* Fase 1: analizador lexico del mini-C ampliado, implementado en C99.
 * Basado en el contrato de tokens y reglas de lexer.l (Flex original).
 * No depende de Flex para compilar en Linux/macOS. En Windows sin GCC,
 * el motor utiliza la version equivalente lexico_portable.py.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>

static int reservado(const char *s) {
    const char *kw[] = {"if","else","while","for","int","float","double","char", "bool",
      "true", "false", "return", "void", "print", NULL};
    for(int i=0; kw[i]; i++) if(strcmp(s, kw[i]) == 0) return 1;
    return 0;
}
static void emitir(const char *tipo, const char *src, size_t comienzo, size_t fin, int linea, int columna) {
    printf("%s|", tipo);
    fwrite(src + comienzo, 1, fin - comienzo, stdout);
    printf("|%d|%d\n", linea, columna);
}
static void avanzar(const char *s,size_t *i,int *linea,int *columna) {
    if(s[*i] == '\n') { (*linea)++; *columna = 1; }
    else (*columna)++;
    (*i)++;
}
static char *leer_archivo(const char *ruta) {
    FILE *f = ruta ? fopen(ruta,"rb") : stdin;
    if(!f) return NULL;
    size_t cap=1024,n=0; char *buf=malloc(cap);
    if(!buf) { if(ruta) fclose(f); return NULL; }
    int c;
    while((c=fgetc(f))!=EOF) {
        if(n+2>=cap) {cap *= 2; char *tmp=realloc(buf,cap);if(!tmp){free(buf);if(ruta)fclose(f);return NULL;}buf=tmp;}
        buf[n++]=(char)c;
    }
    buf[n]=0;
    if(ruta) fclose(f);
    return buf;
}
int main(int argc,char **argv) {
    char *s=leer_archivo(argc>1 ? argv[1] : NULL);
    if(!s) { fputs("Error al leer entrada\n", stderr); return 1; }
    size_t i=0,n=strlen(s); int linea=1,columna=1;
    while(i<n) {
        size_t ini=i; int l=linea, c=columna;
        unsigned char ch=(unsigned char)s[i];
        if(isspace(ch)) { avanzar(s,&i,&linea,&columna);continue; }
        if(s[i]=='/' && i+1<n && s[i+1]=='/') {
            while(i<n && s[i]!='\n') avanzar(s,&i,&linea,&columna);
            continue;
        }
        if(s[i]=='/' && i+1<n && s[i+1]=='*') {
            avanzar(s,&i,&linea,&columna); avanzar(s,&i,&linea,&columna);
            while(i<n && !(s[i]=='*'&&i+1<n&&s[i+1]=='/')) avanzar(s,&i,&linea,&columna);
            if(i<n) {avanzar(s,&i,&linea,&columna); avanzar(s,&i,&linea,&columna);}
            else emitir("ERROR_LEXICO",s,ini,i,l,c);
            continue;
        }
        if(isalpha(ch) || ch=='_') {
            do {avanzar(s,&i,&linea,&columna);} while(i<n&&(isalnum((unsigned char)s[i])||s[i]=='_'));
            char *id=malloc(i-ini+1);
            if(!id) return 1;
            memcpy(id,s+ini,i-ini);id[i-ini]=0;
            emitir(reservado(id)?"PALABRA_RESERVADA":"IDENTIFICADOR",s,ini,i,l,c);
            free(id);continue;
        }
        if(isdigit(ch)) {
            while(i<n && isdigit((unsigned char)s[i])) avanzar(s,&i,&linea,&columna);
            const char *tipo="NUMERO_ENTERO";
            if(i+1<n && s[i]=='.' && isdigit((unsigned char)s[i+1])) {
                tipo="NUMERO_DECIMAL"; avanzar(s,&i,&linea,&columna);
                while(i<n && isdigit((unsigned char)s[i])) avanzar(s,&i,&linea,&columna);
            }
            emitir(tipo,s,ini,i,l,c);continue;
        }
        if(ch=='"'||ch=='\'') {
            unsigned char q=ch; int cerrado=0;
            avanzar(s,&i,&linea,&columna);
            while(i<n && s[i]!='\n') {
                if(s[i]=='\\' && i+1<n && s[i+1]!='\n') {
                    avanzar(s,&i,&linea,&columna); avanzar(s,&i,&linea,&columna);continue;
                }
                if((unsigned char)s[i]==q) {avanzar(s,&i,&linea,&columna);cerrado=1;break;}
                avanzar(s,&i,&linea,&columna);
            }
            const char *tipo="ERROR_LEXICO";
            if(cerrado) {
                if(q=='"') tipo="CADENA";
                else if(i-ini==3 || (i-ini==4 && s[ini+1]=='\\')) tipo="CARACTER";
            }
            emitir(tipo,s,ini,i,l,c);continue;
        }
        const char *tipo=NULL;
        if(i+1<n) {
            if((s[i]=='='&&s[i+1]=='=')||(s[i]=='!'&&s[i+1]=='=')||
               (s[i]=='<'&&s[i+1]=='=')||(s[i]=='>'&&s[i+1]=='=')) tipo="OP_RELACIONAL";
            else if((s[i]=='&'&&s[i+1]=='&')||(s[i]=='|'&&s[i+1]=='|'))tipo="OP_LOGICO";
            else if((s[i]=='+'&&s[i+1]=='+')||(s[i]=='-'&&s[i+1]=='-'))tipo="OP_INCREMENTO";
            if(tipo) {avanzar(s,&i,&linea,&columna);avanzar(s,&i,&linea,&columna); emitir(tipo,s,ini,i,l,c);continue;}
        }
        switch(s[i]) {
            case '<':case '>':tipo="OP_RELACIONAL";break;
            case '!':tipo="OP_LOGICO";break;
            case '=':tipo="OP_ASIGNACION";break;
            case '+':case '-':case '*':case '/':case '%':tipo="OP_ARITMETICO";break;
            case ';':tipo="PUNTO_COMA";break;
            case ',':tipo="COMA";break;
            case '(':tipo="PAR_IZQ";break;
            case ')':tipo="PAR_DER";break;
            case '{':tipo="LLAVE_IZQ";break;
            case '}':tipo="LLAVE_DER";break;
            case '[':tipo="CORCHETE_IZQ";break;
            case ']':tipo="CORCHETE_DER";break;
            default: tipo="ERROR_LEXICO";
        }
        avanzar(s,&i,&linea,&columna);
        emitir(tipo,s,ini,i,l,c);
    }
    free(s);return 0;
}
