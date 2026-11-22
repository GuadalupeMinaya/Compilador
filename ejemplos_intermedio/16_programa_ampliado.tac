func duplicar(numero):
    t1 = numero * 2
    return t1
endfunc

func calcularPromedio(a, b):
    t2 = a + b
    t3 = t2 / 2.0
    return t3
endfunc

func main():
    nombre = "Maria"
    inicial = 'M'
    asistencia = 90.5
    nota1 = 88.5
    nota2 = 95.5
    param nota1
    param nota2
    t4 = call calcularPromedio, 2
    promedio = t4
    t5 = promedio >= 70
    ifFalse t5 goto L1
    t6 = asistencia >= 80
    ifFalse t6 goto L1
    t7 = true
    goto L2
L1:
    t7 = false
L2:
    aprobada = t7
    print "Estudiante:", nombre
    print "Inicial:", inicial
    print "Promedio:", promedio
    ifFalse aprobada goto L3
    t8 = !false
    ifFalse t8 goto L3
    t9 = true
    goto L4
L3:
    t9 = false
L4:
    ifFalse t9 goto L5
    print "Resultado: Aprobada"
    goto L6
L5:
    print "Resultado: Reprobada"
L6:
    total = 0
    i = 1
L7:
    t10 = i <= 3
    ifFalse t10 goto L8
    param i
    t12 = call duplicar, 1
    t13 = total + t12
    total = t13
    t11 = i + 1
    i = t11
    goto L7
L8:
    t14 = total - 1
    total = t14
    print "Total:", total
    t15 = total % 3
    print "Resto:", t15
    t16 = nombre[0]
    print "Primera letra:", t16
    return 0
endfunc

    call main, 0
