function cuadrado(n) {
    return Math.imul(n, n);
}
function mitad(numero) {
    return numero / 2.0;
}
function main() {
    let n = 5;
    let promedio = mitad(9);
    console.log("Numero:", n);
    console.log("Cuadrado:", cuadrado(n));
    console.log("Mitad:", promedio);
    if (n > 3) {
        console.log("Es mayor que 3");
    } else {
        console.log("Es 3 o menor");
    }
    for (let i = 0; i < 3; i = i + 1 | 0) {
        console.log("Iteracion", i);
    }
    return 0;
}

main();
