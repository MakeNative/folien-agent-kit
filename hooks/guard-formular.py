#!/usr/bin/env python3
"""PostToolUse: fährt das Formular-Gate, sobald Spezifikation, Baulog oder
Freigabe der Eval-Straße geschrieben wurden (FB-05).

Exit 2 trägt die Befunde sofort an das Modell zurück. Ohne Befund still.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

WERKZEUG = Path(__file__).resolve().parent.parent / "tools" / "formular_pruefen.py"
ZIELE = ("FORMULAR-SPEZ.md", "BAULOG.md", "FORMULAR-FREIGABE.md")


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
    if "/praesentationen/eval/" not in teile or Path(teile).name not in ZIELE:
        sys.exit(0)
    ordner = Path(teile).parent
    if not ordner.exists() or not WERKZEUG.exists():
        sys.exit(0)
    try:
        lauf = subprocess.run(
            [sys.executable, str(WERKZEUG), str(ordner), "--ausloeser", "hook"],
            capture_output=True, text=True, timeout=20,
            cwd=daten.get("cwd") or None)
    except Exception as e:
        # Ein kaputtes Gate darf nicht wie ein grünes aussehen.
        print(f"Formular-Gate konnte nicht laufen: {e}", file=sys.stderr)
        sys.exit(2)
    if lauf.returncode == 0:
        sys.exit(0)
    if lauf.returncode == 1 and lauf.stdout.strip():
        print(
            "Formular-Befunde (FB-Regeln, gemessen):\n" + lauf.stdout.strip()
            + "\n\nFB-G1 heißt Spez-Format, FB-G2 heißt Fragetext weicht vom "
            "Board ab, FB-G3 heißt Schutzregel verletzt (Anonymität, getrennte "
            "Freigaben, GF-Bogen, interne Regel sichtbar), FB-G4 heißt Baulog, "
            "FB-G5 heißt Freigabe ohne Bau oder mit veraltetem Stand.",
            file=sys.stderr,
        )
        sys.exit(2)
    print(
        f"Formular-Gate unerwartet beendet (rc={lauf.returncode}):\n"
        + (lauf.stderr or lauf.stdout or "keine Ausgabe")[-800:],
        file=sys.stderr,
    )
    sys.exit(2)


if __name__ == "__main__":
    main()
