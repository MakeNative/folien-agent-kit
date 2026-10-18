#!/usr/bin/env python3
"""Maschinengate der Formular-Straße (Regeln FB-01..FB-05).

Prüft praesentationen/eval/ gegen den Board-Abzug:
  FB-G1  Spezifikations-Format: je Bogen Slug, Name, Kopf-Beschreibung,
         Anonym-Zeile, nummerierte Felder mit Feldtyp
  FB-G2  Board-Treue VOR dem Bau: jeder Fragetext in Anführungszeichen,
         der nicht als *Setzung* markiert ist, muss WÖRTLICH im
         BOARD-ABZUG.md stehen (Zitat-Abgleich, der die Spez prüft,
         bevor irgendetwas in Notion entsteht)
  FB-G3  Schutzregeln: anonyme Bögen ohne Personenfeld; die drei
         T20-Freigaben als drei getrennte Felder; GF-Kurzvariante als
         eigener Bogen; Auswertungsregeln nur im internen Block
  FB-G4  Baulog: je gebautem Bogen eine Zeile mit ISO-Datum und URL
  FB-G5  Freigabe-Konsistenz: striktes Zeilenformat, nur bekannte
         Slugs, Stand-Datum == Datum der letzten Baulog-Zeile dieses
         Bogens (Regenerations-Schutz: ein neuer Bau entwertet die
         Freigabe maschinell)

Aufruf: formular_pruefen.py <eval-ordner|datei> [--ausloeser hook|cli]
        formular_pruefen.py --selbsttest
Exit 0 = still & grün, 1 = Befunde, 2 = Fehler.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gemeinsam  # noqa: E402

SLUG_RE = re.compile(r"^## Bogen: ([a-z0-9-]+)\s*$")
FELD_RE = re.compile(r"^\d+\. (.+)$")
BAULOG_RE = re.compile(r"^([a-z0-9-]+) — gebaut (\d{4}-\d{2}-\d{2}) — (\S+)")
FREIGABE_RE = re.compile(
    r"^([a-z0-9-]+)\s*[—–-]+\s*(freigegeben|abgelehnt)\b(.*)$", re.I)
STAND_RE = re.compile(r"Stand\s+(\d{4}-\d{2}-\d{2})")
ZITAT_RE = re.compile('[„"]([^„"]{6,200})[""]')
SETZUNG_MARKER = ("*Setzung", "(Feldtyp Setzung", "Setzung —", "*Aufteilung")
PERSONENFELD = ("name", "mail", "e-mail", "person", "entwickler", "mitarbeiter")


def board_text(wurzel: Path) -> str:
    p = wurzel / "praesentationen" / "BOARD-ABZUG.md"
    if not p.exists():
        return ""
    t = p.read_text(encoding="utf-8")
    # Anführungsformen vereinheitlichen, damit der Abgleich nicht an der
    # Typografie scheitert (das Repo mischt „…" und „…“).
    return t.replace("“", '"').replace("”", '"').replace("„", '"')


def spez_bloecke(text: str) -> dict[str, list[str]]:
    bloecke: dict[str, list[str]] = {}
    aktiv = None
    for z in text.splitlines():
        m = SLUG_RE.match(z)
        if m:
            aktiv = m.group(1)
            bloecke[aktiv] = []
        elif aktiv:
            bloecke[aktiv].append(z)
    return bloecke


def pruefe_spez(pfad: Path, wurzel: Path | None) -> tuple[list[str], dict[str, list[str]]]:
    b: list[str] = []
    text = pfad.read_text(encoding="utf-8")
    bloecke = spez_bloecke(text)
    if not bloecke:
        b.append("FB-G1 FORMULAR-SPEZ.md: kein Block '## Bogen: <slug>' gefunden")
        return b, bloecke
    board = board_text(wurzel) if wurzel else ""
    if wurzel and not board:
        b.append("FB-G2 BOARD-ABZUG.md nicht gefunden — Board-Treue nicht prüfbar")

    for slug, zeilen in bloecke.items():
        block = "\n".join(zeilen)
        for pflicht, muster in (("Name:", r"^Name: \S"),
                                ("Kopf-Beschreibung:", r"^Kopf-Beschreibung: \S"),
                                ("Anonym:", r"^Anonym: (JA|NEIN)\b")):
            if not re.search(muster, block, re.M):
                b.append(f"FB-G1 {slug}: Zeile '{pflicht}' fehlt oder unvollständig")
        felder = [m.group(1) for m in (FELD_RE.match(z.strip()) for z in zeilen) if m]
        if not felder:
            b.append(f"FB-G1 {slug}: keine nummerierten Felder")
        for f in felder:
            if " — " not in f:
                b.append(f"FB-G1 {slug}: Feld ohne Feldtyp (Format "
                         f"'<Frage> — <Feldtyp>, <Pflicht/optional>'): {f[:60]}")

        # FB-G2: Board-Treue der Zitate
        if board:
            for zeile in zeilen:
                if any(mark in zeile for mark in SETZUNG_MARKER):
                    continue
                if not FELD_RE.match(zeile.strip()):
                    continue
                for zitat in ZITAT_RE.findall(zeile.replace("“", '"')
                                              .replace("”", '"').replace("„", '"')):
                    z = zitat.strip()
                    if len(z) < 8:
                        continue
                    if z not in board:
                        kurz = (z[:60] + "…") if len(z) > 60 else z
                        b.append(f"FB-G2 {slug}: Zitat „{kurz}\" steht nicht "
                                 f"wörtlich im BOARD-ABZUG.md (Fragetext "
                                 f"korrigieren oder als *Setzung* kennzeichnen)")

        # FB-G3: Schutzregeln
        anonym = re.search(r"^Anonym: JA\b", block, re.M)
        if anonym:
            for f in felder:
                kopf = f.split("—")[0].lower()
                if any(p in kopf for p in PERSONENFELD):
                    b.append(f"FB-G3 {slug}: anonymer Bogen mit Personenfeld "
                             f"'{f.split('—')[0].strip()[:40]}'")
            if re.search(r"^Personenfeld:", block, re.M):
                b.append(f"FB-G3 {slug}: anonymer Bogen nennt ein Personenfeld")
        if "abschluss-eval-t20" == slug:
            freigaben = [f for f in felder if f.lower().startswith("freigabe")]
            if len(freigaben) != 3:
                b.append(f"FB-G3 {slug}: {len(freigaben)} Freigabe-Felder — die "
                         f"Testimonial-Freigaben (a)(b)(c) müssen drei getrennte "
                         f"Checkbox-Felder sein")
            if any("zusammenarbeit" in f.lower() for f in felder):
                b.append(f"FB-G3 {slug}: GF-Fragen im Entwickler-Bogen — die "
                         f"GF-Kurzvariante ist ein eigener Bogen")
        if re.search(r"^\d+\..*(Score ≤ 3|Ampellogik|geht nur an uns)", block,
                     re.M | re.I):
            b.append(f"FB-G3 {slug}: Auswertungsregel steht als Feld im sichtbaren "
                     f"Bogen — sie gehört in den Block 'Auswertung (intern)'")
    if "gf-kurzvariante-t20" in bloecke and "abschluss-eval-t20" not in bloecke:
        b.append("FB-G3 Spez nennt die GF-Kurzvariante ohne den Entwickler-Bogen")
    return b, bloecke


def pruefe_freigabe(ordner: Path, slugs: set[str]) -> list[str]:
    b: list[str] = []
    baulog = ordner / "BAULOG.md"
    freigabe = ordner / "FORMULAR-FREIGABE.md"
    gebaut: dict[str, str] = {}
    if baulog.exists():
        for z in baulog.read_text(encoding="utf-8").splitlines():
            s = z.strip()
            if not s or s.startswith("#"):
                continue
            m = BAULOG_RE.match(s)
            if not m:
                b.append(f"FB-G4 BAULOG.md: Zeile ohne Format "
                         f"'<slug> — gebaut <YYYY-MM-DD> — <URL>': {s[:60]}")
                continue
            if m.group(1) not in slugs:
                b.append(f"FB-G4 BAULOG.md: unbekannter Bogen-Slug '{m.group(1)}'")
            gebaut[m.group(1)] = m.group(2)  # letzte Zeile gewinnt
    if not freigabe.exists():
        return b
    letzte: dict[str, tuple[str, str]] = {}
    for z in freigabe.read_text(encoding="utf-8").splitlines():
        s = z.strip()
        if not s or s.startswith("#"):
            continue
        m = FREIGABE_RE.match(s)
        if not m:
            b.append(f"FB-G5 FORMULAR-FREIGABE.md: Zeile nicht im strikten Format "
                     f"'<slug> — freigegeben (Stand …)' / '<slug> — ABGELEHNT: …': "
                     f"{s[:60]}")
            continue
        letzte[m.group(1)] = (m.group(2).lower(), m.group(3))
    for slug, (urteil, rest) in letzte.items():
        if slug not in slugs:
            b.append(f"FB-G5 Freigabe für unbekannten Bogen '{slug}'")
            continue
        if urteil != "freigegeben":
            continue
        if slug not in gebaut:
            b.append(f"FB-G5 {slug}: freigegeben, aber keine BAULOG-Zeile "
                     f"(ohne Bau keine Freigabe)")
            continue
        m = STAND_RE.search(rest)
        if not m:
            b.append(f"FB-G5 {slug}: Freigabe ohne 'Stand <YYYY-MM-DD>'")
        elif m.group(1) != gebaut[slug]:
            b.append(f"FB-G5 {slug}: Freigabe-Stand {m.group(1)} ≠ letzte "
                     f"BAULOG-Zeile {gebaut[slug]} — nach einem Neubau verfällt "
                     f"die Freigabe und muss neu erteilt werden")
        if "http" not in rest:
            b.append(f"FB-G5 {slug}: Freigabe ohne Notion-URL")
    return b


def pruefe(ziel: Path, wurzel: Path | None) -> list[str]:
    ordner = ziel if ziel.is_dir() else ziel.parent
    spez = ordner / "FORMULAR-SPEZ.md"
    if not spez.exists():
        return [f"FB-G1 {ordner}/FORMULAR-SPEZ.md fehlt — ohne Spezifikation "
                f"wird nichts gebaut (FB-01)"]
    b, bloecke = pruefe_spez(spez, wurzel)
    b += pruefe_freigabe(ordner, set(bloecke))
    return b


def selbsttest() -> int:
    import tempfile
    board = ('## Badge\n- Sentiment 1–5: "Wie fühlt sich die neue Arbeitsweise an?"\n'
             '- Bester Moment der Woche · Größter Reibungspunkt\n'
             '- NPS 0–10: "Würdest du das Programm einem Kollegen empfehlen?"\n'
             '- Freigabe GETRENNT ankreuzbar: (a) Zitat anonymisiert · '
             '(b) Zitat mit Name/Firma · (c) Zahlen als Referenz (A15)\n')
    spez_gut = """# Spez
## Bogen: starter-pulse-s5
Name: Starter-Pulse — S5
Kopf-Beschreibung: am letzten Tag · 2 min · anonym
Anonym: JA

Felder:
1. „Wie fühlt sich die neue Arbeitsweise an?" — Select 1–5, Pflicht
2. „Bester Moment der Woche" — Freitext, optional

## Bogen: abschluss-eval-t20
Name: Abschluss-Evaluation — T20
Kopf-Beschreibung: im Termin
Anonym: NEIN
Personenfeld: Entwickler

Felder:
1. „Würdest du das Programm einem Kollegen empfehlen?" — Select 0–10, Pflicht
2. Freigabe (a): „Zitat anonymisiert" — Checkbox
3. Freigabe (b): „Zitat mit Name/Firma" — Checkbox
4. Freigabe (c): „Zahlen als Referenz (A15)" — Checkbox
"""
    F: list[tuple[str, dict[str, str], str | None]] = [
        ("gruen", {"FORMULAR-SPEZ.md": spez_gut}, None),
        ("kein-slug", {"FORMULAR-SPEZ.md": "# Spez\nkeine Bloecke\n"}, "FB-G1"),
        ("anonym-zeile-fehlt",
         {"FORMULAR-SPEZ.md": spez_gut.replace("Anonym: JA\n", "")}, "FB-G1"),
        ("feld-ohne-typ",
         {"FORMULAR-SPEZ.md": spez_gut.replace(
             '1. „Wie fühlt sich die neue Arbeitsweise an?" — Select 1–5, Pflicht',
             '1. „Wie fühlt sich die neue Arbeitsweise an?"')}, "FB-G1"),
        ("zitat-nicht-im-board",
         {"FORMULAR-SPEZ.md": spez_gut.replace(
             "Wie fühlt sich die neue Arbeitsweise an?",
             "Wie geht es dir heute?")}, "FB-G2"),
        ("setzung-erlaubt",
         {"FORMULAR-SPEZ.md": spez_gut.replace(
             '2. „Bester Moment der Woche" — Freitext, optional',
             '2. „Frei erfundene Zusatzfrage" — Freitext, optional '
             '*Setzung (Orchestrator)*')}, None),
        ("anonym-mit-personenfeld",
         {"FORMULAR-SPEZ.md": spez_gut.replace(
             "Anonym: JA\n", "Anonym: JA\nPersonenfeld: Entwickler\n")}, "FB-G3"),
        ("freigaben-nur-zwei",
         {"FORMULAR-SPEZ.md": spez_gut.replace(
             '4. Freigabe (c): „Zahlen als Referenz (A15)" — Checkbox\n', "")}, "FB-G3"),
        ("gf-fragen-im-dev-bogen",
         {"FORMULAR-SPEZ.md": spez_gut + '5. „Zusammenarbeit" — Select 1–5\n'}, "FB-G3"),
        ("regel-als-feld",
         {"FORMULAR-SPEZ.md": spez_gut + '5. Score ≤ 3 → 1:1 — Select\n'}, "FB-G3"),
        ("baulog-formlos",
         {"FORMULAR-SPEZ.md": spez_gut,
          "BAULOG.md": "starter-pulse-s5 gebaut gestern\n"}, "FB-G4"),
        ("baulog-fremder-slug",
         {"FORMULAR-SPEZ.md": spez_gut,
          "BAULOG.md": "gibt-es-nicht — gebaut 2026-10-10 — https://notion.so/x\n"}, "FB-G4"),
        ("freigabe-formlos",
         {"FORMULAR-SPEZ.md": spez_gut,
          "FORMULAR-FREIGABE.md": "starter-pulse-s5 ist ok\n"}, "FB-G5"),
        ("freigabe-ohne-bau",
         {"FORMULAR-SPEZ.md": spez_gut,
          "FORMULAR-FREIGABE.md": "starter-pulse-s5 — freigegeben "
                                  "(Stand 2026-10-10, https://notion.so/x, geprüft)\n"},
         "FB-G5"),
        ("freigabe-stand-veraltet",
         {"FORMULAR-SPEZ.md": spez_gut,
          "BAULOG.md": "starter-pulse-s5 — gebaut 2026-10-10 — https://notion.so/x\n"
                       "starter-pulse-s5 — gebaut 2026-10-11 — https://notion.so/x\n",
          "FORMULAR-FREIGABE.md": "starter-pulse-s5 — freigegeben "
                                  "(Stand 2026-10-10, https://notion.so/x, geprüft)\n"},
         "FB-G5"),
        ("freigabe-gueltig-gruen",
         {"FORMULAR-SPEZ.md": spez_gut,
          "BAULOG.md": "starter-pulse-s5 — gebaut 2026-10-11 — https://notion.so/x\n",
          "FORMULAR-FREIGABE.md": "starter-pulse-s5 — freigegeben "
                                  "(Stand 2026-10-11, https://notion.so/x, geprüft)\n"},
         None),
        ("abgelehnt-gruen",
         {"FORMULAR-SPEZ.md": spez_gut,
          "FORMULAR-FREIGABE.md": "starter-pulse-s5 — ABGELEHNT: 1) Feld fehlt\n"}, None),
        ("freigabe-ohne-url",
         {"FORMULAR-SPEZ.md": spez_gut,
          "BAULOG.md": "starter-pulse-s5 — gebaut 2026-10-11 — https://notion.so/x\n",
          "FORMULAR-FREIGABE.md": "starter-pulse-s5 — freigegeben "
                                  "(Stand 2026-10-11, geprüft)\n"}, "FB-G5"),
    ]
    fehler = 0
    with tempfile.TemporaryDirectory() as td:
        w = Path(td)
        (w / "praesentationen" / "eval").mkdir(parents=True)
        (w / "praesentationen" / "BOARD-ABZUG.md").write_text(board, encoding="utf-8")
        ordner = w / "praesentationen" / "eval"
        for name, dateien, erwartet in F:
            for f in ordner.glob("*.md"):
                f.unlink()
            for dn, inhalt in dateien.items():
                (ordner / dn).write_text(inhalt, encoding="utf-8")
            bef = pruefe(ordner, w)
            ok = (not bef) if erwartet is None else any(x.startswith(erwartet) for x in bef)
            if not ok:
                fehler += 1
                print(f"SELBSTTEST ROT: {name} — erwartet {erwartet or 'grün'}, "
                      f"bekam: {bef or 'nichts'}")
    print(f"Selbsttest: {len(F) - fehler}/{len(F)} grün")
    return 0 if fehler == 0 else 1


def main() -> int:
    args = list(sys.argv[1:])
    if "--selbsttest" in args:
        return selbsttest()
    ausloeser = "cli"
    if "--ausloeser" in args:
        i = args.index("--ausloeser")
        ausloeser = args[i + 1] if i + 1 < len(args) else "cli"
        del args[i:i + 2]
    if not args:
        print("Aufruf: formular_pruefen.py <eval-ordner|datei> | --selbsttest")
        return 2
    ziel = Path(args[0])
    if not ziel.exists():
        print(f"Nicht gefunden: {ziel}")
        return 2
    w = gemeinsam.wurzel(ziel.resolve())
    try:
        befunde = pruefe(ziel, w)
    except Exception as e:
        print(f"Gate-Fehler: {type(e).__name__}: {e}")
        return 2
    gemeinsam.spur(w, "gate", werkzeug="formular_pruefen",
                   ausloeser=ausloeser, befunde=len(befunde))
    if befunde:
        print("\n".join(befunde))
        print(f"{len(befunde)} Befunde")
        return 1
    print("0 Befunde")
    return 0


if __name__ == "__main__":
    sys.exit(main())
