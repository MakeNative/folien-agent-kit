#!/usr/bin/env python3
"""Selbsttest für layout_pruefen.py — nagelt die Eichpunkte fest.

    python3 tools/layout_selbsttest.py

Braucht python-pptx und Pillow, aber weder PowerPoint noch ein Deck. Jeder
Fehlalarm oder Durchrutscher am Gate bekommt hier einen Fall.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import layout_pruefen as L  # noqa: E402

fehler = []


def pruefe(name, ist, soll):
    if ist != soll:
        fehler.append(f"{name}: ist {ist!r}, soll {soll!r}")


# Prüfung A — Grundlinienabstand in Zeilenhöhen (Wortrahmen aus pdftotext -bbox)
wort = lambda x0, y0, x1, y1, t: (x0, y0, x1, y1, t)
# zweizeiliger Titel mit engem Zeilenabstand (0.85 Zeilenhöhen) ist KEIN Befund
titel = [wort(100, 100, 300, 160, "Erst"), wort(100, 151, 300, 211, "Aussehen.")]
pruefe("Titel eng gesetzt", L.ueberlappungen(titel), [])
# Kartentitel-Zeile 2 läuft in Kartentext (0.37 Zeilenhöhen) ist ein Befund
karte = [wort(1163, 547, 1247, 575, "Ranking"), wort(1163, 561, 1321, 586, "Kundenfeedback,")]
pruefe("Kartentitel in Kartentext", len(L.ueberlappungen(karte)), 1)
# Wörter derselben Zeile (Kerning) sind kein Befund
zeile = [wort(100, 100, 160, 130, "Wort"), wort(158, 100, 220, 130, "zwei")]
pruefe("gleiche Zeile", L.ueberlappungen(zeile), [])

# Prüfung B — Umbruch mit echten Glyphenbreiten, pessimistisch ab 97 %
if L.SCHRIFT.exists():
    f = L.font(600, 54)
    breite = f.getlength("Erst der Inhalt, dann das Aussehen.")
    # 99,6 % der Breite: PowerPoint bricht um — das Gate muss es auch
    zeilen, _ = L.umbrechen("Erst der Inhalt, dann das Aussehen.", f, breite / 0.996 * L.NUTZBAR, 0)
    pruefe("99,6 % bricht um", len(zeilen), 2)
    # 90 %: passt sicher auf eine Zeile
    zeilen, _ = L.umbrechen("Erst der Inhalt, dann das Aussehen.", f, breite / 0.90 * L.NUTZBAR, 0)
    pruefe("90 % bleibt einzeilig", len(zeilen), 1)
    # Wort breiter als der Kasten („J / a“)
    _, zu_breit = L.umbrechen("Ja", L.font(400, 18), 10, 0)
    pruefe("Wortbruch erkannt", zu_breit, ["Ja"])
else:
    print(f"Hinweis: {L.SCHRIFT} fehlt — Umbruchtests übersprungen")

pruefe("Gewicht SemiBold", L.gewicht("Instrument Sans SemiBold"), 600)
pruefe("Gewicht Regular", L.gewicht("Instrument Sans"), 400)

if fehler:
    print("\n".join(fehler))
    sys.exit(1)
print("layout_pruefen: Selbsttest grün.")
