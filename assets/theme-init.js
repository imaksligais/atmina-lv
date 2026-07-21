// theme-init.js — renderēšanu bloķējošs galvenes skripts (BEZ defer/async).
// Divi uzdevumi, kas jāizpilda PIRMS pirmās krāsošanas:
//   1. FOUC aizsargs: saglabātā tēma (localStorage 'atmina:theme') → data-theme
//      atribūts uz <html> + meta[name=color-scheme] content — lai gaišā tēma
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
  } catch (e) {}

  // --- 2. Fontu media-swap uz link[data-font-async] ---
  // Aizstāj veco onload="this.media='all'" triku un aizver jau-ielādēta-loksne
  // sacīkstes stāvokli: ja link.sheet jau ir pieejama, pārslēdzam uzreiz;
  // pretējā gadījumā gaidām 'load' notikumu.
  var fontLinks = document.querySelectorAll('link[data-font-async]');
  for (var i = 0; i < fontLinks.length; i++) {
    (function (link) {
      var swap = function () { link.media = 'all'; };
      if (link.sheet) {
        swap();
      } else {
        link.addEventListener('load', swap);
      }
    })(fontLinks[i]);
  }
})();
