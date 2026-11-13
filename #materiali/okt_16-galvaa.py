# ============================================================
# 1. TĒMA: SKAITĻU SUMMA UN SKAITĪŠANA (IF-ELSE)
# ============================================================

# 1.A variants
skaitli = [3, 8, 2, 11, 4, 7]
derigie = 0
summa = 0

for n in skaitli:
    if n > 5:
        summa = summa + n
        derigie = derigie + 1
    else:
        summa = summa - 1

print(summa)
print(derigie)














# 1.B variants
vertibas = [10, 3, 6, 1, 8, 2]
derigie = 0
summa = 0

for x in vertibas:
    if x >= 5:
        summa = summa + x
        derigie = derigie + 1
    else:
        summa = summa - 2

print(summa)
print(derigie)







# ============================================================
# 2. TĒMA: KARODZIŅŠ UN SOĻU SKAITĪŠANA (BEZ BREAK)
# ============================================================

# 2.A variants
teksts = ["logs", "galds", "krēsls", "durvis"]
mekletais = "galds"
ir_atrasts = False
soli = 0

for vards in teksts:
    soli = soli + 1
    if vards == mekletais:
        ir_atrasts = True

print(ir_atrasts)
print(soli)






# 2.B variants
elementi = ["zelts", "varš", "dzelzs", "sudrabs", "alva"]
mekletais = "titāns"
ir_atrasts = False
soli = 0

for e in elementi:
    soli = soli + 1
    if e == mekletais:
        ir_atrasts = True

print(ir_atrasts)
print(soli)


# ============================================================
# 3. TĒMA: CIKLS CIKLĀ (NESTED LOOPS)
# ============================================================

# 3.A variants
skaits = 0

for rinda in range(1, 4):
    for kolonna in range(1, 3):
        if rinda == kolonna:
            skaits = skaits + 2
        else:
            skaits = skaits + 1

print(skaits)









# 3.B variants
rezultats = 0

for i in range(1, 3):
    for j in range(1, 4):
        if i < j:
            rezultats = rezultats + j
        else:
            rezultats = rezultats - 1

print(rezultats)
# 1 1 0
# 1 2 2 
# 1 3 5
# 2 1 4
# 2 2 3
# 2 3 6



# ============================================================
# 4. TĒMA
# ============================================================

# 4.A variants
vertibas = [12, 45, 7, 89, 23]
maksimums = 0

for v in vertibas:
    if v > maksimums:
        print("Atrasts jauns maksimums:", v)
        maksimums = v

print("Lielākais skaitlis ir:", maksimums)








# 4.B variants
skaitli = [50, 10, 80, 5, 30]
minimums = 100

for s in skaitli:
    if s < minimums:
        print("Atrasts jauns minimums:", s)
    minimums = s

print("Mazākais skaitlis ir:", minimums)


# ============================================================
# 5. TĒMA: CIKLA RANGE
# ============================================================

# 5.A variants
vertiba = 2

for i in range(2, 11, 3):
    if i % 2 == 0:
        vertiba = vertiba + i
    else:
        vertiba = vertiba - 1

print(vertiba)

2
5
8







# 5.B variants
vertiba = 10

for i in range(12, 3, -3):
    if i % 2 == 0:
        vertiba = vertiba - 3
    else:
        vertiba = vertiba + i

print(vertiba)

12
9
6








# ============================================================
# 6. TĒMA: ELEMENTA SALĪDZINĀŠANA AR IEPRIEKŠĒJO
# ============================================================

# 6.A variants
dati = [1, 4, 3, 7, 7, 9]
ieprieksejais = dati[0]
pieaugumi = 0

for x in dati[1:]:
    if x > ieprieksejais:
        pieaugumi = pieaugumi + 1
    ieprieksejais = x

print(pieaugumi)







# 6.B variants
dati = [15, 12, 14, 10, 10]
ieprieksejais = dati[0]
kritumi = 0

for x in dati[1:]:
    if x < ieprieksejais:
        kritumi = kritumi + 1
    ieprieksejais = x

print(kritumi)


# ============================================================
# 7. TĒMA: BREAK UN CONTINUE PLŪSMA
# ============================================================

# 7.A variants
skaitli = [4, 5, -2, 6, 1]
summa = 0
apstradati = 0

for n in skaitli:
    if n % 2 == 0 and n > 0:
        summa = summa - 1 
        continue # pārlec uz nākamo iterāciju, bet turpina
    if n < 0:
        summa = summa + 4
        apstradati = apstradati + 2
        break    # pārtrauc ciklu pavisam
    summa = summa + n
    apstradati = apstradati + 1

print(summa)
print(apstradati)


# 7.B variants
skaitli = [3, 8, 0, 10]
summa = 0
apstradati = 0

for n in skaitli:
    if n % 2 != 0:
        continue
    if n == 0:
        summa = summa - 1
        apstradati = apstradati + 1
        break
    summa = summa + n
    apstradati = apstradati + 1

print(summa)
print(apstradati)


# ============================================================
# 8. TĒMA: VIRKŅU (STRING) SIMBOLU ANALĪZE
# ============================================================

# 8.A variants
teksts = "A1 b! C"
burtu_skaits = 0
atstarpes = 0

for simbola_char in teksts:
    if simbola_char == " ":
        atstarpes = atstarpes + 1
    elif simbola_char.islower():
        burtu_skaits = burtu_skaits + 2
    elif simbola_char.isupper():
        burtu_skaits = burtu_skaits + 1

print(burtu_skaits)
print(atstarpes)


# 8.B variants
teksts = "xY7- z"
burtu_skaits = 0
atstarpes = 0

for c in teksts:
    if c == " ":
        atstarpes = atstarpes + 1
    elif c.islower():
        burtu_skaits = burtu_skaits + 2
    elif c.isupper():
        burtu_skaits = burtu_skaits + 1

print(burtu_skaits)
print(atstarpes)


# ============================================================
# 9. TĒMA: INDEKSI PRET VĒRTĪBĀM (RANGE(LEN()))
# ============================================================

# 9.A variants
skaitli = [10, 5, 2]
summa = 0

for i in range(len(skaitli)):
    if i % 2 == 0:
        summa = summa + skaitli[i]
    else:
        summa = summa - i
print(summa)








# 9.B variants
skaitli = [4, 7, 12, 1]
summa = 1   # tagad summa ir 1



for i in range(len(skaitli)):
    if i % 2 == 0:
        summa = summa + skaitli[i]
    else:
        summa = summa + i

print(summa)


# 7 % 4 = 3
# 9 % 2 = 1
# 15 % 7 = 1, jo 2x7 = 14, atlikums 1
# +
# -
# *
# /
# %
# //

# 15//7 = 2, jo 2x7 = 14, atlikums 1

# 15/7 = 2.142857142857143








# ============================================================
# 10. TĒMA: RĀDĪTĀJA KUSTĪBA UN MAIŅU LOĢIKA (SWAP/SHIFT)
# ============================================================

# 10.A variants
vertibas = [3, 1, 4, 1, 5]
parbides = 0

for i in range(len(vertibas) - 1):
    if vertibas[i] > vertibas[i + 1]:
        pagaidu = vertibas[i]
        vertibas[i] = vertibas[i + 1]
        vertibas[i + 1] = pagaidu
        parbides = parbides + 1

print(vertibas)
print(parbides)


# A    B
# C









# 10.B variants
dati = [9, 2, 8, 3]
skaits = 0

for i in range(len(dati) - 1):
    if dati[i] > dati[i + 1]:
        dati[i], dati[i + 1] = dati[i + 1], dati[i]
        skaits = skaits + 1


print(dati)
print(skaits)


# x, y = 5, 10
# x = 5
# y = 10


