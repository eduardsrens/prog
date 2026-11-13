def apvienot_intervalus(intervali):
    if not intervali:
        return []

    # Sakārto pēc sākuma punkta
    sakartoti = sorted(intervali, key=lambda x: x[0])
    rezultats = [sakartoti[0]]

    for pasreizejais in sakartoti[1:]:
        pedejais = rezultats[-1]

        # Pārbauda pārklāšanos un pagarina robežu ar max()
        if pasreizejais[0] <= pedejais[1]:
            pedejais[1] = max(pedejais[1], pasreizejais[1])
        else:
            rezultats.append(pasreizejais)

    return rezultats


# --- TESTI ---

# Pārklājas
assert apvienot_intervalus([[1, 4], [3, 6]]) == [[1, 6]]

# Nepārklājas
assert apvienot_intervalus([[1, 2], [4, 5]]) == [[1, 2], [4, 5]]

# Pieskaras robežām
assert apvienot_intervalus([[1, 3], [3, 5]]) == [[1, 5]]

# Viens otra iekšpusē
assert apvienot_intervalus([[1, 10], [3, 5]]) == [[1, 10]]

# Trīs pārklājas pēc kārtas
assert apvienot_intervalus([[1, 3], [2, 5], [4, 7]]) == [[1, 7]]

# Daži pārklājas, daži nē
assert apvienot_intervalus([[1, 3], [2, 4], [6, 8]]) == [[1, 4], [6, 8]]

# Nesakārtota secība
assert apvienot_intervalus([[5, 7], [1, 3], [2, 4]]) == [[1, 4], [5, 7]]

# Vienādi intervāli
assert apvienot_intervalus([[2, 4], [2, 4]]) == [[2, 4]]

# --- Negatīvi skaitļi ---
assert apvienot_intervalus([[-5, -1], [-3, 2]]) == [[-5, 2]]            # pārklājas
assert apvienot_intervalus([[-10, -6], [-4, -2]]) == [[-10, -6], [-4, -2]]  # nepārklājas
assert apvienot_intervalus([[-3, 0], [0, 3]]) == [[-3, 3]]              # pieskaras pie nulles
assert apvienot_intervalus([[-10, 10], [-2, 2]]) == [[-10, 10]]         # viens otra iekšpusē

# --- Daļskaitļi (Python kodā decimālatdalītājs ir punkts) ---
assert apvienot_intervalus([[1.5, 3.5], [2.5, 5.0]]) == [[1.5, 5.0]]    # pārklājas
assert apvienot_intervalus([[0.5, 1.5], [2.5, 3.5]]) == [[0.5, 1.5], [2.5, 3.5]]  # nepārklājas
assert apvienot_intervalus([[1.5, 2.5], [2.5, 4.0]]) == [[1.5, 4.0]]    # pieskaras robežām
assert apvienot_intervalus([[1.25, 9.75], [2.5, 3.5]]) == [[1.25, 9.75]]  # viens otra iekšpusē

# --- Simti ---
assert apvienot_intervalus([[100, 250], [200, 400]]) == [[100, 400]]    # pārklājas
assert apvienot_intervalus([[100, 199], [300, 500]]) == [[100, 199], [300, 500]]  # nepārklājas
assert apvienot_intervalus([[100, 300], [300, 600]]) == [[100, 600]]    # pieskaras robežām
assert apvienot_intervalus([[100, 900], [150, 250]]) == [[100, 900]]    # viens otra iekšpusē

print("Visi testi izdevās!\n")


# Piemērs
paraugs = [[1, 3], [2, 6], [8, 10], [15, 18]]
print("Programma aicina ievadīt intervālus un apvieno tos, ja tie pārklājas.")
print("Piemērs:", paraugs)
print("Apvienotie:  ", apvienot_intervalus(paraugs))


print("\n--- IEVADIET SAVUS INTERVĀLUS ---")
ievade_str = input("Ievadiet intervālu skaitu: ").strip()

if ievade_str.isdigit() and int(ievade_str) > 0:
    skaits = int(ievade_str)
    lietotaja_dati = []

    print("Ievadiet katru intervālu formātā 'sākums beigas' (piemēram: 1 5):")
    for i in range(skaits):
        dala = input(f"#{i + 1}: ").split()
        if len(dala) == 2:
            sakums, beigas = int(dala[0]), int(dala[1])
            if sakums > beigas:
                sakums, beigas = beigas, sakums
            lietotaja_dati.append([sakums, beigas])

    print("\nIevadītie intervāli: ", lietotaja_dati)
    print("Gala rezultāts:       ", apvienot_intervalus(lietotaja_dati))
else:
    print("Ievade atcelta vai nekorekts skaits.")