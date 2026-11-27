# Projekta kopsavilkums

Šajā repozitorijā apkopoti vairāki atsevišķi Python mācību un spēļu projekti. Tie nav apvienoti vienā programmā: katrai galvenajai mapei ir sava loģika, palaišanas fails un, dažos gadījumos, savs grafiskais interfeiss. Lielākā daļa projektu izmanto Python standarta bibliotēku un Tkinter; labirinta spēlei **Glowbug** nepieciešama papildu `pygame-ce` bibliotēka.

## Mapju struktūra

### `#materiali/` — algoritmu un Python pamatu uzdevumi

- `okt_16-galvaa.py` — piemēri par skaitļu summēšanu un skaitīšanu, meklēšanu sarakstā, ligzdotiem cikliem, minimumu/maksimumu, `range`, `break`/`continue` un virkņu analīzi.
- `okt_16-pseido.py` — uzdevumu apraksti pseidokodā par filtrēšanu, sliekšņa summu, lokālajiem maksimumiem, teksta pārveidošanu un minimuma indeksa meklēšanu.
- `okt_16-testi.py` — daļa no minētajiem uzdevumiem pārveidota izpildāmā Python kodā.
- `intervali.py` — sakārto un apvieno pārklājošus vai robežpunktā saskarošus intervālus; satur piemēru pārbaudes un interaktīvu ievadi.
- `speed1.py` — pāra skaitļu skaitīšanas piemēri ar dalījuma atlikumu un bitu operāciju.
- `speed2.py` — burbuļkārtošanas un ātrās kārtošanas piemēri.
- `speed3.py` — nepabeigts piemērs ar skaitļu saraksta apstrādi; failā ir sintakses kļūda.
- `life.py` — piezīmes par iespējamiem Conway's Game of Life grafisko bibliotēku variantiem un projekta ieceri.
- `solve_maze.py` — labirinta meklēšanas un maršrutu animēšanas Tkinter programma, līdzīga citai šī repozitorija labirinta versijai.

### `blackjack/` — Blackjack botu turnīrs

- `RULES.md` apraksta četru kāršu kavu turnīra nosacījumus, bota funkcijas, likmju un darbību formātu, izmaksas un izpildes laika limitu.
- `tournament.py` ir Tkinter turnīra programma. Tā atrod apakšmapēs esošos `bot.py`, ielādē botus, izspēlē raundus ar kopīgu kāršu kurpi un attēlo rezultātus.
- `Pauls/bot.py` ir kompozīciju ņemošs stratēģijas bots: novērtē kāršu varbūtības, dīlera iespējamos rezultātus, gājienus un likmes.
- `Gundars vaivads/bot.py` izmanto redzēto kāršu sastāvu, lai izvēlētos gājienus un pielāgotu likmes.
- `test_bot/bot.py` ir apzināti vienkāršs testa bots, kas parasti velk līdz 17 un nelieto dubultošanas vai dalīšanas darbības.

### `life/` — Conway's Game of Life

- `game_of_life.py` nodrošina Tkinter grafisko lietotni ar šūnu zīmēšanu, dzēšanu, nejaušu aizpildīšanu, simulācijas soļošanu un vadības iespējām.
- Tajā pašā programmā ir arī vairāku spēlētāju režīms: servera un klienta komunikācija pa tīklu, spēļu istabas, spēlētāju komandas/teritorijas, gājienu iesniegšana un raundu norise.
- `IDEJAS.md` ir piezīmju lapa ar lietotāja ieteikumu uzlabot ievades teksta krāsu kontrastu.

### `maze/` — labirintu algoritmi, vizualizatori un spēles

Koplietojamie labirintu teksta faili atrodas mapes saknē: `maze_15x25.txt`, `maze_25x41.txt` un `maze_201x301.txt`. Failos `#` apzīmē sienu, bet `A` un `B` — sākumu un mērķi.

- `README.md` apraksta labirintu vizualizatora vadību un testēšanu, taču tajā minētais `uzdevumi/maze/maze_visualizer.py` ceļš neatbilst šī repozitorija pašreizējai mapju struktūrai.
- `Enrijs/pacman_maze.py` izmanto BFS, lai atrastu īsāko ceļu, un animē Pacman pārvietošanos; atbalsta arī teksta izvadi.
- `Gundars/solve_maze.py` piedāvā Tkinter vizualizatoru maršruta meklēšanai un vairāku ceļu apskatei; mapē ir arī liela labirinta fails.
- `Kristers/maze_game.py` ir Pygame-ce spēle **Glowbug** ar labirinta līmeņiem, savācamiem priekšmetiem, pretiniekiem un ģenerētu līmeni. Mapē ir arī savi labirintu faili.
- `Martins/pacman.py` ir Tkinter labirinta spēle/vizualizators ar ceļu meklēšanu un vairāku maršrutu apskati.
- `Nezinams/Maze_visualizer.py` un `Pauls/Maze_visualizer.py` ir labirintu vizualizatoru versijas ar ģenerēšanu, maršrutu meklēšanu un lokālu spēlētāju atbalstu.
- `Nezinams/solve_maze.py` ir komandrindas BFS īsākā ceļa meklētājs ar izvades faila iespēju. `test_maze_visualizer.py` pārbauda meklēšanu, atkārtošanu, ģenerēšanu, eksportu un ievades validāciju.
- `Peteris/maze_game.py` ir Tkinter spēle, kurā spēlētājs pats iziet labirintu un var animēti apskatīt BFS atrasto risinājumu; `maze_game_25x41.py` paredzēts lielākam labirintam. `kara-spele.py` ir atsevišķa stratēģijas spēle par teritorijām un cīņām, bet `pirmais.py` un `Untitled-1.py` ir atsevišķi mācību/eksperimentu skripti.
- `Sabine/sabine_15x25.py` un `sabine_25x41.py` demonstrē BFS ceļa atrašanu un attēlošanu.
- `Valters K/pacman.py` ir **PACMAN / Maze Lab** meklēšanas vizualizators ar interaktīvu izpēti un Pacman ceļa animāciju.

### `tic-tac-toe/` — piecu rindā (Gomoku) un Swap2

Šeit ar Tic-Tac-Toe nosaukumu apzīmēta 15 × 15 piecu rindā spēle. `RULES.md` nosaka uzvaru ar piecām vienādām figūrām pēc kārtas un **Swap2** atklātnes fāzes gājienus.

- `tournament.py` ielādē botus no apakšmapēm, validē gājienus un Swap2 izvēles, ievēro gājienu laika limitu un nodrošina turnīra CLI un Tkinter saskarni.
- `Gundars vaivads/Gundars.py` ir **Knight_bot** — taktiskais bots ar meklēšanu un lokālu pretinieku gājienu/rezultātu mācīšanos. `Knight_bot_learning.json` glabā mācīšanās datus, bet `gui_gundars.py` nodrošina spēli pret botu.
- `kristers_kalnins/bot.py` un `peteris_punins/bot.py` ir atšķirīgas meklēšanā un pozīciju novērtēšanā balstītas botu implementācijas; katrai ir Tkinter `gui.py`.
- `nikita_kotovs/bot.py` ir vēl viena 15 × 15 Swap2 bota implementācija; `assets/` satur GUI attēlu resursus.
- `Pauls/bot.py` ir Gomoku bots ar gājienu kandidātu un līniju novērtēšanu. `game_engine.py` satur spēles un Swap2 stāvokļa loģiku, bet `gui.py` — grafisko saskarni.
- `Test1/bot.py` un `Test4/bot.py` satur līdzīgas meklēšanas dzinēja versijas; `Test2/bot.py` un `Test3/bot.py` ir citas, atšķirīgas stratēģiju implementācijas.

## Palaišana un pārbaudes

No repozitorija saknes var palaist galvenās programmas, piemēram:

```powershell
python life\game_of_life.py
python blackjack\tournament.py
python tic-tac-toe\tournament.py
python maze\Enrijs\pacman_maze.py
```

`maze\Kristers\maze_game.py` palaišanai nepieciešams instalēts `pygame-ce`. Labirinta vizualizatora automātiskās pārbaudes var palaist ar:

```powershell
python -m unittest discover -s maze\Nezinams -p "test_*.py"
```

Repozitorijā nav kopīga palaišanas punkta vai atkarību manifesta; katrs projekts jāpalaiž atsevišķi.
