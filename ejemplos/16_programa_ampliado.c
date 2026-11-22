// Demostración del mini-C ampliado - cuatro fases
int duplicar(int numero) {
    return numero * 2;
}

double calcularPromedio(double a, double b) {
    return (a + b) / 2;
}

int main(void) {
    char nombre[] = "Maria";
    char inicial = 'M';
    float asistencia = 90.5;
    double nota1 = 88.5;
    double nota2 = 95.5;
    double promedio = calcularPromedio(nota1, nota2);
    bool aprobada = promedio >= 70 && asistencia >= 80;

    print("Estudiante:", nombre);
    print("Inicial:", inicial);
    print("Promedio:", promedio);

    if (aprobada && !false) {
        print("Resultado: Aprobada");
    } else {
        print("Resultado: Reprobada");
    }

    int total = 0;
    for (int i = 1; i <= 3; i++) {
        total = total + duplicar(i);
    }
    total--;
    print("Total:", total);
    print("Resto:", total % 3);
    print("Primera letra:", nombre[0]);
    return 0;
}
