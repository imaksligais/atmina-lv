"""``src/credentials.py`` — keyring pieejas slānis.

**Saucējs (plāna 6.1): 4 no 4 moduļa funkcijām** — ``get_credential``,
``set_credential``, ``verify_all``, ``main``.

**Precizējums pret uzdevuma formulējumu:** modulim NAV vides mainīgo ceļa.
Uzdevums prasīja "env/keyring resolution paths"; kods lasa TIKAI OS keyring
(``keyring.get_password(SERVICE_NAME, name)``) — nav ne ``os.environ``
fallback, ne ``.env`` lasījuma, ne noklusējuma vērtību. Šie testi pin to, kas
ir, un tas pats par sevi ir dokumentējams fakts: ja kāds gaida, ka
``ANTHROPIC_API_KEY`` vides mainīgais te "vienkārši nostrādās", tas nenostrādās.

**Noslēpumi: nekādi.** Reālais keyring nekad netiek aiztikts — ``src.credentials
.keyring`` ir aizvietots ar vārdnīcas-fake katrā testā (autouse fikstūra), un
visas vērtības ir acīmredzami izdomātas placeholdera virknes.
"""

from __future__ import annotations

import pytest

from src import credentials

DUMMY = "not-a-real-value-test-only"


class _FakeKeyring:
    """Vārdnīcas keyring; tur (service, name) → value, kā īstais."""

    def __init__(self):
        self.store: dict[tuple[str, str], str] = {}

    def get_password(self, service, name):
        return self.store.get((service, name))

    def set_password(self, service, name, value):
        self.store[(service, name)] = value


@pytest.fixture(autouse=True)
def fake_keyring(monkeypatch):
    fake = _FakeKeyring()
    monkeypatch.setattr(credentials, "keyring", fake)
    return fake


# --- get / set -------------------------------------------------------------


def test_get_credential_returns_none_when_absent(fake_keyring):
    assert credentials.get_credential("x_username") is None


def test_set_then_get_round_trips_under_the_service_name(fake_keyring):
    credentials.set_credential("x_username", DUMMY)
    assert fake_keyring.store == {(credentials.SERVICE_NAME, "x_username"): DUMMY}
    assert credentials.get_credential("x_username") == DUMMY


def test_service_name_is_the_legacy_politracker_namespace():
    """``politracker`` ir mantojuma nosaukums no pirms-2026-04-06 pivota.

    Tā maiņa PADARĪTU NEREDZAMU katru jau saglabāto atslēgu operatora keyring —
    tāpēc tas ir apzināts lēmums, ne kosmētika.
    """
    assert credentials.SERVICE_NAME == "politracker"


# --- verify_all ------------------------------------------------------------


def test_verify_all_reports_every_known_key(fake_keyring):
    out = credentials.verify_all()
    assert set(out) == set(credentials.KNOWN_KEYS)
    assert len(out) == len(credentials.KNOWN_KEYS) == 14   # saucējs, ne "kaut kas"
    assert set(out.values()) == {False}


def test_verify_all_flips_only_the_key_that_was_set(fake_keyring):
    credentials.set_credential("dashboard_password", DUMMY)
    out = credentials.verify_all()
    assert out["dashboard_password"] is True
    assert sum(out.values()) == 1


def test_verify_all_treats_an_empty_string_as_present(fake_keyring):
    """Raksturojums: pārbaude ir ``is not None``, ne "nav tukšs".

    Tukša vērtība keyring rādās kā SET, un preflight to nesauc par trūkstošu.
    Pinēts, jo tieši šī forma padara "viss iestatīts" par nepatiesu zaļu.
    """
    credentials.set_credential("session_secret", "")
    assert credentials.verify_all()["session_secret"] is True


def test_removed_platform_keys_stay_removed(fake_keyring):
    """``youtube_api_key`` + ``facebook_page_token`` izņemti 2026-08-15.

    Tie nekad nebija iestatīti, tāpēc ``verify_all()`` par tiem brīdināja KATRĀ
    preflight skrējienā — divi mūžīgi WARNING platformām, ko Datu līgums #11
    saka, ka mēs neingestējam. Atpakaļpievienošana ir regresija.
    """
    assert "youtube_api_key" not in credentials.KNOWN_KEYS
    assert "facebook_page_token" not in credentials.KNOWN_KEYS


def test_known_keys_has_no_duplicates(fake_keyring):
    assert len(credentials.KNOWN_KEYS) == len(set(credentials.KNOWN_KEYS))


# --- main() CLI ------------------------------------------------------------


def test_main_without_a_command_exits_1(monkeypatch, capsys):
    monkeypatch.setattr(credentials.sys, "argv", ["credentials"])
    with pytest.raises(SystemExit) as exc:
        credentials.main()
    assert exc.value.code == 1
    assert "Usage:" in capsys.readouterr().out


def test_main_check_prints_set_or_not_set_for_every_key(monkeypatch, capsys, fake_keyring):
    credentials.set_credential("telegram_bot_token", DUMMY)
    monkeypatch.setattr(credentials.sys, "argv", ["credentials", "check"])
    credentials.main()
    out = capsys.readouterr().out
    assert out.count("NOT SET") == len(credentials.KNOWN_KEYS) - 1
    assert "telegram_bot_token: SET" in out
    # Saucējs redzams izvadē: katra zināmā atslēga nosaukta tieši vienreiz.
    for key in credentials.KNOWN_KEYS:
        assert f"  {key}: " in out


def test_main_set_reads_the_value_from_getpass_not_argv(monkeypatch, capsys, fake_keyring):
    """Vērtība nekad neiet caur ``sys.argv`` — tā nenokļūst čaulas vēsturē."""
    monkeypatch.setattr(credentials.sys, "argv", ["credentials", "set", "x_password"])
    monkeypatch.setattr(credentials.getpass, "getpass", lambda prompt: DUMMY)
    credentials.main()
    assert credentials.get_credential("x_password") == DUMMY
    assert "Stored x_password" in capsys.readouterr().out


def test_main_set_without_a_key_name_exits_1(monkeypatch, capsys):
    monkeypatch.setattr(credentials.sys, "argv", ["credentials", "set"])
    with pytest.raises(SystemExit) as exc:
        credentials.main()
    assert exc.value.code == 1


def test_main_set_accepts_a_key_outside_known_keys(monkeypatch, fake_keyring):
    """Raksturojums: ``set`` NEvalidē atslēgas vārdu pret ``KNOWN_KEYS``.

    Pārrakstīšanās (``x_passwrd``) klusi noglabā vērtību atslēgā, ko
    ``verify_all()`` nekad neskatās, un ``check`` turpina rādīt ``NOT SET``
    īstajai. Nav šodienas defekts, bet ir klusa rakstīšana — CLAUDE.md § "Stop
    beats write" klase.
    """
    monkeypatch.setattr(credentials.sys, "argv", ["credentials", "set", "x_passwrd"])
    monkeypatch.setattr(credentials.getpass, "getpass", lambda prompt: DUMMY)
    credentials.main()
    assert credentials.get_credential("x_passwrd") == DUMMY
    assert credentials.verify_all().get("x_passwrd") is None


def test_main_unknown_command_exits_1(monkeypatch, capsys):
    monkeypatch.setattr(credentials.sys, "argv", ["credentials", "rotate"])
    with pytest.raises(SystemExit) as exc:
        credentials.main()
    assert exc.value.code == 1
    assert "Unknown command: rotate" in capsys.readouterr().out
