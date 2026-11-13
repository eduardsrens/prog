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

3,  -1
8,  7 1
2,  6
11,  17 2
4,  16
7  23 3
