function __mini_mod(a, b) {
    if (b === 0) { throw new Error('Módulo entre cero'); }
    return a % b;
}

function duplicar(numero) {
    return Math.imul(numero, 2);
}
function calcularPromedio(a, b) {
    return (a + b) / 2;
}
function main() {
    let nombre = "Maria";
    let inicial = 'M';
    let asistencia = 90.5;
    let nota1 = 88.5;
    let nota2 = 95.5;
    let promedio = calcularPromedio(nota1, nota2);
    let aprobada = Boolean(promedio >= 70 && asistencia >= 80);
    console.log("Estudiante:", nombre);
    console.log("Inicial:", inicial);
    console.log("Promedio:", promedio);
    if (Boolean(aprobada && !false)) {
        console.log("Resultado: Aprobada");
    } else {
        console.log("Resultado: Reprobada");
    }
    let total = 0;
    for (let i = 1; i <= 3; i++) {
        total = total + duplicar(i) | 0;
    }
    total--;
    console.log("Total:", total);
    console.log("Resto:", __mini_mod(total, 3));
    console.log("Primera letra:", nombre[0]);
    return 0;
}

main();
