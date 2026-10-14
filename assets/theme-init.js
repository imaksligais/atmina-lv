// theme-init.js — renderēšanu bloķējošs galvenes skripts (BEZ defer/async).
// Divi uzdevumi, kas jāizpilda PIRMS pirmās krāsošanas:
//   1. FOUC aizsargs: saglabātā tēma (localStorage 'atmina:theme') → data-theme
//      atribūts uz <html> + meta color-scheme un theme-color — lai gaišā tēma
//      neuzplaiksnī tumšā (vai otrādi) lapas ielādes brīdī.
//   2. Fontu media-swap: Google Fonts stils tiek ielādēts ar media="print"
//      (lai neblokētu renderēšanu); kad tas ielādēts, pārslēdzam uz media="all".
(function () {
  // --- 1. Tēmas FOUC aizsargs ---
  try {
    var dark = localStorage.getItem('atmina:theme') === 'dark';
    if (!dark) {
      document.documentElement.setAttribute('data-theme', 'light');
    }
    var cs = document.getElementById('meta-color-scheme');
    if (cs) {
      cs.setAttribute('content', dark ? 'dark' : 'light');
    }
    // Statiskais theme-color ir gaišās tēmas --bg; tumšajai to nomaina jau
    // šeit, citādi telefona josla līdz defer chrome-v1.js uzplaiksnī gaiša.
    // #0d1014 = :root --bg style.css (tests/test_base_theme_meta.py).
    var tc = document.getElementById('meta-theme-color');
    if (tc && dark) {
      tc.setAttribute('content', '#0d1014');
    }
  } catch (e) {}

  // --- 2. (noņemts 2026-08-15) Fontu media-swap uz link[data-font-async] ---
  // Bija vajadzīgs, kamēr JetBrains Mono nāca no fonts.googleapis.com kā
  // renderi bloķējoša loksne. Fonts tagad ir pašmitināts (@font-face ar
  // font-display: swap style.css sākumā), tāpēc bloķējošas loksnes vairs nav
  // un swap-triks bija miris kods.
})();
