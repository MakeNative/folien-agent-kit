#!/usr/bin/env python3
"""Rendert einzelne Deck-Marken neu, ohne den ganzen Asset-Lauf zu wiederholen.

    marke_rendern.py sessions/S2 f2 f14 f16
    marke_rendern.py --liste sessions/S2

Jeder Session-Ordner ist ein HyperFrames-Projekt unter `assets/quellen/`.
Dessen `index.html` montiert immer GENAU EINE Komposition; der Schnappschuss
nimmt den Host, nicht die Komposition. Darum wird der Host je Marke
umgehaengt und danach zurueckgesetzt — bleibt er umgehaengt, rendert der
naechste Lauf die falsche Marke.

Die HyperFrames-Version kommt aus der package.json des Projekts, nicht aus
`npx hyperframes` (dort steht inzwischen eine neuere; eine andere Fassung
kann anders setzen, und die Bilder sollen zum Bestand passen).
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

HOST = """<!doctype html>
<html lang="de">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=1920, height=1080" />
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
    <style>
      * {{ margin: 0; padding: 0; box-sizing: border-box; }}
      html, body {{ margin: 0; width: 1920px; height: 1080px;
                   overflow: hidden; background: #f6f7f9; }}
      #stage {{ position: relative; width: 100%; height: 100%; }}
      .clip {{ position: absolute; inset: 0; }}
    </style>
  </head>
  <body>
    <div id="stage" data-composition-id="main" data-start="0" data-duration="1"
         data-fps="30" data-width="1920" data-height="1080">
      <div id="{name}-host" class="clip" data-composition-id="{name}"
           data-composition-src="compositions/{name}.html" data-start="0"
           data-duration="1" data-track-index="0"
           data-width="1920" data-height="1080"></div>
    </div>
    <script>
      // Standbild: Host-Timeline angehalten auf 0.
      const tl = gsap.timeline({{ paused: true }});
      window.__timelines["main"] = tl;
      tl.seek(0);
    </script>
  </body>
</html>
"""


def version(projekt: Path) -> str:
    pj = projekt / "package.json"
    if pj.exists():
        m = re.search(r"hyperframes@([\d.]+)", pj.read_text(encoding="utf-8"))
        if m:
            return m.group(1)
    return "latest"


def ledger_karte(projekt: Path) -> dict[str, tuple[str, float]]:
    """compositions/<name>.html -> (Zieldatei, Schnappschuss-Sekunde).

    Die Zuordnung steht im LEDGER, nicht im Dateinamen: `stacktrace.html`
    wird zu `F15.png`, und manche Marke wird nicht bei 0.5 s genommen,
    sondern am Schluss-Hold eines Clips. Beides aus dem Namen zu raten
    hiesse, die falsche Datei zu ueberschreiben.
    """
    karte: dict[str, tuple[str, float]] = {}
    pfad = projekt.parent / "LEDGER.md"
    if not pfad.exists():
        return karte
    for z in pfad.read_text(encoding="utf-8").splitlines():
        teile = [x.strip() for x in z.split("|")]
        if len(teile) < 4 or not teile[0].lower().endswith(".png"):
            continue
        m = re.search(r"compositions/([\w-]+)\.html", teile[3])
        if not m:
            continue
        s = re.search(r"Snapshot bei ([\d.]+)", teile[3])
        karte[m.group(1)] = (teile[0], float(s.group(1)) if s else 0.5)
    return karte


def rendern(sess: Path, namen: list[str]) -> int:
    projekt = sess / "assets" / "quellen"
    if not (projekt / "hyperframes.json").exists():
        print(f"  ! {sess.name}: kein HyperFrames-Projekt unter assets/quellen")
        return 1
    hf = version(projekt)
    karte = ledger_karte(projekt)
    sicherung = (projekt / "index.html").read_text(encoding="utf-8")
    snap = projekt / "snapshots"
    fehler = 0
    try:
        for name in namen:
            komp = projekt / "compositions" / f"{name}.html"
            if not komp.exists():
                print(f"  ! {sess.name}/{name}: compositions/{name}.html fehlt")
                fehler = 1
                continue
            (projekt / "index.html").write_text(HOST.format(name=name),
                                                encoding="utf-8")
            # Nicht aufraeumen, was wir nicht angelegt haben: In
            # snapshots/ liegen auch die Frames frueherer Clip-Laeufe.
            # Der Schnappschuss schreibt unter demselben Namen wie ein
            # frueherer Lauf, darum entscheidet die Zeit, nicht der Name.
            # (Gefunden 19.10.2026, nachdem dieser Lauf zwei Clip-Frames
            # von S1 geloescht hatte.)
            schwelle = time.time()
            dateiname, sekunde = karte.get(name, (name.upper() + ".png", 0.5))
            r = subprocess.run(
                ["npx", "--yes", f"hyperframes@{hf}", "snapshot",
                 "--at", str(sekunde)],
                cwd=projekt, capture_output=True, text=True, timeout=900)
            bilder = sorted((f for f in snap.glob("frame-*.png")
                             if f.stat().st_mtime >= schwelle),
                            key=lambda f: f.stat().st_mtime)
            if r.returncode != 0 or not bilder:
                letzte = (r.stderr or r.stdout or "").strip().splitlines()
                print(f"  ! {sess.name}/{name}: Schnappschuss fehlgeschlagen — "
                      f"{(letzte or ['kein Grund gemeldet'])[-1][:150]}")
                fehler = 1
                continue
            ziel = projekt.parent / dateiname
            shutil.copy2(bilder[0], ziel)
            kb = ziel.stat().st_size // 1024
            print(f"  {sess.name}/{name} -> {ziel.name}  "
                  f"({kb} KB, bei {sekunde} s, hf {hf})")
    finally:
        (projekt / "index.html").write_text(sicherung, encoding="utf-8")
    return fehler


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        raise SystemExit(__doc__)
    sess = Path(args[0])
    if "--liste" in sys.argv:
        k = sess / "assets" / "quellen" / "compositions"
        print(" ".join(sorted(p.stem for p in k.glob("*.html"))))
        return 0
    return rendern(sess, args[1:])


if __name__ == "__main__":
    sys.exit(main())
