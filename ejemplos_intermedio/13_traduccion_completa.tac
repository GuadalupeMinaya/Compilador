func cuadrado(n):
    t1 = n * n
    return t1
endfunc

func mitad(numero):
    t2 = numero / 2.0
    return t2
endfunc

func main():
    n = 5
    param 9.0
    t3 = call mitad, 1
    promedio = t3
    print "Numero:", n
    param n
    t4 = call cuadrado, 1
    print "Cuadrado:", t4
    print "Mitad:", promedio
    t5 = n > 3
    ifFalse t5 goto L1
    print "Es mayor que 3"
    goto L2
L1:
    print "Es 3 o menor"
L2:
    i = 0
L3:
    t6 = i < 3
    ifFalse t6 goto L4
    print "Iteracion", i
    t7 = i + 1
    i = t7
    goto L3
L4:
    return 0
endfunc

    call main, 0
