Tu strādā repo `E:\atmina` (Latvijas politiķu izteikumu datubāze). Uzdevums ir mazs un precīzi norobežots.

## Problēma

`src/matcher.py::_latvian_surname_inflections` uzvārdiem ar galotni `-e` ģenerē tikai **sieviešu** 5. deklinācijas formas: `-es`, `-ei`, `-i` (piem. Mūrniece → Mūrnieces, Mūrniecei, Mūrnieci).

Latviešu valodā **vīrieša** uzvārds ar `-e` lokās citādi — datīvā tas ir `-em`, nevis `-ei`:

    Šnore → Šnores (ģen.), **Šnorem** (dat.), Šnori (akuz.)
    Zīle  → Zīles,        **Zīlem**,          Zīli

Tāpēc dokuments 71307, kurā burtiski stāv «Šnorem», netiek sasaistīts ar Edvīnu Šnori (pid=7). Tas ir **atsauces robs — mēs zaudējam īstas piesaistes**, nevis viltus piesaistes problēma.

## Ko izdarīt

1. Papildini `_latvian_surname_inflections`, lai vīriešu `-e` uzvārdiem tiktu ģenerēta arī datīva forma `-em`.
2. Dzimums no funkcijas argumenta nav redzams (tā saņem tikai uzvārdu). Izvēlies vienu no diviem ceļiem un **pamato izvēli docstringā**:
   - (a) ģenerēt `-em` visiem `-e` uzvārdiem (over-generation, tāpat kā `_first_token_decls` jau dara apzināti), vai
   - (b) nodot dzimuma pazīmi no izsaucēja, kur priekšvārds ir zināms.
   Ja izvēlies (a), docstringā jāpaskaidro, kāpēc over-generation šeit ir droša.
3. Atjaunini funkcijas docstringu (tur jau ir aprakstītas visas 4 deklinācijas — pievieno šo).
4. Pievieno testus `tests/test_matcher.py`.

## Obligātie mērījumi — bez tiem uzdevums nav pabeigts

Uzraksti un palaid pagaidu skriptu (liec to `.scratch/`, nevis `scripts/`), kas atbild:

- **Ieguvums:** cik dokumentu korpusā satur jauno formu pie vārda robežas, un kuriem politiķiem? Izmanto `src.matcher._occurrences`, ne savu regex.
- **Risks:** vai kāda jaunā forma sakrīt ar parastu latviešu vārdu vai cita cilvēka vārdu? Pārbaudi katru jauno formu pret korpusu un **izlasi dažus trāpījumus ar aci** — nepaļaujies uz skaitli.
- Konkrēti apstiprini: vai doc 71307 tagad atbilst Šnorem?

## Aizliegts

- **Nekādu DB rakstīšanu.** DB atver TIKAI `mode=ro`: `sqlite3.connect("file:E:/atmina/data/atmina.db?mode=ro", uri=True)`.
- **Nekādu `git commit`, `git push`, deploy vai renderēšanu.**
- Nemaini nevienu citu failu kā `src/matcher.py` un `tests/test_matcher.py` (pagaidu skripts `.scratch/` ir atļauts).
- Neizdzēs un nepārraksti esošos testus. `tests/test_matcher.py` jau satur regresijas testu `test_surname_substring_in_longer_word_is_not_a_match` ar 11 parametriem — tam jāpaliek zaļam.

## Vārti, kas jāpalaiž pašam pirms atskaites

```
cd /e/atmina
env -u PYTHONPATH .venv/Scripts/python.exe -m pytest tests/test_matcher.py -q
env -u PYTHONPATH .venv/Scripts/python.exe scripts/audit_stale_politician_links.py --limit 400
```

Otrais rīks parāda piesaistes, ko pašreizējais saistītājs vairs neradītu — pēc tavām izmaiņām tas **nedrīkst pieaugt** apakšvirknes («apakšvirknes_slazds») klasē.

## Atskaite

Beigās uzraksti īsu kopsavilkumu: ko mainīji, kāds ir ieguvums skaitļos, kādi ir riski, ko atradi lasot trāpījumus ar aci, un pytest/audita izvade. Ja kaut kas neizdodas vai mērījums parāda, ka izmaiņa nav droša — **saki to un neuzspied izmaiņu**. Negatīvs rezultāts ar pierādījumu ir derīgs rezultāts.
