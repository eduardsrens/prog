# # ============================================================
# # 1. UZDEVUMS: FILTRS UN SKAITĪTĀJS
# # Mērķis: Iziet cauri sarakstam un saskaitīt, cik skaitļi 
# # ir pozitīvi un vienlaikus dalās ar 3 bez atlikuma.
# # ============================================================


# DOTS saraksts skaitli = [-6, 3, 0, 9, -12, 14, 18, 5]
# MAINĪGAIS skaits = 0

# KATRAM elementam x NO saraksta skaitli:
#     JA x IR LIELĀKS PAR 0 UN x DALĀS AR 3 BEZ ATLIKUMA:
#         PALIELINĀT skaits PAR 1

# IZVADĪT skaits

print()
print("1. uzdevums")
print("---------------------")
skaitli = [-6, 3, 0, 9, -12, 14, 18, 5]
skaits = 0
for x in skaitli:
    if x>0 and x % 3 == 0:
        skaits = skaits + 1
print(skaits)





# # ============================================================
# # 2. UZDEVUMS: SLIEKŠŅA UZKRĀJĒJS AR PĀRTRAUKŠANU
# # Mērķis: Summēt skaitļus pēc kārtas. Tiklīdz summa sasniedz 
# # vai pārsniedz 50, nekavējoties pārtraukt ciklu un izdrukāt summu.
# # ============================================================

# DOTS saraksts vertibas = [12, 18, 5, 22, 14, 30]
# MAINĪGAIS kopeja_summa = 0

# KATRAM skaitlim n NO saraksta vertibas:
#     PIESKAITĪT n PIE kopeja_summa
#     JA kopeja_summa >= 50:
#         PĀRTRAUKT CIKLU

# IZVADĪT kopeja_summa
# IZVADĪT saskaitīto_elementu_skaits

print()
print("2. uzdevums")
print("---------------------")
vertibas = [12, 18, 5, 22, 14, 30]
kopeja_summa = 0






# # ============================================================
# # 3. UZDEVUMS: VIETĒJIE MAKSIMUMI (SALĪDZINĀŠANA AR KAIMIŅIEM)
# # Mērķis: Atrast un izdrukāt visus elementus, kas ir 
# # stingri lielāki gan par savu kreiso, gan labo kaimiņu.
# # (Piezīme: pirmajam un pēdējam elementam nav abu kaimiņu).
# # ============================================================

# DOTS saraksts dati = [4, 9, 2, 8, 15, 6, 7, 3]

# NO indeksa 1 LĪDZ indeksam (saraksta_garums - 2) IESKAITOT:
#     JA dati[indekss] > dati[indekss - 1] UN dati[indekss] > dati[indekss + 1]:
#         IZVADĪT "Virsotne:", dati[indekss] un viņa kaimiņu vērtības
print()
print("3. uzdevums")
print("---------------------")


# # ============================================================
# # 4. UZDEVUMS: SIMBOLU VIRKNES FORMATĒŠANA
# # Mērķis: No dotā teksta izveidot jaunu tekstu, 
# # aizstājot visas atstarpes ar pasvītrojuma zīmi "_", 
# # bet visus pārējos simbolus atstājot nemainītus.
# # ============================================================

# DOTS teksts = "ievads algoritmos un datu teorija"
# MAINĪGAIS rezultats = ""

# KATRAM simbolam c NO teksta:
#     JA c IR ATSTARPE:
#         PIEVIENOT "_" PIE rezultats GALĀ
#     CITĀDI:
#         PIEVIENOT c PIE rezultats GALĀ

# IZVADĪT rezultats


# # ============================================================
# # 5. UZDEVUMS: MAZĀKĀ SKAITĻA INDEKSA MEKLĒŠANA
# # Mērķis: Atrast sarakstā mazāko skaitli un izdrukāt nevis 
# # pašu skaitli, bet gan pozīciju (indeksu), kurā tas atrodas.
# # ============================================================

# DOTS saraksts masivs = [34, 12, 89, 7, 45, 23]
# MAINĪGAIS min_indekss = 0

# NO i = 1 LĪDZ saraksta pēdējam indeksam:
#     JA masivs[i] < masivs[min_indekss]:
#         min_indekss = i

# IZVADĪT "Mazākā elementa pozīcija ir:", min_indekss