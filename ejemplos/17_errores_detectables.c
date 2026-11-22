// Ejemplo de errores semanticos (no produce JavaScript)
int main(void) {
    char texto[3] = "Hola";  // faltan posiciones (incluye NUL)
    int entero = 3.5;       // valor decimal no compatible con int
    return 0;
}
