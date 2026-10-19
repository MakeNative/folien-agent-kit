#!/usr/bin/env python3
"""Layout-Gate für gebaute PPTX-Decks: findet überlappenden und überlaufenden Text.

    python3 tools/layout_pruefen.py <deck.pptx> [--ausgabe <ordner>] [--pdf <export.pdf>]
            [--schrift <variable-font.ttf>] [--erlaubt <regex>]

Warum es dieses Gate gibt: LibreOffice ersetzt im Headless-Betrieb Schriften
stillschweigend (z. B. eine Groteske durch Linux Libertine, schmaler). Ein Gate
oder eine Sichtprüfung auf diesem Rendering sieht sauber aus, während in
PowerPoint Titel in Untertitel und Kartentitel in Kartentexte laufen. Genau das
ist passiert — elf Folien, keine Meldung.

Darum gilt hier:
1. Gerendert wird mit PowerPoint selbst (macOS, AppleScript-Export als PDF in den
   PowerPoint-Container). Taucht im PDF eine Schrift auf, die nicht zu --erlaubt
   passt, bricht das Gate ab — dann ist jede Messung wertlos.
2. Prüfung A misst im PDF: Überlappen sich Wörter aus verschiedenen Zeilen?
   Unabhängig von jeder Schätzung.
3. Prüfung B misst je Textform mit den echten Glyphenbreiten (--schrift, eine
   Variable Font mit wght-Achse), ob der umbrochene Text aus seiner Form oder
   Karte läuft, eine andere Form oder ein Bild trifft oder ein Wort breiter als
   sein Kasten ist. Umbrochen wird pessimistisch ab 97 % der Kastenbreite.

Exit-Code 0 = kein Befund, 1 = Befunde, 2 = Messung unmöglich.
Erzeugt PNGs je Folie (100 dpi) für den Agenten folien-layout-pruefer.
"""
import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import ImageFont
from pptx import Presentation
from pptx.util import Emu

SCHRIFT = Path.home() / "Library/Fonts/InstrumentSans[wdth,wght].ttf"   # per --schrift
ERLAUBT = re.compile(r"^(InstrumentSans|Calibri)")   # per --erlaubt; Calibri: leere Notizrahmen
SCHNITTE = {"thin": 100, "extralight": 200, "light": 300, "medium": 500,
            "semibold": 600, "bold": 700, "extrabold": 800, "black": 900}


def gewicht(name):
    """Gewicht aus dem Schriftnamen der Vorlage („Instrument Sans SemiBold“ → 600)."""
    letztes = (name or "").split()[-1].lower() if name else ""
    return SCHNITTE.get(letztes, 400)
ZEILE = 1.2          # Zeilenhöhe als Vielfaches der Schriftgröße (PowerPoint-Standard)
PT = 12700
NUTZBAR = 0.97       # Anteil der Kastenbreite, bis zu dem eine Zeile sicher hält


def exportiere(pptx: Path, ziel: Path) -> Path:
    """PDF-Export durch PowerPoint. PowerPoint ist sandboxed: es schreibt nur
    zuverlässig in seinen eigenen Container. Die Präsentation wird über ihren
    Namen angesprochen (nie "active presentation" — eine andere offene
    Präsentation des Nutzers wäre sonst das Ziel) und nur sie wird geschlossen."""
    import time
    box = Path.home() / "Library/Containers/com.microsoft.Powerpoint/Data/tmp/layout-gate"
    box.mkdir(parents=True, exist_ok=True)
    name = f"gate-{int(time.time())}-{pptx.name}"
    kopie, pdf_box = box / name, box / (Path(name).stem + ".pdf")
    shutil.copy(pptx, kopie)
    osa = lambda t: subprocess.run(["osascript", "-e", t], capture_output=True, text=True)
    osa(f'tell application "Microsoft PowerPoint" to open POSIX file "{kopie}"')
    for _ in range(60):
        r = osa('tell application "Microsoft PowerPoint" to get name of every presentation')
        if name in r.stdout:
            break
        time.sleep(1)
    else:
        sys.exit(f"ABBRUCH: PowerPoint hat {name} nicht geöffnet (Dialog offen?).")
    r = osa(f'''tell application "Microsoft PowerPoint"
  set p to presentation "{name}"
  save p in POSIX file "{pdf_box}" as save as PDF
  close p saving no
end tell''')
    if r.returncode or not pdf_box.exists():
        sys.exit(f"ABBRUCH: PowerPoint-Export fehlgeschlagen: {r.stderr.strip()}")
    pdf = ziel / (pptx.stem + ".pdf")
    shutil.move(pdf_box, pdf)
    kopie.unlink(missing_ok=True)
    return pdf


def schriften_ok(pdf: Path):
    out = subprocess.run(["pdffonts", str(pdf)], capture_output=True, text=True).stdout
    namen = {re.sub(r"^[A-Z]{6}\+", "", z.split()[0]) for z in out.splitlines()[2:] if z.strip()}
    return sorted(n for n in namen if not ERLAUBT.match(n))


# ---------- Prüfung A: Wörter, die sich im gerenderten PDF überlappen ----------

def woerter(pdf: Path):
    out = subprocess.run(["pdftotext", "-bbox", str(pdf), "-"],
                         capture_output=True, text=True).stdout
    seiten, aktuell = [], None
    for z in out.splitlines():
        if z.lstrip().startswith("<page"):
            aktuell = []
            seiten.append(aktuell)
        m = re.search(r'xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">(.*)</word>', z)
        if m and aktuell is not None:
            x0, y0, x1, y1 = map(float, m.groups()[:4])
            aktuell.append((x0, y0, x1, y1, m.group(5)))
    return seiten


def ueberlappungen(seite):
    befunde = []
    for i, a in enumerate(seite):
        for b in seite[i + 1:]:
            # gleiche Zeile (gleiche Grundlinie) ist kein Überlappen, sondern Kerning
            # Grundlinienabstand in Zeilenhöhen: < 0.25 = dieselbe Zeile,
            # >= 0.7 = normaler (auch enger) Zeilenabstand. Geeicht 19.10.2026 am
            # PowerPoint-PDF: Titelzeilen 0.83–0.88, echte Überlappungen 0.37–0.61.
            abstand = abs(a[3] - b[3]) / min(a[3] - a[1], b[3] - b[1])
            if abstand < 0.25 or abstand >= 0.7:
                continue
            w = min(a[2], b[2]) - max(a[0], b[0])
            h = min(a[3], b[3]) - max(a[1], b[1])
            if w <= 0 or h <= 0:
                continue
            kleiner = min((a[2] - a[0]) * (a[3] - a[1]), (b[2] - b[0]) * (b[3] - b[1]))
            if w * h > 0.12 * kleiner:
                befunde.append(f"„{a[4]}“ überlappt „{b[4]}“")
    return befunde


# ---------- Prüfung B: umbrochener Text mit echten Glyphenbreiten ----------

_cache = {}
A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"


def font(gewicht, pt):
    key = (gewicht, round(pt * 4))
    if key not in _cache:
        f = ImageFont.truetype(str(SCHRIFT), size=max(1, round(pt * 4)))
        achsen = f.get_variation_axes()
        f.set_variation_by_axes([gewicht if a.get("name", b"") in (b"Weight", "Weight")
                                 else a["default"] for a in achsen])
        _cache[key] = f
    return _cache[key]


def umbrechen(text, f, breite_px, spc_px):
    """Zeilen wie PowerPoint umbrechen; liefert (Zeilenbreiten, zu breite Wörter)."""
    laenge = lambda t: f.getlength(t) + spc_px * len(t)
    breiten, zu_breit = [], []
    for absatz in text.split("\n"):
        zeile = ""
        for w in absatz.split(" "):
            if laenge(w) > breite_px:
                zu_breit.append(w)
            probe = (zeile + " " + w).strip()
            if laenge(probe) <= breite_px or not zeile:
                zeile = probe
            else:
                breiten.append(laenge(zeile))
                zeile = w
        breiten.append(laenge(zeile))
    return breiten, zu_breit


def alle_formen(container, trafo=(0, 0, 1, 1)):
    """Alle Formen mit absoluten Koordinaten (x, y, b, h) — Gruppen umgerechnet."""
    ox, oy, sx, sy = trafo
    for sh in container.shapes:
        if sh.left is None or sh.width is None:
            continue
        x, y = ox + sh.left * sx, oy + sh.top * sy
        b, h = sh.width * sx, sh.height * sy
        if sh.shape_type == 6 and hasattr(sh, "shapes"):
            xf = sh._element.grpSpPr.find(A + "xfrm")
            ch_off, ch_ext = xf.find(A + "chOff"), xf.find(A + "chExt")
            cx, cy = int(ch_off.get("x")), int(ch_off.get("y"))
            cb, chh = int(ch_ext.get("cx")) or 1, int(ch_ext.get("cy")) or 1
            nsx, nsy = b / cb, h / chh
            yield from alle_formen(sh, (x - cx * nsx, y - cy * nsy, nsx, nsy))
        else:
            yield sh, (x, y, b, h)


def textmass(sh, b):
    tf = sh.text_frame
    runs = [r for p in tf.paragraphs for r in p.runs if r.text.strip()]
    if not runs:
        return None
    pt = max((r.font.size.pt for r in runs if r.font.size), default=18)
    name = next((r.font.name for r in runs if r.font.name), "Instrument Sans")
    rpr = runs[0]._r.find(A + "rPr")
    spc = int(rpr.get("spc", 0)) / 100 if rpr is not None else 0     # pt je Zeichen
    bp = tf._txBody.find(A + "bodyPr")
    if bp is not None and bp.get("wrap") == "none":
        return None                      # bewusst ohne Umbruch gesetzt
    ins = lambda k, d: int(bp.get(k, d)) if bp is not None else d
    li, ri, ti = ins("lIns", 91440), ins("rIns", 91440), ins("tIns", 45720)
    breite_pt = (b - li - ri) / PT
    # Pessimistisch umbrechen: PowerPoint bricht bei 0.996 der gemessenen Breite um,
    # bei 0.991 nicht (geeicht 19.10.2026). Alles über 97 % gilt als Umbruch —
    # so knapp gesetzter Text kippt bei jeder Schrift- oder Versionsabweichung.
    breiten, zu_breit = umbrechen(tf.text, font(gewicht(name), pt),
                                  breite_pt * 4 * NUTZBAR, spc * 4)
    return dict(pt=pt, n=len(breiten), hoehe=(ti / PT + len(breiten) * pt * ZEILE) * PT,
                breite=(li / PT + max(breiten) / 4) * PT, zu_breit=zu_breit)


def schneidet(a, b):
    return a[0] < b[0] + b[2] and b[0] < a[0] + a[2] and a[1] < b[1] + b[3] and b[1] < a[1] + a[3]


def enthaelt(aussen, innen):
    return (aussen[0] <= innen[0] + 1 and aussen[1] <= innen[1] + 1 and
            aussen[0] + aussen[2] >= innen[0] + innen[2] - 1 and
            aussen[1] + aussen[3] >= innen[1] + innen[3] - 1)


def formen_befunde(prs):
    befunde = {}
    W, H = prs.slide_width, prs.slide_height
    for nr, folie in enumerate(prs.slides, 1):
        formen = [(sh, g) for sh, g in alle_formen(folie)
                  if g[2] > 0 and g[3] > 0 and g[2] * g[3] < 0.30 * W * H   # Deko raus
                  and not (sh.shape_type == 13 and not sh.has_text_frame and
                           (g[0] <= 0 or g[1] <= 0 or g[0] + g[2] >= W or g[1] + g[3] >= H))]
        # Bilder, die an den Folienrand stoßen, sind Schimmer/Verläufe der Vorlage
        melde = lambda t: befunde.setdefault(nr, []).append(t)
        for sh, g in formen:
            if not sh.has_text_frame or not sh.text_frame.text.strip():
                continue
            m = textmass(sh, g[2])
            if not m:
                continue
            kurz = sh.text_frame.text.strip().replace("\n", " ")[:40]
            for w in m["zu_breit"]:
                melde(f"„{kurz}“: Wort „{w}“ ist breiter als der Kasten — bricht mitten im Wort")
            text = (g[0], g[1], m["breite"], m["hoehe"])
            # kleinster Behälter (Karte), in dem die Form sitzt
            behaelter = [h for s, h in formen if s is not sh and enthaelt(h, g) and h != g]
            karte = min(behaelter, key=lambda h: h[2] * h[3]) if behaelter else None
            if karte and m["n"] > 1 and text[1] + text[3] > karte[1] + karte[3] + 2 * PT:
                melde(f"„{kurz}“ ({m['pt']:.0f} pt, {m['n']} Zeilen) läuft aus seiner Karte")
            for andere, h in formen:
                if andere is sh or enthaelt(h, g) or enthaelt(g, h) and not andere.has_text_frame:
                    continue
                if not (andere.shape_type == 13 or (andere.has_text_frame and andere.text_frame.text.strip())
                        or (karte is None)):
                    continue
                # nur der Teil, der über den eigenen Kasten hinausragt, kann kollidieren
                ueber_unten = m["n"] > 1 and text[1] + text[3] > g[1] + g[3] + 2 * PT
                ueber_rechts = text[0] + text[2] > g[0] + g[2]
                # einzeiliger Text bleibt vertikal in seinem Kasten (Zeilenhöhe > Kastenhöhe
                # ist bei großen Zahlen normal und kein Überlauf)
                rein = (g[0], g[1], text[2], text[3] if m["n"] > 1 else g[3])
                if not schneidet(rein, h) or schneidet(g, h) and not ueber_unten and not ueber_rechts:
                    if not (andere.shape_type == 13 and schneidet((g[0], g[1], text[2], g[3]), h)):
                        continue
                ziel = andere.text_frame.text.strip()[:30] if andere.has_text_frame and \
                    andere.text_frame.text.strip() else f"Bild/Fläche „{andere.name}“"
                melde(f"„{kurz}“ ({m['pt']:.0f} pt, {m['n']} Zeilen) läuft in {ziel}")
                break
    return befunde


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("deck")
    ap.add_argument("--ausgabe", default=None)
    ap.add_argument("--schrift", default=None, help="Variable Font (TTF) der Vorlage")
    ap.add_argument("--erlaubt", default=None, help="Regex erlaubter PDF-Schriftnamen")
    ap.add_argument("--pdf", default=None,
                    help="vorhandenen PowerPoint-PDF-Export verwenden statt neu zu exportieren")
    a = ap.parse_args()
    global SCHRIFT, ERLAUBT
    if a.schrift:
        SCHRIFT = Path(a.schrift)
    if a.erlaubt:
        ERLAUBT = re.compile(a.erlaubt)
    deck = Path(a.deck).resolve()
    ziel = Path(a.ausgabe or tempfile.mkdtemp(prefix="layout-")).resolve()
    ziel.mkdir(parents=True, exist_ok=True)

    pdf = Path(a.pdf).resolve() if a.pdf else exportiere(deck, ziel)
    fremd = schriften_ok(pdf)
    if fremd:
        print(f"ABBRUCH: Ersatzschrift im Rendering ({', '.join(fremd)}). Messung wertlos.")
        sys.exit(2)
    subprocess.run(["pdftoppm", "-r", "100", "-png", str(pdf), str(ziel / "folie")], check=True)

    befunde = {}
    seiten = woerter(pdf)
    if not seiten or not any(seiten):
        print("ABBRUCH: Prüfung A hat keine Wörter gelesen — Messung wertlos.")
        sys.exit(2)
    for nr, seite in enumerate(seiten, 1):
        for b in ueberlappungen(seite):
            befunde.setdefault(nr, []).append("A " + b)
    for nr, liste in formen_befunde(Presentation(deck)).items():
        for b in liste:
            befunde.setdefault(nr, []).append("B " + b)

    print(f"{deck.name} · Rendering PowerPoint · Schriften ok · PNGs: {ziel}")
    if not befunde:
        print("Kein Befund.")
        sys.exit(0)
    for nr in sorted(befunde):
        print(f"  Folie {nr}:")
        for b in dict.fromkeys(befunde[nr]):
            print(f"    {b}")
    print(f"\n{sum(len(set(v)) for v in befunde.values())} Befunde auf {len(befunde)} Folien.")
    sys.exit(1)


if __name__ == "__main__":
    main()
