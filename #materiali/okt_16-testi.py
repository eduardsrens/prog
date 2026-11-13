skaitli = [10, 5, 2]
summa = 0

for i in range(len(skaitli)):
    if i % 2 == 0:
        summa = summa + skaitli[i]
print(summa)


for j in skaitli:
    if j % 2 == 0:
        summa = summa + j
print(summa)

