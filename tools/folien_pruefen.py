#!/usr/bin/env python3
"""Prüft Dünn-Decks gegen die messbaren Leinwand-Regeln.

    folien_pruefen.py <deck.md> [...] [--still]

Geprüft wird nur Mechanisches (P-04):
  F-01  Folienbudget: Kopfzeile `Budget: <n> Folien` wird gegen die Zahl
        der `## Folie`-Überschriften gehalten (Quellen-Folie zählt mit).
  F-02  Sichtbarer Text je Folie ≤ 70 Wörter (Bullets und Freitext;
        nicht gezählt: Sprechnotiz:, Demo:, Jetzt du:, Form:, Skizze:,
        Handout:, Code-Zäune, Folientitel).
  F-03  Ein Gedanke je Folie: höchstens EIN zusammenhängender Bullet-Block.
  F-04  Keine Fußnoten auf der Leinwand: `[^...]` ist verboten; Belege
        gehören ins Handout. Erlaubt ist je Folie eine `Handout:`-Zeile.
  F-05  Beispiel vor Regel: trägt eine Folie eine `Regel:`-Zeile, muss
        davor auf derselben Folie eine `Beispiel:`-Zeile stehen.
  F-06  Leinwandzeit: Summe der `(~n min)`-Angaben der Folientitel gegen
        die Kopfzeile `Leinwandzeit: <n> min` — sie müssen gleich sein, und
        die Summe darf die Untergrenze ZIELZEIT_UNTEN nicht unterschreiten.
        Nur Folientitel zählen; Minutenangaben in der Dramaturgie-Prosa
        bleiben außen vor.
  F-07  Abdeckung: liegt neben dem Deck eine SPEZIFIKATION-<name>.md mit
        `MUSS:`-Zeilen (`MUSS: <schlagwort> — Handout: <anker> — <n> min`),
        muss jedes Schlagwort im Deck vorkommen — außer die Zeile trägt
        `GESTRICHEN (<grund>)`. Ein abgenommenes Deck ohne einen MUSS-Punkt
        war der einzige stille Durchrutscher des Pilotlaufs.

Trägt der Kopf `Grammatik: v2`, gelten zusätzlich die Regeln der
FOLIEN-GRAMMATIK.md (07.10.2026) — und F-02 wird durch F-09 ersetzt:
  F-08  Jede Folie deklariert `Typ:` (A, K, D, STORY, POLL, QUIZ, PRIMING,
        UEBUNG, ABSCHLUSS).
  F-09  Wortbudget je Typ (A 15 · K 45 · D 25 · STORY 20 · POLL 40 ·
        QUIZ 50 · PRIMING 30 · UEBUNG 60 · ABSCHLUSS 40).
  F-10  Folientitel ist eine Behauptung: 4–15 Wörter, endet nicht auf
        Doppelpunkt. (Ob wirklich ein Verb trägt, prüft der Lese-Test.)
  F-11  K-Folien: 2–4 Stichpunktzeilen à höchstens 7 Wörter.
  F-12  Rhythmus über die Inhaltsfolien (A/K/D): A-Anteil 20–35 %, nie
        zwei A in Folge, nie mehr als 4 Nicht-A am Stück (Workshop-Folien
        setzen die Zählung zurück).
  F-13  Deck-Lesebudget: sichtbare Wörter der A/K/D-Folien ≤ 20 × die
        Kopfzeile `Input: <n> min`.
  F-14  Pflicht-Slots ab 45 min Leinwandzeit: ≥1 STORY, ≥1 POLL, ≥2 QUIZ,
        ≥1 PRIMING, ≥1 UEBUNG, ≥1 ABSCHLUSS.
  F-15  `Icon:`-Zeilen nur mit Namen aus praesentationen/pptx/
        ICON-LEXIKON.md.
  F-16  Gesperrte Folklore-Zahlen (22×-Story-Zahl, 10-Minuten-
        Aufmerksamkeit, „behalten 10 %") dürfen nirgends auftauchen.
  F-17  Begriff-vor-Gebrauch: erste sichtbare Zeile einer `Typ: B`-Folie
        ist der Kursbegriff; vor dieser Folie darf er nirgends sichtbar
        stehen.
  F-18  Kernsatz: Kopfzeile `Kernsatz: <Satz>`, wörtlich auf genau einer
        A-Folie (Peak) und auf der ABSCHLUSS-Folie.
  F-19  Sprechnotiz-Format: je Folie KERN:/SAGEN:/UEBERGANG: (TUN: bei
        D/POLL/QUIZ/PRIMING/UEBUNG); SAGEN-Block ≥ 60 Wörter.

Exit 0 ohne Befund, 1 mit Befunden. Schreibt gates/folien-report.md,
wenn das Deck in einem Dokumentprojekt liegt.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import gemeinsam as g  # noqa: E402

FOLIE = re.compile(
    r"^## Folie (\d+):?\s*([^\n]*?)\s*(?:\(~(\d+)\s*min\))?\s*$", re.M)
WORT = re.compile(r"\b[\wäöüÄÖÜß-]+\b")
META = ("Sprechnotiz:", "Demo:", "Jetzt du:", "Form:", "Skizze:",
        "**Form:**", "**Skizze:**",
        "Handout:", "Grafik:", "**Sprechnotiz", "**Demo", "**Jetzt du",
        "**Handout", "**Grafik", "Typ:", "Icon:", "**Typ", "**Icon",
        "Regie:", "**Regie", "KERN:", "SAGEN:", "TUN:", "UEBERGANG:",
        "**KERN", "**SAGEN", "**TUN", "**UEBERGANG",
        "BEI NACHFRAGE:", "**BEI NACHFRAGE")

# Grammatik v2 (FOLIEN-GRAMMATIK.md): Wortbudgets je Folientyp. Die alte
# 70er-Pauschale bleibt nur für nicht migrierte Decks ohne v2-Kopfzeile.
TYP_BUDGET = {"A": 15, "B": 25, "K": 45, "D": 25, "STORY": 20, "POLL": 40,
              "QUIZ": 50, "PRIMING": 30, "UEBUNG": 60, "ABSCHLUSS": 40}
INHALTSTYPEN = ("A", "B", "K", "D")
# TUN:-Block ist Pflicht, wo der Trainer Handgriffe hat.
TUN_PFLICHT = ("D", "POLL", "QUIZ", "PRIMING", "UEBUNG")
PFLICHT_SLOTS = {"STORY": 1, "POLL": 1, "QUIZ": 2, "PRIMING": 1,
                 "UEBUNG": 1, "ABSCHLUSS": 1}
# Folklore-Zahlen, die keine Quelle tragen (Recherche 07.10.2026).
GESPERRT = (
    (re.compile(r"22\s*[x×]", re.I), "22x-Story-Zahl ist ein Meme"),
    (re.compile(r"(?:10|zehn)\s*Minuten[^\n]{0,40}Aufmerksamkeit|"
                r"Aufmerksamkeit[^\n]{0,40}(?:10|zehn)\s*Minuten", re.I),
     "10-Minuten-Aufmerksamkeitsspanne ist unbelegt"),
    (re.compile(r"behalten\s+(?:nur\s+)?10\s*%", re.I),
     "Menschen-behalten-10-Prozent ist unbelegt"),
)

# Toleranzband um die Kopfzeile `Leinwandzeit:`. Die Zahl dort ist der
# Zielwert aus der Spezifikation, nicht eine Obergrenze: ein Deck darf etwas
# darüber liegen und ein Stück darunter, aber eine Präsentation, die den Raum
# nicht füllt, ist kein kurzer Erfolg, sondern eine dünne Session. Beim
# Programmzielwert 60 ergibt das die FIXPLAN-Spanne 55 bis 70.
TOLERANZ_UNTEN = 5
TOLERANZ_OBEN = 10


def folien_teilen(text: str) -> list[tuple[int, str, int | None, str]]:
    """Liefert (foliennummer, titel, minuten, folientext)."""
    treffer = list(FOLIE.finditer(text))
    ergebnis = []
    for i, m in enumerate(treffer):
        ende = treffer[i + 1].start() if i + 1 < len(treffer) else len(text)
        minuten = int(m.group(3)) if m.group(3) else None
        ergebnis.append((int(m.group(1)), (m.group(2) or "").strip(),
                         minuten, text[m.end():ende]))
    return ergebnis


def folien_typ(inhalt: str) -> str | None:
    """Liest die Meta-Zeile `Typ:` einer Folie (v2-Decks)."""
    m = re.search(r"^(?:\*\*)?Typ:(?:\*\*)?\s*([A-ZÄÖÜ]+)", inhalt, re.M)
    return m.group(1) if m else None


def lexikon_icons(deck: Path) -> set[str] | None:
    """Sucht aufwärts nach praesentationen/pptx/ICON-LEXIKON.md und liefert
    die erlaubten Lucide-Namen; None, wenn kein Lexikon zu finden ist."""
    for eltern in [deck.resolve().parent, *deck.resolve().parents]:
        kandidat = eltern / "pptx" / "ICON-LEXIKON.md"
        if kandidat.exists():
            text = kandidat.read_text(encoding="utf-8", errors="replace")
            return set(re.findall(r"^\|\s*`([a-z0-9-]+)`", text, re.M))
    return None


def sichtbarer_text(folie: str) -> list[str]:
    """Sichtbare Zeilen; Leerzeilen bleiben als "" erhalten, damit der
    Blockzähler Bullet-Gruppen trennen kann. META-Zeilen (Sprechnotiz: usw.)
    verschlucken auch ihre umbrochenen Folgezeilen bis zur Leerzeile —
    der Fehlbefund des ersten Pilotlaufs (12x F-02 auf einem sauberen Deck)."""
    zeilen, im_zaun, im_meta, out = folie.splitlines(), False, False, []
    for z in zeilen:
        s = z.strip()
        if s.startswith(("```", "~~~")):
            im_zaun = not im_zaun
            continue
        if im_zaun or s.startswith("---"):
            continue
        if not s:
            im_meta = False
            out.append(s)
            continue
        if any(s.startswith(m) for m in META):
            im_meta = True
            continue
        if im_meta:
            continue
        out.append(s)
    return out


def pruefen(datei: Path) -> list[dict]:
    text = datei.read_text(encoding="utf-8", errors="replace")
    b: list[dict] = []

    def befund(regel, ort, meldung):
        b.append({"regel": regel, "ort": f"{datei.name}:{ort}", "text": meldung})

    folien = folien_teilen(text)
    if not folien:
        befund("F-01", 1, "Keine `## Folie`-Überschriften gefunden — kein Dünn-Deck?")
        return b

    m = re.search(r"^Budget:\s*(\d+)\s*Folien", text, re.M)
    if not m:
        befund("F-01", 1, "Kopfzeile `Budget: <n> Folien` fehlt")
    elif len(folien) > int(m.group(1)):
        befund("F-01", 1, f"{len(folien)} Folien bei Budget {m.group(1)}")

    v2 = bool(re.search(r"^Grammatik:\s*v2", text, re.M))

    for nr, titel, minuten, inhalt in folien:
        zeilen = sichtbarer_text(inhalt)
        woerter = sum(len(WORT.findall(z)) for z in zeilen if z)
        typ = folien_typ(inhalt)
        if v2:
            # 07.10.2026: typbasierte Budgets nach FOLIEN-GRAMMATIK.md —
            # das Lesebudget (20 Wörter/min, Garner & Alley) ersetzt die
            # Pauschale, die das Text-Pendel nie gelöst hat.
            if typ is None or typ not in TYP_BUDGET:
                befund("F-08", nr, f"Folie {nr}: `Typ:` fehlt oder unbekannt "
                       f"({typ or 'keine Zeile'})")
            else:
                if woerter > TYP_BUDGET[typ]:
                    befund("F-09", nr, f"Folie {nr} ({typ}): {woerter} sichtbare "
                           f"Wörter (Budget {TYP_BUDGET[typ]})")
                if typ == "K":
                    bullets = [z for z in zeilen
                               if z.startswith(("-", "*", "•"))
                               or re.match(r"^\d+[.)]", z)]
                    if not 2 <= len(bullets) <= 4:
                        befund("F-11", nr, f"Folie {nr} (K): {len(bullets)} "
                               "Stichpunktzeilen (erlaubt 2–4)")
                    for bz in bullets:
                        bw = len(WORT.findall(bz))
                        if bw > 7:
                            befund("F-11", nr, f"Folie {nr} (K): Zeile mit "
                                   f"{bw} Wörtern (max 7): {bz[:50]}")
            tw = len(WORT.findall(titel))
            # B-Folien tragen den Begriff als Titel — die Behauptungs-Regel
            # gilt dort nicht (FOLIEN-GRAMMATIK §4, Ausnahme).
            if typ != "B" and titel and (tw < 4 or tw > 15
                                         or titel.rstrip().endswith(":")):
                befund("F-10", nr, f"Folie {nr}: Titel ist keine Behauptung "
                       f"in Budgetlänge ({tw} Wörter): {titel[:60]}")
        elif woerter > 70:
            # Alt-Regel für noch nicht migrierte Decks (06.10.2026).
            befund("F-02", nr, f"Folie {nr}: {woerter} sichtbare Wörter (max 70)")

        bloecke, offen = 0, False
        for z in zeilen:
            ist_bullet = z.startswith(("-", "*", "•")) or re.match(r"^\d+[.)]", z)
            if ist_bullet and not offen:
                bloecke += 1
            offen = ist_bullet
        if bloecke > 1:
            befund("F-03", nr, f"Folie {nr}: {bloecke} getrennte Bullet-Blöcke (max 1)")

        if re.search(r"\[\^[A-Za-z0-9][\w-]*\]", inhalt):
            befund("F-04", nr, f"Folie {nr}: Fußnote auf der Leinwand — gehört ins Handout")

        regel_pos = inhalt.find("Regel:")
        if regel_pos >= 0:
            beispiel_pos = inhalt.find("Beispiel:")
            if beispiel_pos < 0 or beispiel_pos > regel_pos:
                befund("F-05", nr, f"Folie {nr}: `Regel:` ohne vorangehendes `Beispiel:`")

    if v2:
        typen = [(nr, folien_typ(inhalt), inhalt)
                 for nr, _, _, inhalt in folien]
        inhaltsfolgen = [(nr, t) for nr, t, _ in typen if t in INHALTSTYPEN]
        if inhaltsfolgen:
            a_anteil = sum(1 for _, t in inhaltsfolgen if t == "A") / len(inhaltsfolgen)
            if not 0.20 <= a_anteil <= 0.35:
                befund("F-12", 1, f"A-Anteil {a_anteil:.0%} der Inhaltsfolien "
                       "(Zielband 20–35 %)")
        # Folgen: Workshop-Folien setzen die Nicht-A-Zählung zurück.
        vorher_a, ohne_anker = False, 0
        for nr, _, _, inhalt in folien:
            t = folien_typ(inhalt)
            if t == "A":
                if vorher_a:
                    befund("F-12", nr, f"Folie {nr}: zwei A-Folien in Folge")
                vorher_a, ohne_anker = True, 0
            elif t in INHALTSTYPEN:
                vorher_a = False
                ohne_anker += 1
                if ohne_anker == 5:
                    befund("F-12", nr, f"Folie {nr}: fünfte Inhaltsfolie "
                           "ohne neuen Anker (max 4)")
            else:
                vorher_a, ohne_anker = False, 0
        m_in = re.search(r"^Input:\s*(\d+)\s*min", text, re.M)
        if not m_in:
            befund("F-13", 1, "Kopfzeile `Input: <n> min` fehlt (Lesebudget)")
        else:
            budget = 20 * int(m_in.group(1))
            lesewoerter = sum(
                sum(len(WORT.findall(z)) for z in sichtbarer_text(inhalt) if z)
                for nr, _, _, inhalt in folien
                if folien_typ(inhalt) in INHALTSTYPEN)
            if lesewoerter > budget:
                befund("F-13", 1, f"{lesewoerter} sichtbare Wörter auf A/K/D-"
                       f"Folien — Lesebudget {budget} (20 × Input-Minuten)")
        mz = re.search(r"^Leinwandzeit:\s*(\d+)\s*min", text, re.M)
        if mz and int(mz.group(1)) >= 45:
            zaehler: dict[str, int] = {}
            for _, t, _ in typen:
                if t:
                    zaehler[t] = zaehler.get(t, 0) + 1
            for slot, soll_n in PFLICHT_SLOTS.items():
                if zaehler.get(slot, 0) < soll_n:
                    befund("F-14", 1, f"Pflicht-Slot {slot}: "
                           f"{zaehler.get(slot, 0)} von {soll_n} vorhanden")
        erlaubt = lexikon_icons(datei)
        for nr, _, _, inhalt in folien:
            for im in re.finditer(r"^(?:\*\*)?Icon:(?:\*\*)?\s*([a-z0-9-]+)",
                                  inhalt, re.M):
                if erlaubt is None:
                    befund("F-15", nr, "ICON-LEXIKON.md nicht gefunden — "
                           "Icon-Zeilen nicht prüfbar")
                    break
                if im.group(1) not in erlaubt:
                    befund("F-15", nr, f"Folie {nr}: Icon `{im.group(1)}` "
                           "steht nicht im Lexikon")
        for muster, grund in GESPERRT:
            tm = muster.search(text)
            if tm:
                befund("F-16", 1, f"Gesperrte Folklore-Zahl: {grund} "
                       f"(«{tm.group(0)[:30]}»)")

        # F-17: Begriff-vor-Gebrauch — die erste sichtbare Zeile einer
        # B-Folie ist der Kursbegriff; vor dieser Folie darf er nirgends
        # sichtbar stehen (Kundenentscheid nach dem T0-Pilot, 07.10.2026:
        # ein Poll mit „Sitzung" vor der Einführung war unlesbar).
        begriffe = []
        for nr, _, _, inhalt in folien:
            if folien_typ(inhalt) == "B":
                erste = [z for z in sichtbarer_text(inhalt) if z]
                if erste:
                    begriffe.append((erste[0].strip().rstrip("."), nr))
                else:
                    befund("F-17", nr, f"Folie {nr}: B-Folie ohne sichtbare "
                           "Begriffszeile")
        for beg, b_nr in begriffe:
            rx = re.compile(r"\b" + re.escape(beg), re.I)
            for nr, titel, _, inhalt in folien:
                if nr >= b_nr:
                    break
                sicht = titel + "\n" + "\n".join(sichtbarer_text(inhalt))
                if rx.search(sicht):
                    befund("F-17", nr, f"Folie {nr}: Kursbegriff "
                           f"„{beg}“ sichtbar vor seiner "
                           f"Begriff-Folie {b_nr}")

        # F-18: Kernsatz-Kette Kopfzeile -> genau eine A-Folie (Peak) ->
        # ABSCHLUSS.
        mk = re.search(r"^Kernsatz:\s*(.+)$", text, re.M)
        if not mk:
            befund("F-18", 1, "Kopfzeile `Kernsatz: <Satz>` fehlt")
        else:
            ks = mk.group(1).strip().rstrip(".")
            a_treffer, abschluss_treffer = [], 0
            for nr, titel, _, inhalt in folien:
                sicht = titel + "\n" + "\n".join(sichtbarer_text(inhalt))
                if ks and ks in sicht:
                    t = folien_typ(inhalt)
                    if t == "A":
                        a_treffer.append(nr)
                    elif t == "ABSCHLUSS":
                        abschluss_treffer += 1
            if len(a_treffer) != 1:
                befund("F-18", 1, f"Kernsatz steht wörtlich auf "
                       f"{len(a_treffer)} A-Folien (gefordert: genau eine, "
                       "der Peak)")
            if abschluss_treffer == 0:
                befund("F-18", 1, "Kernsatz fehlt wörtlich auf der "
                       "ABSCHLUSS-Folie")

        # F-19: Sprechnotiz-Format KERN/SAGEN/(TUN)/UEBERGANG je Folie;
        # SAGEN traegt den Vortrag und braucht Substanz.
        for nr, _, _, inhalt in folien:
            t = folien_typ(inhalt)
            fehlt = [b for b in ("KERN:", "SAGEN:", "UEBERGANG:")
                     if not re.search(r"^(?:\*\*)?" + b, inhalt, re.M)]
            if t in TUN_PFLICHT and not re.search(r"^(?:\*\*)?TUN:",
                                                  inhalt, re.M):
                fehlt.append("TUN:")
            if fehlt:
                befund("F-19", nr, f"Folie {nr}: Notiz-Bloecke fehlen: "
                       f"{', '.join(fehlt)}")
            ms = re.search(r"^(?:\*\*)?SAGEN:(.*?)(?=\n\s*\n|\Z)",
                           inhalt, re.M | re.S)
            if ms:
                sw = len(WORT.findall(ms.group(1)))
                if sw < 60:
                    befund("F-19", nr, f"Folie {nr}: SAGEN-Block zu duenn "
                           f"({sw} Woerter, min 60)")
                # Obergrenze seit dem Probelauf der Fassung 3: Notizen,
                # die alles tragen, sprengen die Uhr um 50 % — Vertiefung
                # gehoert in BEI NACHFRAGE:, nicht in den Pflichtpfad.
                elif sw > 160:
                    befund("F-19", nr, f"Folie {nr}: SAGEN-Block zu lang "
                           f"({sw} Woerter, max 160 — Rest nach "
                           "BEI NACHFRAGE:)")

    m = re.search(r"^Leinwandzeit:\s*(\d+)\s*min", text, re.M)
    if m:
        soll = int(m.group(1))
        ist = sum(mi for _, _, mi, _ in folien if mi)
        if ist > soll + TOLERANZ_OBEN:
            befund("F-06", 1,
                   f"Leinwandzeit {ist} min über der Spanne — Zielwert {soll} min, "
                   f"Toleranz bis {soll + TOLERANZ_OBEN} min")
        elif ist and ist < soll - TOLERANZ_UNTEN:
            # Die Untergrenze fehlte lange. Vier Decks des Programms lagen
            # still 6 bis 19 min unter ihrem Zielwert, und kein Gate sah es —
            # gemeldet hat es nur, wer die Decks von Hand nachgerechnet hat.
            befund("F-06", 1,
                   f"Session zu dünn: {ist} min Leinwandzeit, Zielwert {soll} min, "
                   f"Untergrenze {soll - TOLERANZ_UNTEN} min")
    else:
        befund("F-06", 1, "Kopfzeile `Leinwandzeit: <n> min` fehlt")

    # F-07: Abdeckung gegen die Spezifikation
    name = re.sub(r"^T?", "", datei.stem.split("-")[0]) or datei.stem
    spez = datei.parent / f"SPEZIFIKATION-{datei.stem.split('-')[0]}.md"
    if spez.exists():
        stext = spez.read_text(encoding="utf-8", errors="replace")
        tlow = text.lower()
        for sm in re.finditer(r"^MUSS:\s*([^—\n]+?)\s*(?:—|$)", stext, re.M):
            zeile_voll = stext[sm.start():stext.find("\n", sm.start())]
            if "GESTRICHEN" in zeile_voll:
                continue
            schlagwort = sm.group(1).strip()
            if schlagwort.lower() not in tlow:
                befund("F-07", 1,
                       f"MUSS-Punkt \u201e{schlagwort}\u201c aus {spez.name} kommt "
                       "im Deck nicht vor (und ist nicht als GESTRICHEN begründet)")

    return b


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("dateien", nargs="+")
    ap.add_argument("--still", action="store_true")
    ap.add_argument("--ausloeser", default="lauf", help="hook | lauf — fürs Protokoll")
    a = ap.parse_args()

    # Spezifikationen und Prüfberichte liegen neben den Decks, sind aber keine.
    # Der Hook überspringt sie schon; das CLI zieht hier nach, damit ein Glob
    # über decks/*.md keine Fehlalarme erzeugt.
    dateien = [
        Path(d) for d in a.dateien
        if Path(d).exists()
        and not Path(d).name.startswith("SPEZIFIKATION")
        and "pruefberichte" not in Path(d).as_posix()
    ]
    befunde = [x for d in dateien for x in pruefen(d)]

    w = g.wurzel(dateien[0].resolve().parent if dateien else None)
    if w is not None:
        z = ["<!-- GENERIERT von folien_pruefen.py -->", "# Gate: Folien", "",
             f"Stand {g.heute()} · {len(dateien)} Decks · {len(befunde)} Befunde", ""]
        z += [f"- `{x['ort']}` — {x['regel']} — {x['text']}" for x in befunde] or ["Kein Befund.", ""]
        g.bericht_schreiben(w, "folien-report.md", "\n".join(z))
        nach_regel: dict[str, int] = {}
        for x in befunde:
            nach_regel[x["regel"]] = nach_regel.get(x["regel"], 0) + 1
        details = {}
        for d in dateien:
            txt = d.read_text(encoding="utf-8", errors="replace")
            fol = folien_teilen(txt)
            details[d.name] = {"folien": len(fol),
                               "minuten": sum(mi for _, _, mi, _ in fol if mi)}
        g.spur(w, "gate", werkzeug="folien_pruefen",
               dateien=[d.name for d in dateien], befunde=len(befunde),
               nach_regel=nach_regel, details=details, ausloeser=a.ausloeser)

    if not a.still:
        print(f"{len(dateien)} Decks, {len(befunde)} Befunde")
        for x in befunde[:20]:
            print(f"  {x['regel']}  {x['ort']}  {x['text'][:90]}")
    raise SystemExit(1 if befunde else 0)


if __name__ == "__main__":
    main()
