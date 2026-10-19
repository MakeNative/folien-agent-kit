#!/usr/bin/env python3
"""PostToolUse: fährt das Asset-Gate, sobald Plan/Ledger/Freigabe
eines Decks geschrieben wurden (AS-06).

Exit 2 trägt die Befunde sofort an das Modell zurück. Ohne Befund still.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

WERKZEUG = Path(__file__).resolve().parent.parent / "tools" / "assets_pruefen.py"
ZIELE = ("ASSET-PLAN.md", "LEDGER.md", "FREIGABE.md")


def main():
    try:
        daten = json.load(sys.stdin)
    except Exception:
        sys.exit(0)
    if daten.get("tool_name") not in ("Write", "Edit", "MultiEdit"):
        sys.exit(0)
    pfad_roh = (daten.get("tool_input") or {}).get("file_path") or ""
    p = Path(pfad_roh)
    if not p.is_absolute():  # relativer Pfad: gegen das CWD des Aufrufers
        p = Path(daten.get("cwd") or ".") / p
    teile = p.as_posix()
    # Asset-Mappen lagen unter pptx/assets/<deck>/ und liegen seit dem Umzug
    # als sessions/<ID>/assets/. Beide Orte gelten.
    in_mappe = "/pptx/assets/" in teile or "/praesentationen/sessions/" in teile \
               or teile.startswith("praesentationen/sessions/")
    if not in_mappe or Path(teile).name not in ZIELE:
        sys.exit(0)
    deckname = Path(teile).parent.name
    # Wurzel: …/praesentationen/pptx/assets/<deck>/<datei>
    wurzel = Path(teile).parent.parent.parent.parent
    deck = wurzel / "decks" / f"{deckname}.md"
    if not deck.exists() or not WERKZEUG.exists():
        sys.exit(0)
    try:
        lauf = subprocess.run(
            [sys.executable, str(WERKZEUG), str(deck), "--ausloeser", "hook"],
            capture_output=True, text=True, timeout=20,
            cwd=daten.get("cwd") or None)
    except Exception as e:
        # Ein kaputtes Gate darf nicht wie ein grünes aussehen
        # (Review 09.10., Befund 22).
        print(f"Asset-Gate konnte nicht laufen: {e}", file=sys.stderr)
        sys.exit(2)
    if lauf.returncode == 0:
        sys.exit(0)
    if lauf.returncode == 1 and lauf.stdout.strip():
        print(
            "Asset-Befunde (AS-Regeln, gemessen):\n" + lauf.stdout.strip()
            + "\n\nA-01 heißt Plan und Marken decken sich nicht, A-03 heißt "
            "Status ohne Datei/Ledger/Freigabe, A-05 heißt Fiktivname ohne "
            "Register-Eintrag.",
            file=sys.stderr,
        )
        sys.exit(2)
    print(
        f"Asset-Gate unerwartet beendet (rc={lauf.returncode}):\n"
        + (lauf.stderr or lauf.stdout or "keine Ausgabe")[-800:],
        file=sys.stderr,
    )
    sys.exit(2)


if __name__ == "__main__":
    main()
