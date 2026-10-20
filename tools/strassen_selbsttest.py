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

# ───────────────────────────── Ergebnis ─────────────────────────────────
print("─" * 60)
for f in fehlt:
    print("FEHLT: " + f)
print(f"{ok} von {ok + len(fehlt)} Erwartungen erfüllt")
sys.exit(1 if fehlt else 0)
