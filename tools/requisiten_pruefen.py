#!/usr/bin/env python3
"""Gate der Requisiten-Strasse: Manifest gegen Deck, Dateien und BEDARFE.

    requisiten_pruefen.py [praesentationen] [--streng]

Ohne --streng sind die Punkte, die heute noch nicht ueberall erfuellt
sind, Hinweise statt Befunde — so wie es der Plan vorsieht: scharf
geschaltet wird erst, wenn alle 28 Sessions ein geprueftes Manifest
haben.

Geprueft wird:
  R-1  Jeder Eintrag hat Folie (bei Decks), Art und braucht-Text.
  R-2  Jede genannte Datei existiert.
  R-3  Jede *Requisit.*-Marke im Deck hat einen Eintrag — und umgekehrt.
  R-4  Keine Vor-Ort-Reste in den Hinweisen. Die Manifeste hatten die
       Remote-Umstellung nicht mitgemacht; das darf nicht wiederkommen.
  R-5  Jede Demo-Folie, die laut BEDARFE.md etwas vom Projekt verlangt,
       hat einen Manifest-Eintrag.
  R-6  (Hinweis) Jeder Eintrag nennt seine Herkunft im Deck.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ARTEN = {"datei", "vorlage", "trainer", "session", "asset", "druck"}
VOR_ORT = ("auf den Plätzen", "im Raum", "auf dem Tisch", "an der Wand",
           "Flipchart", "Beamer", "Moderationskarte", "an die Tafel")
BRAUCHT_REQUISIT = {"Repo", "Mechanik", "System", "Infra"}


def decks(sess: Path) -> list[Path]:
    return sorted(sess.glob(f"{sess.name}*-*.md"))


def marken(deck: Path) -> dict[int, int]:
    """Je Folie die Zahl der *Requisit.*-Marken."""
    out: dict[int, int] = {}
    for b in re.split(r"^## Folie ", deck.read_text(encoding="utf-8"),
                      flags=re.M)[1:]:
        nr = b.split(":")[0].strip()
        if nr.isdigit():
            n = len(re.findall(r"\*Requisit\.\*", b))
            if n:
                out[int(nr)] = out.get(int(nr), 0) + n
    return out


def bedarfe(pfad: Path) -> dict[tuple[str, int], str]:
    """(Deckname, Folie) -> Art, aus BEDARFE.md."""
    out: dict[tuple[str, int], str] = {}
    deck = None
    nr = None
    for z in pfad.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^## ([ST]\d+b?-\S+)", z)
        if m:
            deck, nr = m.group(1), None
            continue
        m = re.match(r"^### F(\d+) ", z)
        if m:
            nr = int(m.group(1))
            continue
        m = re.match(r"^- \*\*Art\*\* `(.+?)`", z)
        if m and deck and nr:
            out[(deck, nr)] = m.group(1)
    return out


def main() -> int:
    streng = "--streng" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    wurzel = Path(args[0] if args else ".").resolve()
    bed = bedarfe(wurzel / "BEDARFE.md") if (wurzel / "BEDARFE.md").exists() else {}

    befunde: list[str] = []
    hinweise: list[str] = []
    mit, ohne = 0, []

    for sess in sorted(p for p in (wurzel / "sessions").iterdir() if p.is_dir()):
        mpfad = sess / "requisiten" / "manifest.json"
        hat_deck = bool(decks(sess))
        if not mpfad.exists():
            ohne.append(sess.name)
            if hat_deck:
                (befunde if streng else hinweise).append(
                    f"{sess.name}: Deck-Session ohne requisiten/manifest.json")
            continue
        mit += 1
        try:
            d = json.loads(mpfad.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            befunde.append(f"{sess.name}: manifest.json ist kein JSON — {e}")
            continue
        eintraege = d.get("requisiten") or []
        belegt: dict[int, int] = {}

        for i, e in enumerate(eintraege):
            wo = f"{sess.name} Eintrag {i + 1}"
            # R-1
            if not e.get("braucht"):
                befunde.append(f"{wo}: kein braucht-Text")
            art = e.get("art")
            if art not in ARTEN:
                befunde.append(f"{wo}: Art {art!r} ist keine der "
                               f"{sorted(ARTEN)}")
            if hat_deck and not e.get("folie"):
                befunde.append(f"{wo}: keine Folie (Deck-Session)")
            if art in ("datei", "vorlage") and not e.get("datei"):
                befunde.append(f"{wo}: Art {art} ohne Datei")
            # R-2
            datei = e.get("datei")
            if datei:
                q = (sess / "requisiten" / datei)
                if not q.exists():
                    befunde.append(f"{wo}: {datei} existiert nicht")
            # R-4
            h = e.get("hinweis") or ""
            for wort in VOR_ORT:
                if wort.lower() in h.lower():
                    befunde.append(f"{wo}: Vor-Ort-Rest im Hinweis "
                                   f"(„{wort}\") — das Programm läuft remote")
            # R-6
            if not e.get("herkunft"):
                hinweise.append(f"{wo}: nennt keine Herkunft im Deck")
            if e.get("folie"):
                belegt[e["folie"]] = belegt.get(e["folie"], 0) + 1

        # R-3
        for deck in decks(sess):
            for nr, n in marken(deck).items():
                if nr not in belegt:
                    befunde.append(f"{sess.name} F{nr}: {n} *Requisit.*-Marke(n) "
                                   f"im Deck, kein Eintrag im Manifest")
        # R-5
        for deck in decks(sess):
            for (dname, nr), art in bed.items():
                if dname != deck.stem or art not in BRAUCHT_REQUISIT:
                    continue
                if nr not in belegt:
                    (befunde if streng else hinweise).append(
                        f"{sess.name} F{nr}: BEDARFE nennt Art `{art}`, "
                        f"das Manifest hat keinen Eintrag")

    print(f"{mit} Manifest(e), {len(ohne)} Session(en) ohne — "
          f"{len(befunde)} Befund(e), {len(hinweise)} Hinweis(e)"
          f"{'  [streng]' if streng else ''}")
    for b in befunde:
        print("  ! " + b)
    if hinweise and not streng:
        print(f"\n  ({len(hinweise)} Hinweise, mit --streng werden sie Befunde)")
        for h in hinweise[:8]:
            print("    i " + h)
        if len(hinweise) > 8:
            print(f"    … und {len(hinweise) - 8} weitere")
    return 1 if befunde else 0


if __name__ == "__main__":
    sys.exit(main())
