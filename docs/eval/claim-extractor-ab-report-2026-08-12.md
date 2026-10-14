# Claim-extractor prompta eksperiments — 2026-08-12

## Uzbūve

11 vēsturiski grūtie gadījumi ar dokumentētu pareizo iznākumu (operatora korekcijas, DA noraidījumi, CHANGELOG precedenti). Dry-run bez DB rakstīšanas; abi aģenti = `claim-extractor` (Opus). Katrs gadījums pārstāv vienu zināmu kļūdu klasi:

| # | Gadījums | Pārbaudāmā klase |
|---|---|---|
| 1 | Vītols 2PL tvīts | sarkasms beigās invertē nostāju (#7322) |
| 2 | Braže / Delfi paywall | parafrāze kā quote + paywall stubs (#423) |
| 3 | Braže / NRA | virsraksts kā quote + vienpusējs stance (#113) |
| 4 | Zeltīts RT | RT ar verbatim citātu ≠ first-party (#689420) |
| 5 | Kleinbergs RT @ltvzinas | tā pati klase, cits paveids (#689422) |
| 6 | Štāls KNAB | vairāku prasību konsolidācija vienā tēmā (T2) |
| 7 | Lindberga "diskotēkas" | platums: nosaukts pasākums ≠ kategorija (#615828) |
| 8 | Hermanis koalīcija | kondicionāļa saglabāšana (#615824 klase) |
| 9 | Indriksone lībiešu val. | tēmas robeža + kondicionālis + marķiera-vārda higiēna (#689217) |
| 10 | Vitenbergs pmo.ee | fragmentāri citāti, hedžu saglabāšana (#20850) |
| 11 | NBS Tūtins | institūcijas balss vs privāta ekspertīze + truncated-source (#555829) |

Variants A = pašreizējais prompts bez izmaiņām. Variants B = tas pats + obligāts 7 punktu pirms-atbildes kontrolsaraksts (runātājs / līdz galam / kvalifikatori / quote-verbatim / platums / viena tēma / otra puse), atbildē jāuzrāda.

## Rezultāti pa gadījumiem

| # | A | B | Piezīmes |
|---|---|---|---|
| 1 | ✅ | ✅ | Abi izslēdz sarkasmu; B papildus eksplicīti tur "tiem, kuri to vēlas" |
| 2 | ✅ | ✅ | Abi: needs_review, quote=null, zema conf. Abi izvēlas Ārpolitika (vēsturiskais labojums: Aizsardzība un drošība) — robežgadījums, karogs pareizs |
| 3 | ✅ | ✅ | Abi netur virsrakstu kā quote un iekļauj hibrīddraudu pusi; B saglabā arī laika logu "tuvāko gadu laikā" |
| 4 | ✅ | ✅ | Abi empty ar pareizu klases atpazīšanu |
| 5 | ✅ | ✅ | Abi needs_review (nevis tīrs claim) — 2026-08-10 klase vairs neizslīd |
| 6 | ✅ | ✅ | Abi konsolidē vienā claim; abi "būtu jāveic"→aicina (ne pieprasa) |
| 7 | ◐ | ◐ | Abi tur "diskotēkām" nesašaurinātu, bet abi zaudē "ko raksturo kā" atrunu (vēsturiskajā korekcijā tā ir būtiska). A tēma = Imigrācija (sakrīt ar operatora lēmumu), B = NVO — B šeit novirzās no rationale-principa |
| 8 | ✅ | ✅ | Abi tur kondicionāli "ja atkal JV un Pro" |
| 9 | ✅ | ✅ | Abi: Valodu politika, kondicionālis saglabāts, marķiera vārdi nav noplūduši |
| 10 | ◐ | ✅ | **A ieliek fragmentāru citātu** ("varbūt necensties...") Klimata claim — nesaistīts fragments, nevis nepārtraukts pirmās personas teikums. B pareizi: quote=null + zemāka conf |
| 11 | ◐ | ✅ | A: quote=null (pārlieku strikti — verbatim citāts eksistē). B: tur verbatim citātu ar pazemināti conf — burtiski sakrīt ar operatora korekciju #555829 |

Kopvērtējums: A ≈ 8.5/11, B ≈ 9.5/11. Neviens no abiem neuzķērās uz vēsturiskajām lamatām — bāzes prompts jau ir spēcīgs; atlikušās kļūdas ir tieši quote-fidelity un atribūcijas-atrunas nianses.

## Secinājumi

1. **Kontrolsaraksts uzlabo tieši quote-fidelity robežgadījumus** (10, 11) — abās pusēs: gan atturot no fragmentāra citāta, gan atturot no pārlieku stingra null. Hipotēze: 4. punkts ("verbatim NEPĀRTRAUKTS") piespiež eksplicītu lēmumu, kur garā prompta noteikums Nr. 8 paliek pasīvs.
2. **Neatrisināta paliek atribūcijas-atrunas klase** (7. gadījums, "ko raksturo kā X"): kad politiķa apzīmējums atšķiras no realitātes, stance to atkārto bez atrunas. Neviens kontrolsaraksta punkts to nesedza. Kandidāts jaunam punktam/noteikumam: *"Ja stance atkārto runātāja strīdīgu apzīmējumu par citu personu/pasākumu/organizāciju, ietin to ar 'ko viņš/viņa raksturo kā …'"*.
3. **Kontrolsaraksta cena ≈ 0** (83.6k vs 84.2k tokeni) — pašdokumentējošie jā/nē lauki aizņem maz un dod auditējamu pēdu.
4. B tēmas izvēle 7. gadījumā rāda, ka kontrolsaraksts nedrīkst dublēt tēmas-robežas lēmumu (tur jau ir Topic Boundary Rule) — 7 punkti jāatstāj formas, ne satura jautājumiem.

## Ieteikums (operatora lēmumam — nekas vēl nav mainīts)

`.claude/agents/claim-extractor.md` beigās pievienot kompaktu **"Pirms katras atbildes — 6 jautājumi"** bloku (bez tēmas-robežas punkta, ar jauno atribūcijas-atrunas punktu):
1. Runātājs pats? (RT-verbatim ≠ first-party)
2. Izlasīts līdz beigām? (sarkasms/atsauce beigās)
3. Visi kvalifikatori saglabāti?
4. Quote = verbatim nepārtraukts pirmās personas teksts? Citādi null.
5. Stance ne platāks par avotu?
6. Strīdīgs apzīmējums ietīts atrunā ("ko raksturo kā …")?

Efekts sagaidāms mazs, bet mērķēts tieši uz divām joprojām dzīvajām kļūdu klasēm (quote-fidelity, atribūcijas atruna), un cena ir dažas rindas prompta + ~0 tokenu.

---

# Papildinājums 2026-08-13 — variants C (validācija pēc ieviešanas)

Pēc 6 jautājumu bloka iestrādāšanas `claim-extractor.md` Critical Rules 9. punktā
palaists variants C: tas pats tīrais gadījumu fails, kontrolsaraksts TIKAI
sistēmas failā (ne uzdevuma promptā) — t.i., reālā ražošanas konfigurācija.

**Rezultāts: 11/11** (A 8.5, B 9.5, C 11).

| Gadījums | Ko C izdarīja labāk |
|---|---|
| 7 | Vienīgais variants, kas ietina strīdīgo apzīmējumu atrunā: "pasākumiem, ko viņa raksturo kā «kaut kādas diskotēkas»" — jaunā 6. jautājuma klase; tēma Imigrācija (operatora precedents), kur B novirzījās uz NVO |
| 10 | quote=null fragmentāriem citātiem ar eksplicītu pamatojumu (A šeit ielika sašūtu fragmentu) |
| 11 | Verbatim citāts + pazemināta conf 0.6 — burtiski #555829 operatora korekcijas forma |
| 6 | Papildu piesardzība: nepārbaudītie apgalvojumi par nosauktu personu (Straume) apzināti nav transportēti stance kā fakts |

**Secinājumi:**
1. Faila beigās iestrādāts kontrolsaraksts NE tikai notur uzdevuma-prompta efektu — tas to pārspēj (visticamāk tāpēc, ka Critical Rules sadaļu aģents lasa kā normatīvu, ne kā ieteikumu).
2. Jaunais 6. jautājums (atribūcijas atruna) reāli nostrādā pirmajā mēģinājumā.
3. **Atklāta neizlemta tēmas robeža:** visi trīs varianti 2. gadījumam izvēlas `Ārpolitika`, kur vēsturiskais #423 palika `Aizsardzība un drošība`. Klase "NATO naratīvs / dezinformācijas uzbrukums aliansei" nav starp 2026-08-11 izlemtajiem precedentiem — kandidāts nākamajai precedentu triāžai (operatora lēmums; līdz tam karogs NEEDS_REVIEW šai klasei ir pareizā uzvedība).
4. Metodikas piezīme: golden failam pirms padošanas aģentam OBLIGĀTI jānogriež rubrikas sadaļa (Read ielādē visu failu; viens C mēģinājums tāpēc tika apturēts un pārpalaists ar tīru kopiju).
