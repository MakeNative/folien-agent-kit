#!/usr/bin/env python3
"""PostToolUse: misst ein Deck, sobald es geschrieben wurde.

Exit 2 trägt die Befunde sofort an das Modell zurück, solange der Writer noch
am Deck ist. Ohne Befund still.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

WERKZEUG = Path(__file__).resolve().parent.parent / "tools" / "folien_pruefen.py"


def main():
    try:
        daten = json.load(sys.stdin)
    except Exception:
        sys.exit(0)
    if daten.get("tool_name") not in ("Write", "Edit", "MultiEdit"):
        sys.exit(0)
    pfad_roh = (daten.get("tool_input") or {}).get("file_path") or ""
    teile = Path(pfad_roh).as_posix()
    if "/pruefberichte/" in teile or Path(teile).name.startswith("SPEZIFIKATION"):
        # Prüfberichte und Spezifikationen unter decks/ sind keine Decks.
        sys.exit(0)
    if "/.claude/" in teile:
        # Agent-Memory und andere Metadateien unter decks/ sind keine Decks.
        sys.exit(0)
    if "/praesentationen/decks/" not in teile and not teile.startswith("praesentationen/decks/"):
        sys.exit(0)
    pfad = Path(pfad_roh)
    if not pfad.exists() or not WERKZEUG.exists():
        sys.exit(0)
    try:
        lauf = subprocess.run([sys.executable, str(WERKZEUG), str(pfad), "--ausloeser", "hook"],
                              capture_output=True, text=True, timeout=25,
                              cwd=daten.get("cwd") or None)
    except Exception:
        sys.exit(0)
    if lauf.returncode == 1 and lauf.stdout.strip():
        print(
            "Folien-Befunde (gemessen, nicht beurteilt):\n" + lauf.stdout.strip()
            + "\n\nF-02/F-03 löst Kürzen, F-04 verschiebt Belege ins Handout, "
            "F-05 stellt das Beispiel vor die Regel.",
            file=sys.stderr,
        )
        sys.exit(2)
    sys.exit(0)


if __name__ == "__main__":
    main()
