# Trūkstošās profila bildes

Kopā: **0** no 176 profiliem (izņemot `inactive` + `commentator`). Atjaunots 2026-05-30 14:40.

Fails: `assets/photos/{slug}.jpg` (JPG, ~200–400px). Profilam ir bilde, ja eksistē `assets/photos/<_slugify(name)>.jpg`.

**Visas bildes ir vietā.** 🎉

## Piezīmes

- 2026-05-30: ielādēti 17 trūkstošie avatari ar `python -m scripts.fetch_profile_photos`
  (deputāti Ceriņš/Velps/Lindberga/Zalāns/Žuravļevs/Zeltīts + mediji IR/Krustpunktā/LETA/
  LTV De Facto/LTV Panorāma/NRA/Otto Ozols/Marats Kasems/TV3 Ziņas + institūcijas
  Latvijas armija (NBS) un Saeimas ziņas).
- 2026-05-30: pievienoti manuāli (operatora skrīnšoti, konvertēti uz JPEG) — Aleksandrs
  Bartaševičs un Jānis Tutins. Render `--only=politiki,personas,partijas` + `deploy.sh --no-delete`.
