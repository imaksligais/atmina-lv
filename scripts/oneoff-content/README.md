# Vienreizējie satura ģeneratori

Šeit dzīvo 24 skripti, kas **vienu reizi** uzzīmēja kādu publicētu artefaktu — pārskata attēlu, PDF/DOCX melnrakstu, laika joslu, tvītu paku vai intro video. Katrs ir savas dienas darbs, ne rīks.

**Neviena rutīna tos nesauc.** Tie nav `scripts/check.sh`, `scripts/deploy.sh`, dienas vai nedēļas rutīnā, nevienā `.claude/` promptā un nevienā testā; `scripts/` saknē paliek tikai dzīvie ieejas punkti un atkārtoti lietojamie rīki.

Tos netur šeit sentimenta pēc: determiniska ģeneratora kods repo kokā ir attēla vietniece (BACKLOG § ģeneratoru izņēmums), tāpēc **neko no šīs mapes nedzēš** — pārvieto vai papildina.

Palaiž no repo saknes ar `.venv/Scripts/python.exe scripts/oneoff-content/<fails>.py`; repo sakni tie atrod paši caur `Path(__file__).resolve().parents[2]`.
