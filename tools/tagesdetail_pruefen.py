#!/usr/bin/env python3
"""Maschinengate der Tagesdetail-Straße (Regeln TD-01..TD-05).

Befund-Kürzel TD-G1..TD-G5 (eigener Namensraum — die Deck-Regeln D-01..D-04
des REGELWERKs bedeuten etwas anderes):
  TD-G1  Kopffelder, Whitelists, Zeitformate, Pflichtabschnitte
  TD-G2  Zeilenformat + Quellen-Vokabular (jede Angabe trägt Herkunft);
         jede nicht-leere Zeile eines Pflichtabschnitts muss Bullet oder
         exakt "keine" sein — Prosa und Tabellen sind Befunde
  TD-G3  Minuten-Arithmetik (Blocksumme = Plan-Zeit; Abweichung von der
         Board-Zeit nur mit "## Überzug" samt Begründung:-Zeile)
  TD-G4  Lücken-Spiegelung (LÜCKE-Quellen == Lücken-Einträge, beidseitig)
  TD-G5  Verweise existieren — Kopffelder UND Zeilen-Quellen, exakter
         Dateistamm; dazu Soll-Ist der erwarteten Tag-IDs (--erwartet)

Board-Treue: `Badge:` trägt das Board-Badge wörtlich (frei), `Art:` die
normalisierte Klasse aus der Whitelist. Zeitangaben dürfen Board-Formen
tragen ("30–45 min", "90 + 30 min", "3 h", "—"); gerechnet wird nur mit
der Plan-Zeit, die eine Einzelzahl sein muss.

T0 ist kein Board-Tag (Quick-Start-Deck außerhalb der Journey) und daher
keine gültige Tag-ID.

Aufruf: tagesdetail_pruefen.py <blatt.md | ordner> [--erwartet T1,T2,...]
                               [--ausloeser hook|cli]
        tagesdetail_pruefen.py --selbsttest
Exit 0 = still & grün, 1 = Befunde (eine Zeile je Befund), 2 = Fehler.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gemeinsam  # noqa: E402

# W0-F ist die Vorbereitungskarte der Starter-Woche (Board-Karte seit 14.10.2026,
# nur bei L0/L1). Sie steht neben W0, weil sie einen anderen Teilnehmerkreis hat:
# Gruppe statt einem Dev, Lizenzen auch fuer Nicht-Entwickler, MCP-Freigabe mit
# der IT, Baseline vor dem Starter.
# T0 ist kein Board-Tag, sondern ein eigener, OPTIONALER Programmtag
# (Christian, 19.10.2026): das Grundlagen-Intro zu M0B vor W1.
TAG_IDS = {"W0", "W0-F", "T0",
           *{f"S{i}" for i in range(1, 6)}, *{f"T{i}" for i in range(1, 21)}}
ARTEN = ("Live-Session", "Gruppen-Session", "Workshop", "Eigenarbeit",
         "Check-in", "Messung", "GF-Report", "Abschlusstermin", "intern")
ROLLEN = ("Entwickler", "Trainer", "Team-Lead", "GF", "intern")
KOPF_FELDER = ("Board-Zeit", "Plan-Zeit", "Badge", "Art", "Teilnehmer",
               "Modul", "Deck", "Rolle", "Level-Ziel")
KOPF_RE = re.compile(r"^(" + "|".join(KOPF_FELDER) + r"):\s*(.+?)\s*$")
ABLAUF_RE = re.compile(r"^- (\d{1,3}) min — (.+?) \(Quelle: ([^)]+)\)$")
PUNKT_RE = re.compile(r"^- (.+?) \(Quelle: ([^)]+)\)$")
QUELLE_EINZEL = re.compile(
    r"^(Board|Modul ([A-Za-z0-9]+)|Deck ([A-Za-z0-9-]+)"
    r"|Programm-Entscheidung \d{1,2}\.\d{1,2}\.\d{4}|LÜCKE)$")
LUECKE_RE = re.compile(r"^- LÜCKE: .+")
BEGRUENDUNG_RE = re.compile(r"^Begründung: \S", re.M)
PFLICHT_ABSCHNITTE = ("Ablauf", "Ergebnis", "Vorbereitung", "Requisiten", "Lücken")


def zeit_spanne(wert: str) -> tuple[int, int] | None:
    """Board-Zeitformen → (min, max) in Minuten. None = nicht interpretierbar."""
    w = wert.strip()
    if w == "—":
        return None
    w = w.replace("–", "-").replace("—", "-")
    m = re.fullmatch(r"(\d{1,3})\s*-\s*(\d{1,3})\s*min", w)
    if m:
        return int(m.group(1)), int(m.group(2))
    m = re.fullmatch(r"(\d{1,3})(?:\s*\+\s*(\d{1,3}))?\s*min", w)
    if m:
        s = int(m.group(1)) + (int(m.group(2)) if m.group(2) else 0)
        return s, s
    m = re.fullmatch(r"(\d{1,2})(?:[.,](\d))?\s*h", w)
    if m:
        s = int(m.group(1)) * 60 + (int(m.group(2)) * 6 if m.group(2) else 0)
        return s, s
    return None


def zeit_gueltig(wert: str) -> bool:
    return wert.strip() == "—" or zeit_spanne(wert) is not None


def abschnitte(text: str) -> tuple[list[str], dict[str, list[str]]]:
    kopf: list[str] = []
    teile: dict[str, list[str]] = {}
    aktiv = None
    for z in text.splitlines():
        m = re.match(r"^## (.+?)\s*$", z)
        if m:
            aktiv = m.group(1)
            teile.setdefault(aktiv, [])
        elif aktiv is None:
            kopf.append(z)
        else:
            teile[aktiv].append(z)
    return kopf, teile


def datei_da(wurzel: Path, ordner: str, kennung: str) -> bool:
    """Exakter Stamm-Match: <kennung>.md oder <kennung>-*.md — kein Präfix-Glob
    (sonst deckt 'M1' die Datei M10-abschluss.md ab)."""
    kandidaten = [kennung]
    m = re.fullmatch(r"M(\d)", kennung)
    if m:  # Board-Kurzform M2 → Dateikennung M02
        kandidaten.append(f"M0{m.group(1)}")
    m = re.fullmatch(r"M(\d)([A-Za-z])", kennung)
    if m:  # Board-Kurzform M9b → Dateikennung M09B (Anhangbloecke)
        kandidaten.append(f"M0{m.group(1)}{m.group(2).upper()}")
    # Seit dem Umzug am 19.10.2026 liegt alles, was zu einem Programmtag
    # gehoert, in praesentationen/sessions/<TAG>/. Module ohne Deck und
    # uebergreifende Dateien stehen weiter in praesentationen/module/.
    # Gesucht wird in beidem, damit das Gate waehrend und nach dem Umzug
    # dasselbe Ergebnis liefert.
    orte = [wurzel / "praesentationen" / "sessions",
            wurzel / "praesentationen" / ordner]
    for k in kandidaten:
        for basis in orte:
            if not basis.exists():
                continue
            if (basis / f"{k}.md").exists():
                return True
            muster = "*/*.md" if basis.name == "sessions" else "*.md"
            if any(p.stem == k or p.stem.startswith(f"{k}-")
                   for p in basis.glob(muster)):
                return True
    return False


def pe_register(wurzel: Path | None) -> set[str] | None:
    """Die im Projekt belegten Programm-Entscheidungs-Daten.
    None = kein Register vorhanden (dann wird nicht geprueft)."""
    if wurzel is None:
        return None
    p = wurzel / "praesentationen" / "PROGRAMM-ENTSCHEIDUNGEN.md"
    if not p.exists():
        return None
    daten = set()
    for m in re.finditer(r"PE-(\d{4})-(\d{2})-(\d{2})", p.read_text(encoding="utf-8")):
        j, mo, t = m.groups()
        daten.add(f"{int(t)}.{int(mo)}.{j}")
    return daten


def pruefe_quelle(q: str, name: str, wo: str, wurzel: Path | None,
                  b: list[str], pe: set[str] | None = None) -> bool:
    """Eine Quellen-Angabe (ggf. mehrere, mit '; ' getrennt). True = LÜCKE dabei."""
    hat_luecke = False
    for teil in [t.strip() for t in q.split(";") if t.strip()]:
        m = QUELLE_EINZEL.match(teil)
        if not m:
            b.append(f"TD-G2 {name}: Quelle '{teil}' nicht im Vokabular "
                     f"(Board | Modul <id> | Deck <id> | "
                     f"Programm-Entscheidung <T.M.JJJJ> | LÜCKE), {wo}")
            continue
        if teil == "LÜCKE":
            hat_luecke = True
        elif teil.startswith("Programm-Entscheidung ") and pe is not None:
            datum = teil.split(" ", 1)[1]
            norm = ".".join(str(int(x)) if x.isdigit() else x
                            for x in datum.split("."))
            if norm not in pe:
                b.append(f"TD-G5 {name}: Programm-Entscheidung {datum} steht "
                         f"nicht in praesentationen/PROGRAMM-ENTSCHEIDUNGEN.md "
                         f"— dort eintragen oder als LÜCKE führen, {wo}")
        elif wurzel is not None and m.group(2) and not datei_da(
                wurzel, "module", m.group(2)):
            b.append(f"TD-G5 {name}: Quelle '{teil}' — keine Moduldatei "
                     f"zu '{m.group(2)}', {wo}")
        elif wurzel is not None and m.group(3) and not datei_da(
                wurzel, "decks", m.group(3)):
            b.append(f"TD-G5 {name}: Quelle '{teil}' — keine Deckdatei "
                     f"zu '{m.group(3)}', {wo}")
    return hat_luecke


def pruefe_blatt(pfad: Path, wurzel: Path | None) -> list[str]:
    b: list[str] = []
    pe = pe_register(wurzel)
    # Seit dem Umzug am 19.10.2026 heisst jedes Blatt TAGESBLATT.md und
    # liegt in sessions/<TAG>/ — dann traegt der Ordner die Tag-ID. Die
    # alte Form <TAG>.md bleibt gueltig, damit Blaetter ausserhalb einer
    # Session (und die Selbsttests) unveraendert durchlaufen.
    name = pfad.parent.name if pfad.stem == "TAGESBLATT" else pfad.stem
    text = pfad.read_text(encoding="utf-8")

    if name not in TAG_IDS:
        b.append(f"TD-G5 {pfad.name}: '{name}' ist keine Board-Tag-ID "
                 f"(W0, W0-F, T0, S1–S5, T1–T20)")

    kopfzeilen, teile = abschnitte(text)
    kopf: dict[str, str] = {}
    for z in kopfzeilen:
        m = KOPF_RE.match(z)
        if m:
            kopf[m.group(1)] = m.group(2)
    for feld in KOPF_FELDER:
        if feld not in kopf:
            b.append(f"TD-G1 {name}: Kopffeld '{feld}:' fehlt (vor dem ersten "
                     f"'## '-Abschnitt)")
    if kopf.get("Art") and kopf["Art"] not in ARTEN:
        b.append(f"TD-G1 {name}: Art '{kopf['Art']}' nicht in Whitelist "
                 f"{'/'.join(ARTEN)} (das Board-Badge gehört ins Feld 'Badge:')")
    if kopf.get("Badge", "").strip() in ("", "—") and kopf.get("Art") != "Eigenarbeit":
        b.append(f"TD-G1 {name}: Badge: trägt kein Board-Badge wörtlich")
    for rolle in [r.strip() for r in kopf.get("Teilnehmer", "").split(",") if r.strip()]:
        if rolle not in ROLLEN:
            b.append(f"TD-G1 {name}: Teilnehmer '{rolle}' nicht in Whitelist "
                     f"{'/'.join(ROLLEN)}")
    if "Teilnehmer" in kopf and not kopf["Teilnehmer"].strip():
        b.append(f"TD-G1 {name}: Teilnehmer: leer")
    for feld in ("Board-Zeit", "Plan-Zeit"):
        if feld in kopf and not zeit_gueltig(kopf[feld]):
            b.append(f"TD-G1 {name}: {feld} '{kopf[feld]}' nicht lesbar — erlaubt "
                     f"sind '<n> min', '<n>–<n> min', '<n> + <n> min', '<n> h', '—'")
    for a in PFLICHT_ABSCHNITTE:
        if a not in teile:
            b.append(f"TD-G1 {name}: Abschnitt '## {a}' fehlt")

    # --- TD-G2: jede Zeile der Pflichtabschnitte ist Bullet oder "keine"
    summe = 0
    ablauf_zeilen = 0
    luecken_quellen = 0
    for abschnitt in PFLICHT_ABSCHNITTE:
        for z in teile.get(abschnitt, []):
            s = z.strip()
            if not s:
                continue
            if s == "keine":
                continue
            if not s.startswith("- "):
                b.append(f"TD-G2 {name}: {abschnitt}: Zeile ist weder Bullet noch "
                         f"'keine': {s[:70]}")
                continue
            if z[:1] not in ("-", ""):  # eingerückter Bullet
                b.append(f"TD-G2 {name}: {abschnitt}: eingerückte Zeile — "
                         f"Unterpunkte sind nicht vorgesehen: {s[:70]}")
                continue
            if abschnitt == "Ablauf":
                m = ABLAUF_RE.match(s)
                if not m:
                    b.append(f"TD-G2 {name}: Ablauf-Zeile ohne Format "
                             f"'- <n> min — <Text> (Quelle: …)': {s[:70]}")
                    continue
                summe += int(m.group(1))
                ablauf_zeilen += 1
                if pruefe_quelle(m.group(3), name, f"Ablauf '{m.group(2)[:30]}'",
                                 wurzel, b, pe):
                    luecken_quellen += 1
            elif abschnitt == "Lücken":
                if not LUECKE_RE.match(s):
                    b.append(f"TD-G2 {name}: Lücken-Zeile ohne Format "
                             f"'- LÜCKE: <was fehlt, wer entscheidet>': {s[:70]}")
            else:
                m = PUNKT_RE.match(s)
                if not m:
                    b.append(f"TD-G2 {name}: {abschnitt}-Zeile ohne Quelle: {s[:70]}")
                    continue
                if pruefe_quelle(m.group(2), name, f"{abschnitt} '{m.group(1)[:30]}'",
                                 wurzel, b, pe):
                    luecken_quellen += 1

    # --- TD-G3: Arithmetik
    plan_roh, board_roh = kopf.get("Plan-Zeit", ""), kopf.get("Board-Zeit", "")
    plan, board = zeit_spanne(plan_roh), zeit_spanne(board_roh)
    ueberzug = "\n".join(teile.get("Überzug", []))
    hat_begruendung = bool(BEGRUENDUNG_RE.search(ueberzug))
    if plan_roh.strip() == "—" and board is not None:
        b.append(f"TD-G3 {name}: Board-Zeit '{board_roh}' nennt Minuten, "
                 f"Plan-Zeit ist '—' — Plan-Zeit ausweisen")
    if plan is not None:
        if plan[0] != plan[1]:
            b.append(f"TD-G3 {name}: Plan-Zeit '{plan_roh}' ist eine Spanne — "
                     f"die Plan-Zeit muss eine Einzelzahl sein")
        elif ablauf_zeilen == 0:
            b.append(f"TD-G3 {name}: Plan-Zeit {plan_roh}, aber kein Ablauf-Block")
        elif summe != plan[0]:
            b.append(f"TD-G3 {name}: Ablauf-Summe {summe} min ≠ Plan-Zeit {plan[0]} min")
        if board is not None and not (board[0] <= plan[0] <= board[1]):
            if not ueberzug.strip():
                b.append(f"TD-G3 {name}: Plan-Zeit {plan_roh} außerhalb der "
                         f"Board-Zeit {board_roh}, aber kein Abschnitt '## Überzug'")
            elif not hat_begruendung:
                b.append(f"TD-G3 {name}: '## Überzug' ohne Zeile 'Begründung: …'")
    if ueberzug.strip() and not hat_begruendung:
        b.append(f"TD-G3 {name}: '## Überzug' ohne Zeile 'Begründung: …'")

    # --- TD-G4: Lücken beidseitig spiegeln
    luecken_eintraege = [z.strip() for z in teile.get("Lücken", [])
                         if LUECKE_RE.match(z.strip())]
    nur_keine = any(z.strip() == "keine" for z in teile.get("Lücken", []))
    if luecken_quellen != len(luecken_eintraege):
        b.append(f"TD-G4 {name}: {luecken_quellen} LÜCKE-Quelle(n) im Blatt gegen "
                 f"{len(luecken_eintraege)} Lücken-Eintrag/-Einträge — "
                 f"jede LÜCKE-Zeile braucht genau einen Eintrag und umgekehrt")
    if luecken_eintraege and nur_keine:
        b.append(f"TD-G4 {name}: Lücken-Abschnitt sagt 'keine' UND trägt Einträge")
    if "Lücken" in teile and not luecken_eintraege and not nur_keine:
        b.append(f"TD-G4 {name}: Lücken-Abschnitt leer — 'keine' ausschreiben "
                 f"oder Einträge nennen")

    # --- TD-G5: Programm-Entscheidungen im GANZEN Blatt (auch Überzug/Prosa —
    # dort fiel ein falsches Datum bisher maschinell nicht auf, Befund 10.10.)
    if pe is not None:
        for m in re.finditer(r"Programm-Entscheidung (\d{1,2}\.\d{1,2}\.\d{4})", text):
            norm = ".".join(str(int(x)) for x in m.group(1).split("."))
            if norm not in pe:
                b.append(f"TD-G5 {name}: Programm-Entscheidung {m.group(1)} steht "
                         f"nicht in praesentationen/PROGRAMM-ENTSCHEIDUNGEN.md")
                break

    # --- TD-G5: Kopf-Verweise
    if wurzel is not None:
        for feld, ordner in (("Modul", "module"), ("Deck", "decks")):
            wert = kopf.get(feld, "—")
            if not wert or wert == "—":
                continue
            # Ein Termin kann zwei Bloecke tragen (T17: M9 + M09B). Dann steht
            # im Kopffeld jede Kennung einzeln, verbunden mit " + ".
            for teil in [t.strip() for t in wert.split(" + ") if t.strip()]:
                if not datei_da(wurzel, ordner, teil):
                    b.append(f"TD-G5 {name}: {feld} '{teil}' — keine Datei "
                             f"praesentationen/{ordner}/{teil}.md bzw. {teil}-*.md")
    return b


def selbsttest() -> int:
    import tempfile
    gut = """# T3 — Anatomie (Di)
Board-Zeit: 90 min
Plan-Zeit: 95 min
Badge: Workshop
Art: Workshop
Teilnehmer: Entwickler, Trainer
Modul: M2
Deck: T3-anatomie
Rolle: Operator
Level-Ziel: L2

## Ablauf
- 10 min — Ankommen, Win der Woche (Quelle: Board)
- 85 min — Session nach Deck (Quelle: Deck T3-anatomie; Modul M2)

## Ergebnis
- Die Anatomie sitzt (Quelle: Board)

## Vorbereitung
- Beamer prüfen (Quelle: LÜCKE)

## Requisiten
keine

## Lücken
- LÜCKE: Vorbereitung unklar, Entscheidung Trainer

## Überzug
Begründung: Sessions dürfen leicht über 90 laufen (Christian, 09.10.2026).
"""
    F: list[tuple[str, str, str | None]] = [
        ("gruen", gut, None),
        # Board-Spanne: früher ein Crash (ValueError), heute zwei Richtungen
        ("board-range-mit-ueberzug-gruen",
         gut.replace("Board-Zeit: 90 min", "Board-Zeit: 30–45 min"), None),
        ("board-range-ohne-ueberzug",
         gut.replace("Board-Zeit: 90 min", "Board-Zeit: 30–45 min")
            .replace("\n## Überzug\nBegründung: Sessions dürfen leicht "
                     "über 90 laufen (Christian, 09.10.2026).\n", "\n"), "TD-G3"),
        ("board-range-plan-drin-gruen",
         gut.replace("Board-Zeit: 90 min", "Board-Zeit: 90–120 min")
            .replace("\n## Überzug\nBegründung: Sessions dürfen leicht "
                     "über 90 laufen (Christian, 09.10.2026).\n", "\n"), None),
        ("board-stunden-gruen", gut.replace("Board-Zeit: 90 min", "Board-Zeit: 3 h")
                                   .replace("Plan-Zeit: 95 min", "Plan-Zeit: 180 min")
                                   .replace("- 85 min", "- 170 min"), None),
        ("board-plus-gruen", gut.replace("Board-Zeit: 90 min", "Board-Zeit: 90 + 30 min")
                                .replace("Plan-Zeit: 95 min", "Plan-Zeit: 120 min")
                                .replace("- 85 min", "- 110 min"), None),
        ("planzeit-strich", gut.replace("Plan-Zeit: 95 min", "Plan-Zeit: —"), "TD-G3"),
        ("planzeit-spanne", gut.replace("Plan-Zeit: 95 min", "Plan-Zeit: 90–95 min"), "TD-G3"),
        ("kopffeld-fehlt", gut.replace("Art: Workshop\n", ""), "TD-G1"),
        ("art-fremd", gut.replace("Art: Workshop", "Art: Webinar"), "TD-G1"),
        ("badge-leer", gut.replace("Badge: Workshop", "Badge: —"), "TD-G1"),
        ("rolle-fremd", gut.replace("Entwickler, Trainer", "Entwickler, Praktikant"), "TD-G1"),
        ("zeit-unlesbar", gut.replace("Board-Zeit: 90 min", "Board-Zeit: irgendwann"), "TD-G1"),
        ("abschnitt-fehlt", gut.replace("## Requisiten\nkeine\n", ""), "TD-G1"),
        ("ergebnis-fehlt", gut.replace("## Ergebnis\n- Die Anatomie sitzt (Quelle: Board)\n\n", ""), "TD-G1"),
        ("rolle-kopffeld-fehlt", gut.replace("Rolle: Operator\n", ""), "TD-G1"),
        ("prosa-zeile", gut.replace("- 10 min — Ankommen, Win der Woche (Quelle: Board)",
                                    "Ab 9:00 Uhr im Raum Alpha, dann Ankommen"), "TD-G2"),
        ("tabelle", gut.replace("- 10 min — Ankommen, Win der Woche (Quelle: Board)",
                                "| 10 min | Ankommen |"), "TD-G2"),
        ("eingerueckt", gut.replace("- 85 min — Session nach Deck "
                                    "(Quelle: Deck T3-anatomie; Modul M2)",
                                    "  - 85 min — Session (Quelle: Board)"), "TD-G2"),
        ("quelle-fremd", gut.replace("(Quelle: Board)", "(Quelle: Bauchgefühl)"), "TD-G2"),
        ("zeilenquelle-tot", gut.replace("Deck T3-anatomie; Modul M2",
                                         "Deck gibt-es-nicht"), "TD-G5"),
        ("summe-falsch", gut.replace("- 85 min", "- 80 min"), "TD-G3"),
        ("ueberzug-fehlt", gut.replace("\n## Überzug\nBegründung: Sessions dürfen leicht "
                                       "über 90 laufen (Christian, 09.10.2026).\n", "\n"), "TD-G3"),
        ("ueberzug-ohne-begruendung", gut.replace("Begründung: Sessions dürfen leicht "
                                                  "über 90 laufen (Christian, 09.10.2026).",
                                                  "x"), "TD-G3"),
        ("luecke-ungespiegelt", gut.replace("- LÜCKE: Vorbereitung unklar, "
                                            "Entscheidung Trainer", "keine"), "TD-G4"),
        ("phantom-luecke", gut.replace("- LÜCKE: Vorbereitung unklar, Entscheidung Trainer",
                                       "- LÜCKE: Vorbereitung unklar, Entscheidung Trainer\n"
                                       "- LÜCKE: noch was Erfundenes"), "TD-G4"),
        ("luecken-leer", gut.replace("- LÜCKE: Vorbereitung unklar, Entscheidung Trainer\n",
                                     "").replace("(Quelle: LÜCKE)", "(Quelle: Board)"), "TD-G4"),
        ("tagid-fremd", gut, "TD-G5"),
        ("modul-praefix", gut.replace("Modul: M2", "Modul: M1"), "TD-G5"),
        ("modul-kurzform-gruen", gut, None),
        ("pe-im-register-gruen", gut.replace("(Quelle: Board)",
                                             "(Quelle: Programm-Entscheidung 9.10.2026)"), None),
        ("pe-nicht-im-register", gut.replace("(Quelle: Board)",
                                             "(Quelle: Programm-Entscheidung 1.1.2020)"), "TD-G5"),
        ("pe-falsch-im-ueberzug", gut.replace(
            "Begründung: Sessions dürfen leicht über 90 laufen (Christian, 09.10.2026).",
            "Begründung: Programm-Entscheidung 1.1.2020 deckt das ab."), "TD-G5"),
    ]
    fehler = 0
    with tempfile.TemporaryDirectory() as td:
        w = Path(td)
        (w / "praesentationen" / "module").mkdir(parents=True)
        (w / "praesentationen" / "decks").mkdir(parents=True)
        for n in ("M02-anatomie.md", "M10-abschluss.md"):
            (w / "praesentationen" / "module" / n).write_text("x", encoding="utf-8")
        (w / "praesentationen" / "decks" / "T3-anatomie.md").write_text("x", encoding="utf-8")
        (w / "praesentationen" / "PROGRAMM-ENTSCHEIDUNGEN.md").write_text(
            "## PE-2026-10-09 · Test\n", encoding="utf-8")
        for name, inhalt, erwartet in F:
            datei = w / ("X9.md" if name == "tagid-fremd" else "T3.md")
            datei.write_text(inhalt, encoding="utf-8")
            bef = pruefe_blatt(datei, w)
            ok = (not bef) if erwartet is None else any(x.startswith(erwartet) for x in bef)
            if not ok:
                fehler += 1
                print(f"SELBSTTEST ROT: {name} — erwartet {erwartet or 'grün'}, "
                      f"bekam: {bef or 'nichts'}")
            datei.unlink()
    print(f"Selbsttest: {len(F) - fehler}/{len(F)} grün")
    return 0 if fehler == 0 else 1


def main() -> int:
    args = list(sys.argv[1:])
    if "--selbsttest" in args:
        return selbsttest()
    ausloeser, erwartet = "cli", []
    for flag, ziel in (("--ausloeser", "a"), ("--erwartet", "e")):
        if flag in args:
            i = args.index(flag)
            wert = args[i + 1] if i + 1 < len(args) else ""
            del args[i:i + 2 if wert else i + 1]
            if ziel == "a":
                ausloeser = wert or "cli"
            else:
                erwartet = [t.strip() for t in wert.split(",") if t.strip()]
    if not args:
        print("Aufruf: tagesdetail_pruefen.py <blatt.md|ordner> "
              "[--erwartet T1,T2] | --selbsttest")
        return 2
    ziel = Path(args[0])
    if not ziel.exists():
        print(f"Nicht gefunden: {ziel}")
        return 2
    dateien = sorted(ziel.glob("*.md")) if ziel.is_dir() else [ziel]
    w = gemeinsam.wurzel(ziel.resolve())
    befunde: list[str] = []
    for d in dateien:
        try:
            befunde += pruefe_blatt(d, w)
        except Exception as e:  # ein kaputtes Blatt darf den Lauf nicht killen
            befunde.append(f"TD-G1 {d.name}: Blatt nicht prüfbar ({type(e).__name__}: {e})")
    if erwartet:
        da = {d.stem for d in dateien}
        for tag in erwartet:
            if tag not in da:
                befunde.append(f"TD-G5 Soll-Ist: Blatt '{tag}.md' fehlt im Ordner")
    gemeinsam.spur(w, "gate", werkzeug="tagesdetail_pruefen",
                   ausloeser=ausloeser, dateien=len(dateien), befunde=len(befunde))
    if befunde:
        print("\n".join(befunde))
        print(f"{len(befunde)} Befunde")
        return 1
    print("0 Befunde")
    return 0


if __name__ == "__main__":
    sys.exit(main())
