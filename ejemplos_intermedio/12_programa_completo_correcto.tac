func promedio(a, b):
    t1 = a + b
    t2 = (float) t1
    t3 = t2 / 2.0
    r = t3
    return r
endfunc

func abs(n):
    t4 = n < 0
    ifFalse t4 goto L1
    t5 = -n
    return t5
    goto L2
L1:
    return n
L2:
endfunc

    i = 0
    p = 0.0
    param 4
    param 7
    t6 = call promedio, 2
    p = t6
    i = 0
L3:
    t7 = i < 3
    ifFalse t7 goto L4
    t9 = i - 5
    param t9
    t10 = call abs, 1
    print "i =", t10
    t8 = i + 1
    i = t8
    goto L3
L4:
    print "promedio", p
