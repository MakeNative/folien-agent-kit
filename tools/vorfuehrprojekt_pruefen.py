#!/usr/bin/env python3
"""Prueft das Vorfuehrprojekt gegen das, was die Folien von ihm behaupten.

    vorfuehrprojekt_pruefen.py [projekt] [praesentationen]

Das Vorfuehrprojekt ist der Rueckfall jeder Demo. Weicht es von den
Bildern ab, merkt das niemand beim Bauen — sondern der Trainer in der
Session, wenn die Abbruchlinie schon gerissen ist.

Geprueft wird nur, was eine Folie sichtbar behauptet:
  - jeder im Fiktiv-Register genannte Projektpfad existiert
  - deliveryRetryPolicy.ts existiert NICHT (Pruefstein von S2 F2)
  - orderNotifier.ts hat genau die Zeilenzahl aus dem Dateikopf des Bildes
  - die im Bild gezeigten Zeilen stehen zeichengenau an ihrer Nummer
  - retryDelayMinutes steht auf dem Ausgangswert, nicht auf dem Zielwert
  - die Proben laufen und genau die eine ist offen
  - die zweite Domaene hat CLAUDE.md, einen @-Import und eine Regeldatei
    in einem Unterordner (T17 F11)
  - der Schutz-Hook ist eingetragen (T4 F16)
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

VERBOTEN = "src/services/deliveryRetryPolicy.ts"
AUSGANGSWERT = 5          # Betriebshandbuch 4.3 verlangt 15 — das ist die Demo
ZWEITE_DOMAENE = "zustell-doku"


def registerpfade(register: Path) -> set[str]:
    roh = re.findall(r"\b(?:src|protokolle|bin|werkzeug|berichte|wegwerf)/[\w./-]+",
                     register.read_text(encoding="utf-8"))
    # Satzzeichen am Ende gehoeren zum Text, nicht zum Pfad
    return {p.rstrip(".,;:") for p in roh if "/" in p.rstrip(".,;:")}


def bildzeilen(plan: Path) -> tuple[int | None, dict[int, str]]:
    """Zeilenzahl aus dem Dateikopf und die nummerierten Zeilen des Bildes."""
    if not plan.exists():
        return None, {}
    t = plan.read_text(encoding="utf-8")
    m = re.search(r"orderNotifier\.ts — (\d+) Zeilen", t)
    gesamt = int(m.group(1)) if m else None
    zeilen: dict[int, str] = {}
    for z in t.splitlines():
        m = re.match(r"^(\d{2,4})(\s.*)$", z)
        if m and 100 <= int(m.group(1)) <= 999:
            zeilen[int(m.group(1))] = m.group(2)
    return gesamt, zeilen


def main() -> int:
    projekt = Path(sys.argv[1] if len(sys.argv) > 1
                   else Path.home() / "StudioProjects/vorfuehrprojekt")
    praes = Path(sys.argv[2] if len(sys.argv) > 2
                 else Path.home() / "Documents/agentic-coding-guide/praesentationen")
    befunde: list[str] = []
    geprueft = 0

    if not projekt.is_dir():
        print(f"  ! kein Projekt unter {projekt}")
        return 2

    # 1 Registerpfade
    register = praes / "pptx" / "assets" / "FIKTIV-REGISTER.md"
    if register.exists():
        for p in sorted(registerpfade(register)):
            geprueft += 1
            if p != VERBOTEN and not (projekt / p).exists():
                befunde.append(f"Register nennt {p}, im Projekt fehlt es")

    # 2 Pruefstein
    geprueft += 1
    if (projekt / VERBOTEN).exists():
        befunde.append(f"{VERBOTEN} existiert — damit verliert S2 F2 "
                       f"seinen Beweis")

    # 3+4 Zeilenzahl und Bildzeilen
    quelle = projekt / "src" / "services" / "orderNotifier.ts"
    gesamt, zeilen = bildzeilen(praes / "sessions" / "S2" / "assets" / "ASSET-PLAN.md")
    if quelle.exists() and gesamt:
        ist = quelle.read_text(encoding="utf-8").splitlines()
        geprueft += 1
        if len(ist) != gesamt:
            befunde.append(f"orderNotifier.ts hat {len(ist)} Zeilen, das Bild "
                           f"nennt {gesamt}")
        for nr, text in sorted(zeilen.items()):
            geprueft += 1
            if nr > len(ist):
                befunde.append(f"Bild zeigt Zeile {nr}, Datei endet bei {len(ist)}")
            elif ist[nr - 1] != text:
                befunde.append(f"Zeile {nr} weicht vom Bild ab\n"
                               f"        ist : {ist[nr-1]!r}\n"
                               f"        Bild: {text!r}")

    # 5 Ausgangswert
    if quelle.exists():
        geprueft += 1
        m = re.search(r"const retryDelayMinutes = (\d+);",
                      quelle.read_text(encoding="utf-8"))
        if not m:
            befunde.append("retryDelayMinutes steht nicht im Nachtlauf")
        elif int(m.group(1)) != AUSGANGSWERT:
            befunde.append(f"retryDelayMinutes steht auf {m.group(1)}, der "
                           f"Ausgangsstand ist {AUSGANGSWERT} — sonst hat "
                           f"T0 F11 nichts zu zeigen")

    # 6 Proben
    pruefbefehl = projekt / "bin" / "test"
    if pruefbefehl.exists():
        geprueft += 1
        r = subprocess.run([str(pruefbefehl)], cwd=projekt,
                           capture_output=True, text=True, timeout=180)
        offen = re.search(r"(\d+) Probe\(n\) offen", r.stdout)
        if not offen:
            befunde.append("bin/test meldet keine Probenbilanz")
        elif offen.group(1) != "1":
            befunde.append(f"{offen.group(1)} Proben offen, erwartet ist "
                           f"genau 1 (die, die T0 F11 gruen macht)")

    # 7 zweite Domaene
    zd = projekt / ZWEITE_DOMAENE
    geprueft += 1
    if not (zd / "CLAUDE.md").exists():
        befunde.append(f"{ZWEITE_DOMAENE}/CLAUDE.md fehlt — T17 F11 braucht "
                       f"eine zweite Domaene")
    else:
        if "@" not in zd.joinpath("CLAUDE.md").read_text(encoding="utf-8"):
            befunde.append(f"{ZWEITE_DOMAENE}/CLAUDE.md bindet nichts per "
                           f"@pfad ein — dann zeigt /context nichts")
        unter = [p for p in zd.rglob("CLAUDE.md") if p.parent != zd]
        if not unter:
            befunde.append(f"{ZWEITE_DOMAENE}: keine Regeldatei in einem "
                           f"Unterordner — die Pointe von T17 F12 fehlt")

    # 8 Schutz-Hook
    s = projekt / ".claude" / "settings.json"
    geprueft += 1
    if not s.exists():
        befunde.append(".claude/settings.json fehlt — T4 F16 verlangt den "
                       "fertigen Eintrag")
    else:
        try:
            d = json.loads(s.read_text(encoding="utf-8"))
            if not d.get("hooks", {}).get("PreToolUse"):
                befunde.append("kein PreToolUse-Hook in settings.json")
        except json.JSONDecodeError as e:
            befunde.append(f"settings.json ist kein gueltiges JSON — {e}")

    print(f"{geprueft} Pruefungen, {len(befunde)} Befund(e)")
    for b in befunde:
        print("  ! " + b)
    return 1 if befunde else 0


if __name__ == "__main__":
    sys.exit(main())
