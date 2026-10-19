#!/usr/bin/env python3
"""PostToolUse: fährt das Tagesdetail-Gate, sobald ein Tagesblatt
unter praesentationen/tagesdetails/ geschrieben wurde (TD-05).

Exit 2 trägt die Befunde sofort an das Modell zurück. Ohne Befund still.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

WERKZEUG = Path(__file__).resolve().parent.parent / "tools" / "tagesdetail_pruefen.py"


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
    # Tagesblaetter lagen unter praesentationen/tagesdetails/<ID>.md und liegen
    # seit dem Umzug als praesentationen/sessions/<ID>/TAGESBLATT.md. Beide Orte
    # gelten, sonst faellt dieser Hook still aus.
    alt_ort = "/praesentationen/tagesdetails/" in teile and teile.endswith(".md")
    neu_ort = ("/praesentationen/sessions/" in teile
               or teile.startswith("praesentationen/sessions/")) \
              and Path(teile).name == "TAGESBLATT.md"
    if not alt_ort and not neu_ort:
        sys.exit(0)
    if not Path(teile).exists() or not WERKZEUG.exists():
        sys.exit(0)
    try:
        lauf = subprocess.run(
            [sys.executable, str(WERKZEUG), teile, "--ausloeser", "hook"],
            capture_output=True, text=True, timeout=20,
            cwd=daten.get("cwd") or None)
    except Exception as e:
        # Ein kaputtes Gate darf nicht wie ein grünes aussehen.
        print(f"Tagesdetail-Gate konnte nicht laufen: {e}", file=sys.stderr)
        sys.exit(2)
    if lauf.returncode == 0:
        sys.exit(0)
    if lauf.returncode == 1 and lauf.stdout.strip():
        print(
            "Tagesdetail-Befunde (TD-Regeln, gemessen):\n" + lauf.stdout.strip()
            + "\n\nD-01 heißt Kopffeld/Whitelist, D-02 heißt Zeile ohne "
            "Quelle, D-03 heißt Minuten-Arithmetik, D-04 heißt Lücke nicht "
            "gespiegelt, D-05 heißt toter Verweis.",
            file=sys.stderr,
        )
        sys.exit(2)
    print(
        f"Tagesdetail-Gate unerwartet beendet (rc={lauf.returncode}):\n"
        + (lauf.stderr or lauf.stdout or "keine Ausgabe")[-800:],
        file=sys.stderr,
    )
    sys.exit(2)


if __name__ == "__main__":
    main()
