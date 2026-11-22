function promedio(a, b) {
    let r;
    r = (a + b | 0) / 2.0;
    return r;
}
function abs(n) {
    if (n < 0) {
        return -n;
    } else {
        return n;
    }
}
let i = 0;
let p = 0;
p = promedio(4, 7);
for (i = 0; i < 3; i = i + 1 | 0) {
    console.log("i =", abs(i - 5 | 0));
}
console.log("promedio", p);
