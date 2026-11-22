    contador = 0
    promedio = 0.0

func sumar(a, b):
    t1 = a + b
    return t1
endfunc

    param 3
    param 4
    t2 = call sumar, 2
    contador = t2
    t3 = (float) contador
    t4 = t3 + 2.5
    promedio = t4
    print "Resultado", promedio
