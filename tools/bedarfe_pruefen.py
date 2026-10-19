#!/usr/bin/env python3
"""Prueft BEDARFE.md gegen die Decks: traegt jede Demo-Folie einen Bedarf?

    bedarfe_pruefen.py [praesentationen-wurzel]

Die Bedarfsliste ist die Schnittstelle zwischen Material und Projekt. Faellt
eine Demo-Folie heraus, merkt es sonst erst der Trainer am Morgen — die
Pipeline haette fuer diese Folie nichts geschnitten und nichts gemeldet.

Geprueft wird dreierlei: Deckung in beide Richtungen, Vollstaendigkeit der
vier Felder und die Zaehlung in der Kopftabelle.
"""
from __future__ import annotations

import collections
import re
import sys
from pathlib import Path

FELDER = ("verlangt", "Probe")          # abgeleitet/Rueckfall duerfen entfallen
ARTEN = {"—", "Repo", "Mechanik", "System", "Infra"}


def demos(wurzel: Path) -> set[tuple[str, str]]:
    """(Deckname, Foliennummer) jeder Folie mit `Typ: D`."""
    out: set[tuple[str, str]] = set()
    for sess in sorted(p for p in (wurzel / "sessions").iterdir() if p.is_dir()):
        for deck in sorted(sess.glob(f"{sess.name}*-*.md")):
            for b in re.split(r"^## Folie ", deck.read_text(encoding="utf-8"),
                              flags=re.M)[1:]:
                if re.search(r"^Typ:\s*D\s*$", b, re.M):
                    out.add((deck.stem, b.split(":")[0].strip()))
    return out


def eintraege(pfad: Path) -> tuple[set[tuple[str, str]], dict, list[str]]:
    soll: set[tuple[str, str]] = set()
    arten: collections.Counter = collections.Counter()
    maengel: list[str] = []
    sess, akt, felder = None, None, set()

    def abschluss() -> None:
        if akt is None:
            return
        for f in FELDER:
            if f not in felder:
                maengel.append(f"{akt[0]} F{akt[1]}: Feld **{f}** fehlt")

    for z in pfad.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^## ([ST]\d+b?-\S+)", z)
        if m:
            sess = m.group(1)
            continue
        m = re.match(r"^### F(\d+) ", z)
        if m:
            abschluss()
            if sess is None:
                maengel.append(f"F{m.group(1)}: steht unter keiner Session")
            akt, felder = (sess, m.group(1)), set()
            continue
        m = re.match(r"^- \*\*Art\*\* `(.+?)`", z)
        if m and akt:
            soll.add(akt)
            arten[m.group(1)] += 1
            if m.group(1) not in ARTEN:
                maengel.append(f"{akt[0]} F{akt[1]}: unbekannte Art "
                               f"„{m.group(1)}\"")
            continue
        m = re.match(r"^- \*\*(\w+)\*\*", z)
        if m and akt:
            felder.add(m.group(1))
    abschluss()
    return soll, arten, maengel


def kopfzahlen(pfad: Path) -> dict[str, int]:
    """Die Zahlen aus der Arten-Tabelle im Kopf — sie veralten sonst still."""
    out: dict[str, int] = {}
    for z in pfad.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\| `?(—|Repo|Mechanik|System|Infra)`? \| (\d+) \|", z)
        if m:
            out[m.group(1)] = int(m.group(2))
    return out


def main() -> int:
    wurzel = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    pfad = wurzel / "BEDARFE.md"
    if not pfad.exists():
        print(f"  ! {pfad} fehlt")
        return 2

    ist = demos(wurzel)
    soll, arten, maengel = eintraege(pfad)
    befunde: list[str] = list(maengel)

    for deck, nr in sorted(ist - soll):
        befunde.append(f"{deck} F{nr}: Demo-Folie ohne Bedarf")
    for deck, nr in sorted(soll - ist):
        befunde.append(f"{deck} F{nr}: Bedarf ohne Demo-Folie")

    for art, n in kopfzahlen(pfad).items():
        if arten.get(art, 0) != n:
            befunde.append(f"Kopftabelle: Art `{art}` nennt {n}, "
                           f"gezaehlt sind {arten.get(art, 0)}")

    print(f"{len(ist)} Demo-Folien, {len(soll)} Bedarfe, "
          f"{len(befunde)} Befund(e)")
    for b in befunde:
        print("  ! " + b)
    if not befunde:
        print("  " + " · ".join(f"{a}: {n}" for a, n in sorted(arten.items())))
    return 1 if befunde else 0


if __name__ == "__main__":
    sys.exit(main())
