// lbv1.js — raksta attēlu pilnekrāna skats (blog-post.html.j2: analīzes,
// sintēzes, dienas pārskati). Bez JS attēls paliek parasts <img>; ar JS katrs
// raksta (.post-content) attēls, kas NAV saitē, kļūst par pogu, kas atver
// vienu kopīgu <dialog class="lb"> (showModal: Esc, fokusa slazds, top layer).
// Lapas ritināšanu bloķē CSS (html:has(dialog.lb:modal)), ne šis skripts.
// Režīmi: «fit» (viss attēls ekrānā); «pan» (attēls ekrāna augstumā, velk uz
// sāniem — sāk ar to, ja fit attēlu samazinātu zem puses, t.i. telefonā plata
// shēma); «natural» (dabiskais izmērs, platā ekrānā). Klikšķis uz attēla
// pārslēdz starp fit un otru režīmu.
(function () {
  var MIN_SIZE = 200; // mazākas bildes (ikonas) netiek palielinātas
  var imgs = document.querySelectorAll('.post-content img');
  if (!imgs.length || typeof HTMLDialogElement !== 'function') return;

  var dialog, scroller, big, caption, trigger, fitScale = 1;

  function build() {
    dialog = document.createElement('dialog');
    dialog.className = 'lb';
    dialog.setAttribute('aria-label', 'Attēla palielinājums');
    var close = document.createElement('button');
    close.type = 'button';
    close.className = 'lb-close';
    close.setAttribute('aria-label', 'Aizvērt');
    close.textContent = '×';
    scroller = document.createElement('div');
    scroller.className = 'lb-scroll';
    big = document.createElement('img');
    big.className = 'lb-img';
    big.alt = '';
    caption = document.createElement('figcaption');
    caption.className = 'lb-cap';
    var fig = document.createElement('figure');
    fig.className = 'lb-fig';
    scroller.appendChild(big);
    fig.appendChild(scroller);
    fig.appendChild(caption);
    dialog.appendChild(close);
    dialog.appendChild(fig);
    document.body.appendChild(dialog);

    close.addEventListener('click', function () { dialog.close(); });
    dialog.addEventListener('click', function (e) {
      if (e.target === big) {
        var zoomed = dialog.classList.contains('is-pan') || dialog.classList.contains('is-natural');
        dialog.classList.remove('is-pan', 'is-natural');
        if (!zoomed) dialog.classList.add(fitScale < 0.5 ? 'is-pan' : 'is-natural');
      } else if (e.target === dialog || e.target === scroller || e.target === fig) {
        dialog.close(); // klikšķis tumšajā laukumā ap attēlu
      }
    });
    // 'close' nāk arī no Esc (native cancel), tāpēc fokusu atjauno šeit.
    dialog.addEventListener('close', function () {
      if (trigger) trigger.focus();
      trigger = null;
    });
  }

  function open(img) {
    if (!dialog) build();
    trigger = img;
    big.src = img.currentSrc || img.src;
    // pan režīms aizpilda augstumu, bet nekad nepalielina pāri dabiskajam izmēram
    big.style.setProperty('--lb-nat-h', (img.naturalHeight || 0) + 'px');
    caption.textContent = img.alt || '';
    caption.hidden = !img.alt;
    fitScale = Math.min(1, window.innerWidth / (img.naturalWidth || 1),
      window.innerHeight / (img.naturalHeight || 1));
    dialog.classList.remove('is-natural');
    dialog.classList.toggle('is-pan', fitScale < 0.5);
    dialog.showModal();
    scroller.scrollTop = 0;
    scroller.scrollLeft = 0;
  }

  function enhance(img) {
    if (img.naturalWidth < MIN_SIZE && img.naturalHeight < MIN_SIZE) return;
    img.classList.add('lb-zoomable');
    img.tabIndex = 0;
    img.setAttribute('role', 'button');
    img.setAttribute('aria-label', 'Palielināt attēlu' + (img.alt ? ': ' + img.alt : ''));
    img.addEventListener('click', function () { open(img); });
    img.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        open(img);
      }
    });
  }

  // defer izpildās pirms attēli ielādēti — izmēru zina tikai pēc 'load'.
  Array.prototype.forEach.call(imgs, function (img) {
    if (img.closest('a')) return; // saite ved citur — to neaizstāj
    if (img.complete && img.naturalWidth) enhance(img);
    else img.addEventListener('load', function () { enhance(img); }, { once: true });
  });
})();
