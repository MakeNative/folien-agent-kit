#!/usr/bin/env python3
"""Maschinengate der Asset-Straße (AS-06).

Aufruf: assets_pruefen.py <deck.md> [--ausloeser hook] | --selbsttest

Verträge (Review 09.10.2026):
  Status-Vokabular im Plan: geplant | offen | erzeugt — NICHTS anderes.
  Freigaben leben AUSSCHLIESSLICH in FREIGABE.md (AS-05), Zeilenformat
  strikt `F<nr>.<png|mp4> — freigegeben (Stand <YYYY-MM-DD>, …)` bzw.
  `F<nr>.<ext> — ABGELEHNT: …`; bei mehreren Zeilen je Datei gilt die
  letzte. Eine Folie trägt höchstens EINE Bild-Marke (AS-07).

Prüfungen:
  A-01  Marken↔Plan-Deckung · höchstens eine Marke je Folie · Marken
        außerhalb von Folien · Dateien ohne Plan-Block
  A-02  Route-/Status-Whitelist · Pflichtfelder Datei+Masse ·
        Eigentümer bei Route ODER Status offen · foto: Text-Block
        PFLICHT-leer · clip: Clip-Feld Pflicht (sonst verboten) ·
        mock/clip: Fiktiv-Zeile Pflicht
  A-03  erzeugt ⇒ Datei(en) existieren und stehen im LEDGER · jede
        vorhandene Asset-Datei ohne LEDGER-Zeile ist Befund ·
        FREIGABE „freigegeben" ⇒ Status erzeugt, Datei existiert und
        die Freigabe-Zeile trägt das Datum der LETZTEN Ledger-Zeile
        (Regenerations-Schutz, AS-05)
  A-04  Namenskonvention F<nr>.png / F<nr>.mp4
  A-05  jeder Fiktivname steht als Zeilenanfang im FIKTIV-REGISTER.md

Exit 0 ohne Befund, 1 mit Befunden. Jeder Lauf landet im Laufprotokoll.
"""
from __future__ import annotations

import os
import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gemeinsam as g  # noqa: E402

MARKE_RE = re.compile(r"\[(Screenshot|Bild|Video):")
BLOCK_RE = re.compile(r"^## F(\d+)\b[^\n]*\n(.*?)(?=^## F\d|\Z)", re.M | re.S)
FOLIE_RE = re.compile(r"^## Folie (\d+)\b", re.M)
FREIGABE_RE = re.compile(
    r"^(F\d+\.(?:png|mp4))\s*[—–-]+\s*(freigegeben|abgelehnt)\b(.*)$",
    re.M | re.I)
DATUM_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
ROUTEN = ("mock", "foto", "clip", "offen")
STATI = ("geplant", "offen", "erzeugt")


def _feld(block: str, name: str) -> str | None:
    m = re.search(rf"^{name}:\s*(.+)$", block, re.M)
    return m.group(1).strip() if m else None


def _text_block(block: str) -> str:
    m = re.search(r"^Text \(zeichengenau\):\s*\n(.*?)(?=^\w[\w ()-]*:|\Z)",
                  block, re.M | re.S)
    return (m.group(1).strip() if m else "")


def parse_freigabe(text: str) -> dict[str, tuple[str, str]]:
    """Datei -> (status, ganze Zeile); letzte Zeile je Datei gewinnt."""
    out: dict[str, tuple[str, str]] = {}
    for m in FREIGABE_RE.finditer(text):
        out[m.group(1)] = (m.group(2).lower(), m.group(0))
    return out


def pruefe_deck(deck_pfad: str) -> list[str]:
    befunde: list[str] = []
    deck = open(deck_pfad, encoding="utf-8").read()
    name = os.path.splitext(os.path.basename(deck_pfad))[0]
    wurzel = os.path.dirname(os.path.dirname(os.path.abspath(deck_pfad)))
    adir = os.path.join(wurzel, "pptx", "assets", name)

    marken: dict[int, int] = {}
    folie = 0
    notiz = re.compile(r"^(KERN|SAGEN|TUN|UEBERGANG|BEI NACHFRAGE|Demo|"
                       r"Jetzt du|Regie|Hilfe|Plan B|Requisit\w*|"
                       r"Sprechnotiz):", re.I)
    for zeile in deck.splitlines():
        fm = FOLIE_RE.match(zeile)
        if fm:
            folie = int(fm.group(1))
            continue
        # Nur Marken, die der Builder rendert: Regie-/Notiz-Zeilen und
        # in Backticks zitierte Syntax sind Dokumentation, keine Fläche
        # (Pilotbefund 09.10., asset-planner).
        if notiz.match(zeile) or "`[" in zeile:
            continue
        if MARKE_RE.search(zeile):
            marken[folie] = marken.get(folie, 0) + 1
    if 0 in marken:
        befunde.append(f"A-01: {marken.pop(0)} Marke(n) außerhalb jeder "
                       f"Folie (z. B. Dramaturgie-Block) — dort plant die "
                       f"Asset-Straße nichts")
    for nr, anzahl in sorted(marken.items()):
        if anzahl > 1:
            befunde.append(f"A-01/AS-07: Folie {nr} trägt {anzahl} Marken — "
                           f"erlaubt ist eine je Folie")

    plan_pfad = os.path.join(adir, "ASSET-PLAN.md")
    if not os.path.exists(plan_pfad):
        if marken:
            befunde.append(
                f"A-01: {name} trägt {sum(marken.values())} Marken, aber "
                f"kein ASSET-PLAN.md unter {os.path.relpath(adir, wurzel)}")
        return befunde

    plan = open(plan_pfad, encoding="utf-8").read()
    bloecke = {int(nr): body for nr, body in BLOCK_RE.findall(plan)}

    for nr in sorted(marken):
        if nr not in bloecke:
            befunde.append(f"A-01: Marke auf Folie {nr} ohne Plan-Block")
    for nr in sorted(bloecke):
        if nr not in marken:
            befunde.append(f"A-01: Plan-Block F{nr} ohne Marke im Deck")

    ledger = ""
    lp = os.path.join(adir, "LEDGER.md")
    if os.path.exists(lp):
        ledger = open(lp, encoding="utf-8").read()
    freigaben = {}
    fp = os.path.join(adir, "FREIGABE.md")
    if os.path.exists(fp):
        freigaben = parse_freigabe(open(fp, encoding="utf-8").read())
    register = ""
    rp = os.path.join(wurzel, "pptx", "assets", "FIKTIV-REGISTER.md")
    if os.path.exists(rp):
        register = open(rp, encoding="utf-8").read()

    def letztes_ledger_datum(datei: str) -> str | None:
        daten = [DATUM_RE.search(z).group(0)
                 for z in ledger.splitlines()
                 if datei in z and DATUM_RE.search(z)]
        return daten[-1] if daten else None

    geplante_dateien: set[str] = set()
    for nr, block in sorted(bloecke.items()):
        route = (_feld(block, "Route") or "").lower()
        status = (_feld(block, "Status") or "").lower()
        datei = _feld(block, "Datei") or ""
        clip = _feld(block, "Clip") or ""
        kopf = f"F{nr}"

        if route not in ROUTEN:
            befunde.append(f"A-02: {kopf} Route fehlt oder unbekannt: "
                           f"'{route}' (erlaubt: {', '.join(ROUTEN)})")
            continue
        if status not in STATI:
            befunde.append(f"A-02: {kopf} Status fehlt oder unbekannt: "
                           f"'{status}' (erlaubt: {', '.join(STATI)} — "
                           f"Freigabe lebt nur in FREIGABE.md)")
        if route == "offen" or status == "offen":
            if not re.search(r"^Eigent(ü|ue)mer:\s*\S", block, re.M | re.I):
                befunde.append(f"A-02: {kopf} offen ohne Eigentümer-Zeile")
            continue

        if not datei:
            befunde.append(f"A-02: {kopf} Datei-Feld fehlt")
            continue
        if not _feld(block, "Masse"):
            befunde.append(f"A-02: {kopf} Masse-Feld fehlt")
        if not re.fullmatch(rf"F{nr}\.png", datei):
            befunde.append(f"A-04: {kopf} Dateiname '{datei}' bricht die "
                           f"Konvention F{nr}.png")
        if route == "clip":
            if not clip:
                befunde.append(f"A-02: {kopf} Route clip ohne Clip-Feld")
            elif not re.fullmatch(rf"F{nr}\.mp4", clip):
                befunde.append(f"A-04: {kopf} Clip '{clip}' bricht die "
                               f"Konvention F{nr}.mp4")
        elif clip:
            befunde.append(f"A-02: {kopf} Clip-Feld nur bei Route clip "
                           f"erlaubt (Route ist {route})")
        if route == "foto" and _text_block(block):
            befunde.append(f"A-02/AS-02: {kopf} Route foto mit "
                           f"Text (zeichengenau)-Inhalt — generative Bilder "
                           f"tragen keinen Pflichttext")
        fiktiv = _feld(block, "Fiktiv")
        if route in ("mock", "clip") and fiktiv is None:
            befunde.append(f"A-05: {kopf} Fiktiv-Zeile fehlt "
                           f"(Pflicht bei mock/clip, notfalls 'keine')")

        dateien = [datei] + ([clip] if route == "clip" and clip else [])
        geplante_dateien.update(dateien)
        for d in dateien:
            voll = os.path.join(adir, d)
            existiert = os.path.exists(voll)
            if status == "erzeugt":
                if not existiert:
                    befunde.append(f"A-03: {kopf} Status erzeugt, aber {d} "
                                   f"existiert nicht")
                if d not in ledger:
                    befunde.append(f"A-03: {kopf} {d} ohne LEDGER-Eintrag")
            if existiert and d not in ledger:
                befunde.append(f"A-03: {kopf} {d} liegt im Ordner, steht "
                               f"aber nicht im LEDGER (AS-04)")
            fz = freigaben.get(d)
            if fz and fz[0] == "freigegeben":
                if status != "erzeugt":
                    befunde.append(f"A-03/AS-05: {kopf} {d} ist freigegeben, "
                                   f"Plan-Status ist aber '{status}'")
                if not existiert:
                    befunde.append(f"A-03/AS-05: {kopf} {d} ist freigegeben, "
                                   f"existiert aber nicht")
                ld = letztes_ledger_datum(d)
                if ld and ld not in fz[1]:
                    befunde.append(f"A-03/AS-05: {kopf} {d} wurde nach der "
                                   f"Freigabe neu erzeugt (Ledger {ld}, "
                                   f"Freigabe-Zeile trägt das Datum nicht) — "
                                   f"Regeneration braucht neue Freigabe")

        if fiktiv and fiktiv.strip("„“\" ") not in ("-", "—", "keine", ""):
            for eintrag in re.split(r"[,;·]", fiktiv):
                e = eintrag.strip().strip("„“\"")
                if e and not re.search(rf"^{re.escape(e)}\b", register, re.M):
                    befunde.append(f"A-05: {kopf} Fiktivname '{e}' steht "
                                   f"nicht am Zeilenanfang im "
                                   f"FIKTIV-REGISTER.md")

    if os.path.isdir(adir):
        for f in sorted(os.listdir(adir)):
            m = re.fullmatch(r"F(\d+)\.(png|mp4)", f)
            if not m:
                continue
            if int(m.group(1)) not in bloecke:
                befunde.append(f"A-01: Datei {f} ohne Plan-Block")
            elif f not in geplante_dateien:
                befunde.append(f"A-02: Datei {f} ist in Block "
                               f"F{m.group(1)} nicht als Datei/Clip geführt")
    return befunde


def selbsttest() -> int:
    ok = True

    def fall(name, erwartet, deck_text, plan=None, ledger=None,
             freigabe=None, register=None, dateien=()):
        nonlocal ok
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "decks"))
            deck = os.path.join(d, "decks", "T-test.md")
            open(deck, "w").write(deck_text)
            adir = os.path.join(d, "pptx", "assets", "T-test")
            os.makedirs(adir)
            if plan is not None:
                open(os.path.join(adir, "ASSET-PLAN.md"), "w").write(plan)
            if ledger is not None:
                open(os.path.join(adir, "LEDGER.md"), "w").write(ledger)
            if freigabe is not None:
                open(os.path.join(adir, "FREIGABE.md"), "w").write(freigabe)
            if register is not None:
                open(os.path.join(d, "pptx", "assets",
                                  "FIKTIV-REGISTER.md"), "w").write(register)
            for f in dateien:
                open(os.path.join(adir, f), "wb").write(b"x")
            befunde = pruefe_deck(deck)
            treffer = any(erwartet in b for b in befunde) if erwartet else not befunde
            print(("  ok " if treffer else "  FEHLT ") + name +
                  ("" if treffer else f" — Befunde: {befunde}"))
            ok = ok and treffer

    deck = "## Folie 3: X (~1 min)\n\n[Screenshot: ein Fenster.]\n"
    basis = ("## F3\nRoute: mock\nStatus: geplant\nDatei: F3.png\n"
             "Masse: 1920x1080\nFiktiv: keine\n")
    fall("Marke ohne Plan", "A-01", deck, plan=None)
    fall("Plan-Block ohne Marke", "A-01", deck,
         plan=basis + "## F9\nRoute: mock\nStatus: geplant\nDatei: F9.png\n"
                      "Masse: 1920x1080\nFiktiv: keine\n")
    fall("zwei Marken auf einer Folie", "AS-07",
         "## Folie 3: X (~1 min)\n\n[Bild: a.]\n[Bild: b.]\n", plan=basis)
    fall("Marke außerhalb der Folien", "außerhalb",
         "[Bild: im Vorspann.]\n" + deck, plan=basis)
    fall("Regie-Marke zählt nicht",
         "", deck + "Demo: Plan B — [Screenshot: Rückfallbild] zeigen.\n",
         plan=basis)
    fall("zitierte Marke zählt nicht",
         "", deck + "1. **Folie 9** — `[Screenshot: …]` Hinweis.\n",
         plan=basis)
    fall("Route fehlt", "A-02", deck,
         plan="## F3\nStatus: geplant\nDatei: F3.png\nMasse: x\nFiktiv: keine\n")
    fall("Status unbekannt", "Status fehlt oder unbekannt", deck,
         plan="## F3\nRoute: mock\nStatus: freigegeben\nDatei: F3.png\n"
              "Masse: x\nFiktiv: keine\n")
    fall("offen ohne Eigentümer", "A-02", deck,
         plan="## F3\nRoute: offen\nStatus: offen\n")
    fall("Masse fehlt", "Masse-Feld fehlt", deck,
         plan="## F3\nRoute: mock\nStatus: geplant\nDatei: F3.png\nFiktiv: keine\n")
    fall("falscher Dateiname", "A-04", deck,
         plan="## F3\nRoute: mock\nStatus: geplant\nDatei: bild3.png\n"
              "Masse: x\nFiktiv: keine\n")
    fall("clip ohne Clip-Feld", "Route clip ohne Clip-Feld", deck,
         plan="## F3\nRoute: clip\nStatus: geplant\nDatei: F3.png\n"
              "Masse: x\nFiktiv: keine\n")
    fall("Clip-Feld bei mock", "Clip-Feld nur bei Route clip", deck,
         plan=basis.replace("Fiktiv: keine\n", "Clip: F3.mp4\nFiktiv: keine\n"))
    fall("foto mit Pflichttext", "AS-02", deck,
         plan="## F3\nRoute: foto\nStatus: geplant\nDatei: F3.png\n"
              "Masse: x\nText (zeichengenau):\nHallo Welt\n")
    fall("mock ohne Fiktiv-Zeile", "Fiktiv-Zeile fehlt", deck,
         plan="## F3\nRoute: mock\nStatus: geplant\nDatei: F3.png\nMasse: x\n")
    fall("erzeugt ohne Datei", "existiert nicht", deck,
         plan=basis.replace("geplant", "erzeugt"),
         ledger="F3.png | mock | … | 2026-10-09")
    fall("Datei ohne Ledger trotz Status geplant", "AS-04", deck,
         plan=basis, dateien=("F3.png",))
    fall("'nicht freigegeben' zählt nicht als Freigabe", "", deck,
         plan=basis.replace("geplant", "erzeugt"),
         ledger="F3.png | mock | … | 2026-10-09",
         freigabe="F3.png — nicht freigegeben (Text weicht ab)",
         dateien=("F3.png",))
    fall("Freigabe bei Status geplant", "AS-05", deck,
         plan=basis, freigabe="F3.png — freigegeben (Stand 2026-10-09)")
    fall("Regeneration nach Freigabe", "Regeneration", deck,
         plan=basis.replace("geplant", "erzeugt"),
         ledger="F3.png | mock | … | 2026-10-09\nF3.png | mock | retry | 2026-10-10",
         freigabe="F3.png — freigegeben (Stand 2026-10-09, geprüft)",
         dateien=("F3.png",))
    fall("Ablehnung nach Freigabe neutralisiert sie (letzte Zeile gewinnt)",
         "", deck,
         plan=basis.replace("geplant", "erzeugt"),
         ledger="F3.png | mock | … | 2026-10-09",
         freigabe="F3.png — freigegeben (Stand 2026-10-09)\n"
                  "F3.png — ABGELEHNT: Tippfehler\n",
         dateien=("F3.png",))
    fall("Freigabe nach Ablehnung gilt (letzte Zeile gewinnt)", "AS-05", deck,
         plan=basis,  # Status geplant → Freigabe muss anschlagen
         freigabe="F3.png — ABGELEHNT: Tippfehler\n"
                  "F3.png — freigegeben (Stand 2026-10-09)\n")
    fall("Fiktivname fehlt im Register", "A-05", deck,
         plan=basis.replace("Fiktiv: keine", "Fiktiv: KorbSync"),
         register="— leer —")
    fall("Fiktiv-Substring reicht nicht", "A-05", deck,
         plan=basis.replace("Fiktiv: keine", "Fiktiv: Korb"),
         register="KorbSync — fiktives System")
    fall("alles grün", "", deck,
         plan=basis.replace("geplant", "erzeugt")
                   .replace("Fiktiv: keine", "Fiktiv: KorbSync"),
         ledger="F3.png | mock | hyperframes | komposition f3 | 2026-10-09",
         freigabe="F3.png — freigegeben (Stand 2026-10-09, Wort für Wort)",
         register="KorbSync — fiktives Lager-Shop-Abgleichsystem",
         dateien=("F3.png",))
    print("SELBSTTEST " + ("GRUEN" if ok else "ROT"))
    return 0 if ok else 1


def main() -> int:
    roh = sys.argv[1:]
    ausloeser = "cli"
    if "--ausloeser" in roh:
        i = roh.index("--ausloeser")
        ausloeser = roh[i + 1] if i + 1 < len(roh) else "cli"
        roh = roh[:i] + roh[i + 2:]
    args = [a for a in roh if not a.startswith("--")]
    if "--selbsttest" in sys.argv:
        return selbsttest()
    if len(args) != 1:
        print(__doc__)
        return 2
    befunde = pruefe_deck(args[0])
    w = g.wurzel(Path(args[0]).resolve().parent)
    g.spur(w, "gate", werkzeug="assets_pruefen", ausloeser=ausloeser,
           deck=os.path.basename(args[0]), befunde=len(befunde))
    if befunde:
        print("\n".join(befunde))
        return 1
    print("0 Befunde")
    return 0


if __name__ == "__main__":
    sys.exit(main())
