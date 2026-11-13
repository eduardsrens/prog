
# 1. uzdevums
# -------------------------------
#   vai x > 0?   tad
#      tad izvadam ka ir lielāks
#   ja nav
#      vai x < 0 tad
#         tad izvadam ka mazāks
#      ja nav tad 
#        izvadam ka ir 0


# x = int (input("ievadi skaitli"))

# if x > 0:
#     print ("Skaitlis ir lielāks par nulli")
# elif  x < 0:
#     print ("skaitlis ir mazāks par nulli")
# else:
#     print ("Skaitlis ir vienāds ar nulli")
    
# 2. uzdevums datu pārbaude + aprēķins
# -------------------------------

# Doti 3 skaitļi   a, b, c
#  vai šie skaitļi veido trijstūri?
#  ja jebkuru divu malu summa ir > kā trešā mala,     tad tas ir trijstūris

# visiem vienlaicīgi jābūt spēkā
# a+b>c
#  b+c>a
#  a+c>b

# Aprēķināt šī trijstūra laukumu.
#   Nedrīkst ievadīt negatīvus skaitļus

# atkārtot kamēr x> 0
#   x = int(input("Ievadi skaitli: "))
# atkārtot kamēr normāli pārveidojams par int un nav <0

a = int(input("Ievadi primo skaitli: "))
b = int(input("Ievadi otro skaitli: "))
c = int(input("Ievadi trešo skaitli: "))

if a+b>c and b+c>a and c+a>b:
    s = (a+b+c)/2

    laukums = (s*(s-a)*(s-b)*(s-c))**0.5
    print ("Ir trijstūris. Trijstūra laukums ir:", laukums )

else:
    print ("Nav trijstūris")




