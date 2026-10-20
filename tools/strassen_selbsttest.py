#!/usr/bin/env python3
"""Selbsttest der Agenten-Strassen: Agenten, Skills und Gates.

    strassen_selbsttest.py [kit-wurzel]

Exit 0, wenn alle Erwartungen erfuellt sind. Kein Netz, keine Modelllaeufe —
geprueft wird, was sich ohne Sitzung pruefen laesst:

  A  Agenten-Dateien sind wohlgeformt und widersprechen sich nicht
  B  Skills nennen nur Werkzeuge und Agenten, die es gibt
  C  Die Gates melden gruen auf gutem Material und rot auf schlechtem
  D  Die Strassen sind untereinander stimmig

Das faengt nicht, ob ein Agent gute Arbeit macht. Es faengt, ob die
Strasse ueberhaupt laufen kann — und genau das ist in dieser Woche
dreimal still kaputt gewesen.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HIER = Path(__file__).resolve().parent
KIT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else HIER.parent

ok, fehlt = 0, []


def erwarte(name: str, bedingung: bool, grund: str = "") -> None:
    global ok
    if bedingung:
        ok += 1
    else:
        fehlt.append(f"{name}{'  — ' + grund if grund else ''}")


def frontmatter(p: Path) -> dict:
    t = p.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", t, re.S)
    if not m:
        return {}
    d: dict[str, str] = {}
    for z in m.group(1).splitlines():
        mm = re.match(r"^([a-zA-Z]+):\s*(.*)$", z)
        if mm:
            d[mm.group(1)] = mm.group(2).strip().strip('"')
    return d


# ───────────────────────────── A · Agenten ──────────────────────────────
for p in sorted((KIT / "agents").glob("*.md")):
    fm = frontmatter(p)
    erwarte(f"A1 {p.name}: Frontmatter", bool(fm))
    erwarte(f"A2 {p.name}: name == Dateiname",
            fm.get("name") == p.stem, f"name={fm.get('name')!r}")
    erwarte(f"A3 {p.name}: description vorhanden", bool(fm.get("description")))
    erwarte(f"A4 {p.name}: tools gesetzt", bool(fm.get("tools")))
    werkzeuge = {x.strip() for x in fm.get("tools", "").split(",") if x.strip()}
    verboten = {x.strip() for x in fm.get("disallowedTools", "").split(",") if x.strip()}
    erwarte(f"A5 {p.name}: tools und disallowedTools ueberschneiden sich nicht",
            not (werkzeuge & verboten), f"doppelt: {sorted(werkzeuge & verboten)}")
    # Wer laut Beschreibung nichts aendert, darf nicht editieren duerfen.
    beschr = fm.get("description", "")
    # „aendert nichts" heisst etwas anderes als „aendert kein Deck" — der
    # Bauer darf schreiben, nur eben keine Decks. (Eigener Testfehler,
    # gefunden beim ersten Lauf dieses Selbsttests, 20.10.2026.)
    # Nur die eindeutigen Formulierungen: „aendert nichts" und „repariert
    # nichts" meinen Dateien. „erzeugt nichts" meint beim asset-planner
    # keine ASSETS — er schreibt sehr wohl seinen Plan. (Zweiter eigener
    # Testfehler desselben Laufs.)
    if re.search(r"(aendert|ändert) nichts|repariert nichts", beschr):
        erwarte(f"A6 {p.name}: aendert nichts ⇒ kein Edit",
                "Edit" not in werkzeuge, "Edit steht in tools")

# ───────────────────────────── B · Skills ───────────────────────────────
agentennamen = {p.stem for p in (KIT / "agents").glob("*.md")}
for p in sorted((KIT / "skills").glob("*/SKILL.md")):
    fm = frontmatter(p)
    t = p.read_text(encoding="utf-8")
    erwarte(f"B1 {p.parent.name}: Frontmatter", bool(fm))
    erwarte(f"B2 {p.parent.name}: name == Ordnername",
            fm.get("name") == p.parent.name, f"name={fm.get('name')!r}")
    for werkzeug in set(re.findall(r"tools/([a-z_]+\.py)", t)):
        erwarte(f"B3 {p.parent.name}: Werkzeug {werkzeug} existiert",
                (KIT / "tools" / werkzeug).exists())
    for agent in set(re.findall(r"[Ss]pawn `?([a-z-]+)`?", t)):
        erwarte(f"B4 {p.parent.name}: Agent {agent} existiert",
                agent in agentennamen, f"bekannt: {sorted(agentennamen)[:3]}…")

# ───────────────────────────── C · Gates ────────────────────────────────
GUT = {
    "deck": "S9-probe",
    "stand": "2026-10-20",
    "requisiten": [
        {"folie": 1, "braucht": "Ein Blatt", "art": "vorlage",
         "datei": "vorlagen/blatt.md", "herkunft": "TAGESBLATT Requisiten"},
        {"folie": 2, "braucht": "Der Lauf", "art": "datei",
         "herkunft": "F2 TUN",
         "hinweis": "liegt im Vorführprojekt: laeufe/ — die Mappe bringt es mit"},
    ],
}

def requisiten_gate(manifest: dict, deck: str | None = None,
                    streng: bool = True) -> str:
    with tempfile.TemporaryDirectory() as td:
        w = Path(td)
        sess = w / "sessions" / "S9"
        (sess / "requisiten" / "vorlagen").mkdir(parents=True)
        (sess / "requisiten" / "vorlagen" / "blatt.md").write_text("x", encoding="utf-8")
        (sess / "requisiten" / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
        if deck is not None:
            (sess / "S9-probe.md").write_text(deck, encoding="utf-8")
        befehl = [sys.executable, str(KIT / "tools" / "requisiten_pruefen.py"), str(w)]
        if not streng:
            befehl.append("--nachsichtig")
        return subprocess.run(befehl, capture_output=True, text=True).stdout

aus = requisiten_gate(GUT)
erwarte("C1 gutes Manifest ⇒ 0 Befunde", "0 Befund(e)" in aus, aus.splitlines()[0] if aus else "")

schlecht = json.loads(json.dumps(GUT))
schlecht["requisiten"][0]["datei"] = "vorlagen/gibtsnicht.md"
erwarte("C2 fehlende Datei ⇒ Befund",
        "existiert nicht" in requisiten_gate(schlecht))

vorort = json.loads(json.dumps(GUT))
vorort["requisiten"][0]["hinweis"] = "liegt auf den Plätzen bereit"
erwarte("C3 Vor-Ort-Rest ⇒ Befund",
        "Vor-Ort-Rest" in requisiten_gate(vorort))

falsch = json.loads(json.dumps(GUT))
falsch["requisiten"][0]["art"] = "zettelchen"
erwarte("C4 unbekannte Art ⇒ Befund", "keine der" in requisiten_gate(falsch))

erwarte("C5 art=datei ohne Datei ist erlaubt, wenn der Hinweis das "
        "Vorfuehrprojekt nennt", "ohne Datei" not in aus)

ohne_hinweis = json.loads(json.dumps(GUT))
del ohne_hinweis["requisiten"][1]["hinweis"]
erwarte("C6 art=datei ohne Datei UND ohne Verweis ⇒ Befund",
        "ohne Datei" in requisiten_gate(ohne_hinweis))

ohne_herkunft = json.loads(json.dumps(GUT))
del ohne_herkunft["requisiten"][0]["herkunft"]
erwarte("C7 fehlende Herkunft ⇒ Befund im strengen Modus",
        "keine Herkunft" in requisiten_gate(ohne_herkunft))
erwarte("C8 fehlende Herkunft ⇒ nur Hinweis mit --nachsichtig",
        "0 Befund(e)" in requisiten_gate(ohne_herkunft, streng=False))

DECK_MIT_MARKE = (
    "## Folie 5: Eine Probe (~2 min)\n\nTyp: D\n\n"
    "Demo: ~2 min. Etwas liegt bereit (*Requisit.*).\n\nKERN: x\n")
erwarte("C9 *Requisit.*-Marke ohne Eintrag ⇒ Befund",
        "kein Eintrag im Manifest" in requisiten_gate(GUT, deck=DECK_MIT_MARKE))

# ─────────────────────────── D · Stimmigkeit ────────────────────────────
vp = (KIT / "tools" / "vorfuehrprojekt_pruefen.py").read_text(encoding="utf-8")
erwarte("D1 Vorfuehrprojekt-Gate kennt den Pruefstein",
        "deliveryRetryPolicy" in vp)
erwarte("D2 Vorfuehrprojekt-Gate prueft die beiden Vorlauf-Zweige",
        "vorlauf/queue-uebersicht" in vp and "vorlauf/adresspruefung" in vp)
erwarte("D3 requisiten-Strasse und kundenprojekt-Strasse teilen den Validator",
        "requisiten-validator" in (KIT / "skills" / "kundenprojekt" / "SKILL.md").read_text(encoding="utf-8"))
for datei in ("repo-leser.md", "aufgaben-schneider.md"):
    erwarte(f"D4 {datei} liegt im Kit", (KIT / "agents" / datei).exists())
erwarte("D5 kein Repo-Name in einer Agenten-Datei",
        not any(re.search(r"bayerninfo2|findpenguins", p.read_text(encoding="utf-8"))
                for p in (KIT / "agents").glob("*.md")
                if p.stem not in ("repo-leser", "aufgaben-schneider")),
        "ein Fix, der einen Repo-Namen enthaelt, ist keiner")

# ──────────────── E · Die Lehren der Laeufe bleiben drin ─────────────────
# Ein Fix, den kein Test festhaelt, verschwindet beim naechsten Umbau.
leser = (KIT / "agents" / "repo-leser.md").read_text(encoding="utf-8")
schneider = (KIT / "agents" / "aufgaben-schneider.md").read_text(encoding="utf-8")

erwarte("E1 Lauf 2 · zweiter Weg fuer T3 F10 ohne Anweisungsdatei",
        "durch seine Struktur belegt" in leser,
        "das zweite Repo hatte gar keine Anweisungsdatei")
erwarte("E1b Lauf 2 · Verstoesse werden gezaehlt, drei Faelle unterschieden",
        "Zähl immer die Verstöße" in leser and "am besten" in leser,
        "eine Regel mit wenigen Verstoessen IST die Erosion")
erwarte("E1c Lauf 2 · die Strukturregel wird gegengeprueft",
        "nicht leer ist" in leser,
        "das Verbotene muss im Projekt woanders vorkommen")
erwarte("E2 Lauf 2 · die Historie wird geprueft, nicht angenommen",
        "statt es anzunehmen" in leser,
        "in Lauf 2 trug kein einziger Commit-Betreff eine Vorgangsnummer")
erwarte("E3 Lauf 2 · Testpfade sind kein Ziel fuer eine Lesefrage",
        "Testpfade aus" in leser,
        "in Lauf 2 waren die drei groessten eigenen Dateien Testdateien")
erwarte("E4 Lauf 2 · der Schneider erfindet keine Regel",
        "Erfinde keine Regel" in schneider)
erwarte("E5 Lauf 1 · Testbereich der Zieldatei vorher fahren",
        "Testbereich" in schneider and "gruen" in schneider.lower().replace("ü","ue"))
erwarte("E5b Lauf 2 · der Testbefehl wird nicht geraten",
        "rate den Befehl nicht" in leser,
        "in Lauf 2 war der naheliegende Aufgabenname falsch")
erwarte("E5c Lauf 2 · ein frischer Klon ist nicht lauffaehig",
        "nicht lauffähig" in leser and "nachgereicht" in leser,
        "unversionierte Konfiguration fuer den Testlauf nachholen")
erwarte("E5d Lauf 2 · die nachgereichte Konfiguration kommt in keinen Bericht",
        "Nichts davon kommt in einen Bericht" in leser)
erwarte("E6 beide Agenten arbeiten auf einem Klon",
        "Klon" in leser and "Klon" in schneider,
        "nie im Arbeitsverzeichnis des Kunden")
_BED = (KIT.parent.parent / "Documents/agentic-coding-guide/praesentationen"
        / "BEDARFE.md")
_bed = _BED.read_text(encoding="utf-8") if _BED.exists() else ""
erwarte("E7 BEDARFE traegt die Auflage aus Lauf 1 zu T0 F11",
        not _bed or ("vorher einmal gefahren" in _bed
                     and "Fehlschlag darin muss der des" in _bed),
        "Zieldatei vorher gefahren, jeder Fehlschlag darin gehoert zum Ticket")
erwarte("E7b die Auflage unterscheidet fremdes Rot von dem des Tickets",
        not _bed or ("TS-4871" in _bed and "erwünscht" in _bed),
        "sonst widerspricht die Regel dem Vorfuehrprojekt, das genau eine "
        "rote Probe absichtlich mitbringt")
erwarte("E7c der repo-leser trennt beide Arten von rot",
        "Unterscheide zwei Arten von rot" in leser
        and "Melde beide getrennt" in leser)

# ──────── E2 · Das Board hat DREI Seiten (Lehre vom 20.10.) ─────────────
# „Detail pro Tag" war nie abgezogen, obwohl sie woertlich die Ebene
# beschreibt, die die Tagesdetail-Strasse schreibt. Rund die Haelfte der
# 110 gemeldeten Luecken stand dort schon beantwortet. Diese Erwartungen
# halten fest, dass die Strasse die Seite kennt — und dass sie
# Widersprueche zwischen den Board-Seiten als Befund behandelt.
def _flach(pfad):
    """Markdown-Umbrueche weg: ein Satz darf ueber zwei Zeilen stehen."""
    return " ".join((KIT / pfad).read_text(encoding="utf-8").split())

_tdw = _flach("agents/tagesdetail-writer.md")
_btp = _flach("agents/board-treue-pruefer.md")
_tds = _flach("skills/tagesdetail/SKILL.md")

erwarte("E8 der tagesdetail-writer kennt DETAIL-ABZUG.md",
        "DETAIL-ABZUG.md" in _tdw,
        "sonst belegt er die Durchfuehrungs-Ebene wieder aus Deck und Modul")
erwarte("E8b und liest sie ZUERST, nicht zuletzt",
        "Fang hier an" in _tdw and "die erste Quelle" in _tdw)
erwarte("E8c der writer entscheidet Board-Widersprueche nicht selbst",
        "ist das ein Befund, keine Wahl" in _tdw and "nennst beide Wortlaute" in _tdw)
erwarte("E9 der board-treue-pruefer prueft BEIDE Board-Seiten",
        "DETAIL-ABZUG.md" in _btp and "Pr\u00fcf beide Seiten" in _btp,
        "ein Befund aus nur der Uebersicht ist ein Fehlalarm")
erwarte("E9b und meldet Widersprueche zwischen den Seiten als Befund",
        "Widerspr\u00fcche zwischen den Board-Seiten" in _btp)
erwarte("E10 die Skill zaehlt die Board-Seiten, statt eine zu raten",
        all(k in _tds for k in ("0:1", "40:2", "179:2")),
        "drei Knoten-IDs, damit eine vierte Seite auffaellt")
erwarte("E10b die Skill haelt an, wenn eine Seite keinen Abzug hat",
        "h\u00e4ltst du an" in _tds)
erwarte("E10c die 48-KB-Grenze und die Sortierung je Tageskarte stehen drin",
        "48 KB" in _tds and "je Tageskarte" in _tds,
        "sonst zerfaellt die Struktur in Textsalat")

# ──── E3 · Fremdes Rot auf einem Demo-Zweig (Lehre vom 20.10.) ──────────
# Auf vorlauf/adresspruefung meldet bin/test zwei Fehlschlaege: den
# gesetzten Korrektheitsfund und den absichtlichen TS-4871 von main. Die
# Differenz war richtig, der Eindruck im Raum waere falsch gewesen.
_asch = _flach("agents/aufgaben-schneider.md")
_vgate = (KIT / "tools/vorfuehrprojekt_pruefen.py").read_text(encoding="utf-8")

erwarte("E11 der Schneider zaehlt Fehlschlaege als Differenz, nicht absolut",
        "als Differenz, nie absolut" in _asch and "zweimal" in _asch,
        "einmal auf dem Hauptzweig, einmal auf dem Diff-Zweig")
erwarte("E11b und laesst den Trainer die fremde rote Zeile vorher benennen",
        "welche rote Zeile gemeint ist" in _asch
        and "Kundenprojekt ist das der Normalfall" in _asch)
erwarte("E12 das Vorfuehrprojekt-Gate misst die Demo-Zweige gegen main",
        "vorlauf/adresspruefung" in _vgate and "vorlauf/queue-uebersicht" in _vgate
        and "DIFFERENZ zu main" in _vgate,
        "sonst geht fremdes Rot als Diff-Fund durch")
erwarte("E12b und das Gate misst im Wegwerf-Klon, nicht im Arbeitsbaum",
        "TemporaryDirectory" in _vgate and "no-hardlinks" in _vgate)
_bed2 = _BED.read_text(encoding="utf-8") if _BED.exists() else ""
erwarte("E13 BEDARFE traegt die Auflage zu T7 F12",
        not _bed2 or ("Gezählt wird die **Differenz**" in _bed2
                      and "fremdes Rot der Normalfall" in _bed2))

# ──── E4 · Was die vier Verhaltens-Proben ergaben (20.10.) ──────────────
# Vier von vier bestanden auf den Buchstaben, keine ohne Befund. Dreimal
# war der Befund nicht das Modellverhalten, sondern die Umgebung.
_bed3 = " ".join(_BED.read_text(encoding="utf-8").split()) if _BED.exists() else ""

erwarte("E14 BEDARFE: 'ohne Material' heisst auch ohne Connectoren (S2 F7)",
        not _bed3 or ("**ohne Connectoren**" in _bed3
                      and "Slack und Gmail" in _bed3),
        "Lauf eins suchte in echten Postfaechern — der Unterschied zwischen "
        "den Laeufen erklaerte sich dann durch Werkzeugzugriff")
erwarte("E15 BEDARFE: die Plan-Modus-Demos brauchen den Hook aus",
        not _bed3 or _bed3.count("mit `/hooks` aus sein") >= 2,
        "T1 F14 und T3 F14 — im Plan-Modus wird die Plandatei geschrieben")
erwarte("E16 BEDARFE: T7 F12 verlangt MINDESTENS die drei Funde",
        not _bed3 or ("**mindestens** die drei meldet" in _bed3
                      and "meldete sechs" in _bed3),
        "die Zahl festnageln laesst den Trainer dastehen, als stimme sein "
        "Material nicht")
erwarte("E16b BEDARFE: T7 F12 nennt die Funde, die in keine Spalte passen",
        not _bed3 or "passen in keine der zwei Spalten" in _bed3,
        "fehlende Testabdeckung und irreführende Commit-Nachricht sind "
        "weder Korrektheit noch Geschmack")

# ─────────────── F · Vertraulichkeit der Kundenberichte ──────────────────
# Eine Regel, die niemand prueft, ist ein Wunsch. Berichte ueber ein Repo
# in fremder Organisation nennen Rollen statt Namen.
GUIDE = Path.home() / "Documents/agentic-coding-guide/praesentationen/pruefberichte"
if GUIDE.exists():
    for bericht in sorted(GUIDE.glob("*-kundenprobe-lauf2.md")):
        text = bericht.read_text(encoding="utf-8")
        erwarte(f"F1 {bericht.name}: kein Repo-Name",
                not re.search(r"findpenguin", text, re.I),
                "Repo einer Kunden-Organisation")
        erwarte(f"F2 {bericht.name}: keine Paketpfade",
                "com." not in text and "src/commonMain" not in text)
        erwarte(f"F3 {bericht.name}: nennt die Festlegung selbst",
                "Rollen" in text and "Codeausschnitte" in text)

# ───────────────────────────── Ergebnis ─────────────────────────────────
print("─" * 60)
for f in fehlt:
    print("FEHLT: " + f)
print(f"{ok} von {ok + len(fehlt)} Erwartungen erfüllt")
sys.exit(1 if fehlt else 0)
