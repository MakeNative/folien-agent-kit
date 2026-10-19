#!/usr/bin/env python3
"""Baut die Sitzungsmappe eines Programmtags — den Ordner, den der Trainer
am Morgen in die Hand nimmt.

    mappe_bauen.py <sessions/TAG> [...]
    mappe_bauen.py --alle <sessions-wurzel>

Quelle ist `requisiten/manifest.json` der Session. Das Werkzeug erfindet
nichts: Was dort nicht steht, landet nicht in der Mappe. Was dort steht,
aber niemand liefern kann — Dinge, die der Trainer mitbringt, und Dinge,
die erst in der Session entstehen —, steht als Checkliste in
`01_ZUERST-LESEN.md`. Dieser Teil ist der eigentliche Zweck der Anleitung:
Eine Mappe, die verschweigt, was fehlt, ist schlimmer als keine.

**Der Zielordner wird bei jedem Lauf gelöscht und neu angelegt.** Damit gibt
es keinen Zwischenzustand, den jemand von Hand repariert, und keinen Zweifel,
ob der Inhalt aktuell ist (Festlegung 3 des Plans vom 19.10.2026).

Die acht Unterordner folgen den Requisiten-Arten des Manifests. 05, 07 und 08
sind nicht erfunden — die Decks nennen sie bereits.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import zipfile
from datetime import date
from pathlib import Path

# Zielordner nach ART. Nur zwei Arten nennen ueberhaupt eine Datei; wo
# die Datei liegt, entscheidet NACH_PFAD und schlaegt diese Zuordnung.
# (Bis 19.10.2026 standen hier zusaetzlich kanal/planb/uebergabe — Arten,
# die es in keinem Manifest gibt. Toter Code, der Absicht vortaeuschte.)
ORDNER = {
    "datei": "05_Mappe",
    "druck": "04_Drucken",
}
# Welcher Unterordner der Requisiten in welchen Mappen-Ordner gehoert.
NACH_PFAD = {
    "laeufe": "07_PlanB",
    "uebergabe": "06_Uebergabe",
    "mappe": "05_Mappe",
    "befunde": "07_PlanB",
}


def _quelle_ordner(datei: str) -> str:
    """Der erste Pfadteil eines Manifest-Eintrags, oder '' bei einer Datei
    direkt in requisiten/."""
    roh = datei.replace("\\", "/").lstrip("./")
    # "laeufe/" ist ein Ordner, kein Dateiname — der abschliessende Slash
    # darf nicht dazu fuehren, dass der Eintrag im Fallback landet.
    ordner_form = roh.endswith("/")
    teile = [x for x in roh.split("/") if x]
    if ordner_form:
        return teile[0] if teile else ""
    return teile[0] if len(teile) > 1 else ""


ALLE_ORDNER = ["02_Deck", "03_Kanal", "04_Drucken", "05_Mappe",
               "06_Uebergabe", "07_PlanB", "08_Vorfuehrprojekt"]

ERZEUGT = ("<!-- ERZEUGT am {d} von tools/mappe_bauen.py — Änderungen hier "
           "gehen beim nächsten Bau verloren.\n     Quelle: {q} -->\n\n")


def laden(sess: Path) -> dict:
    p = sess / "requisiten" / "manifest.json"
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise SystemExit(f"{p}: kein gültiges JSON — {e}")


MUELL = shutil.ignore_patterns(".DS_Store", "__pycache__", ".git",
                               "Thumbs.db", "*.pyc")


def kopiere(quelle: Path, zielordner: Path) -> bool:
    """Kopiert Datei oder Ordner in die Mappe. Betriebssystem-Muell bleibt
    draussen — er landete sonst im ZIP und im Ordner des Trainers."""
    if not quelle.exists() or quelle.name in (".DS_Store", "__pycache__"):
        return False
    zielordner.mkdir(parents=True, exist_ok=True)
    if quelle.is_dir():
        shutil.copytree(quelle, zielordner / quelle.name,
                        dirs_exist_ok=True, ignore=MUELL)
    else:
        shutil.copy2(quelle, zielordner / quelle.name)
    return True


def vorfuehrprojekt(repo: str, tag: str, ziel: Path) -> str:
    """Klont den Stand, den das Manifest nennt. Fehlschlag ist kein Abbruch —
    die Mappe ist auch ohne das Projekt brauchbar, der Trainer muss es nur
    wissen. Deshalb kommt der Grund in die Anleitung."""
    ziel.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(
        ["git", "clone", "--quiet", "--depth", "1", "--branch", tag, repo,
         str(ziel / "vorfuehrprojekt")],
        capture_output=True, text=True)
    if r.returncode == 0:
        shutil.rmtree(ziel / "vorfuehrprojekt" / ".git", ignore_errors=True)
        return ""
    return (r.stderr.strip().splitlines() or ["unbekannter Fehler"])[-1][:160]


def _zeile(e: dict, zusatz: str) -> str:
    """Ein Checklisten-Posten. Ohne Foliennummer (Tage ohne Deck) entfaellt
    das Praefix, statt ein leeres „Folie None" zu drucken."""
    f = e.get("folie")
    kopf = f"Folie {f}: " if f else ""
    return f"- {kopf}{e.get('braucht', '?')}{zusatz}"


def anleitung(sess: Path, daten: dict, gelegt: list[str],
              fehlt: list[dict], klon_fehler: str) -> str:
    tag = sess.name
    z = [ERZEUGT.format(d=date.today().isoformat(),
                        q=f"sessions/{tag}/requisiten/manifest.json"),
         f"# {tag} — zuerst lesen\n"]

    blatt = sess / "TAGESBLATT.md"
    if blatt.exists():
        zeilen = blatt.read_text(encoding="utf-8").splitlines()
        titel = next((l[2:] for l in zeilen[:3] if l.startswith("# ")), "")
        kopf = [l for l in zeilen[:14]
                if l.startswith(("Board-Zeit:", "Plan-Zeit:", "Art:",
                                 "Teilnehmer:", "Modul:", "Deck:"))]
        if titel:
            z[-1] = f"# {titel}\n"
        z.append("\n".join(kopf) + "\n")

    z.append("## Was in diesem Ordner liegt\n")
    for o in ALLE_ORDNER:
        if o in gelegt:
            z.append(f"- `{o}/`")
    z.append("\nDer vollständige Ablauf mit Minuten steht in `TAGESBLATT.md`.\n")

    if fehlt:
        z.append("## Was NICHT in diesem Ordner liegt\n")
        z.append("Diese Posten kann kein Werkzeug packen. Ohne sie fällt die "
                 "jeweils genannte Folie.\n")
        trainer = [e for e in fehlt if e.get("art") == "trainer"]
        session = [e for e in fehlt if e.get("art") == "session"]
        druck = [e for e in fehlt if e.get("art") == "druck"]
        sonst = [e for e in fehlt
                 if e.get("art") not in ("trainer", "session", "druck")]
        if trainer:
            z.append("\n**Bringt der Trainer mit oder bereitet er vor:**\n")
            for e in sorted(trainer, key=lambda x: x.get("folie") or 0):
                h = f" — {e['hinweis']}" if e.get("hinweis") else ""
                z.append(_zeile(e, h))
        if druck:
            z.append("\n**Muss gedruckt oder beschafft werden:**\n")
            for e in sorted(druck, key=lambda x: x.get("folie") or 0):
                h = f" — {e['hinweis']}" if e.get("hinweis") else ""
                z.append(_zeile(e, h))
        if session:
            z.append("\n**Entsteht erst in der Session:**\n")
            for e in sorted(session, key=lambda x: x.get("folie") or 0):
                h = f" — {e['hinweis']}" if e.get("hinweis") else ""
                z.append(_zeile(e, h))
        if sonst:
            z.append("\n**Ohne Datei im Manifest — bitte pruefen:**\n")
            for e in sorted(sonst, key=lambda x: x.get("folie") or 0):
                z.append(_zeile(e, f" (art: {e.get('art','—')})"))
        z.append("")

    if klon_fehler:
        z.append("## Achtung: Vorführprojekt fehlt\n")
        z.append(f"Der Stand konnte nicht geholt werden: `{klon_fehler}`\n")
        vp = (daten.get("vorfuehrprojekt") or {})
        if vp:
            z.append(f"Von Hand: `git clone --branch {vp.get('tag','?')} "
                     f"{vp.get('repo','?')}`\n")

    if not daten:
        z.append("## Noch kein Requisiten-Manifest\n")
        z.append("Für diese Session ist noch nicht maschinenlesbar erfasst, "
                 "was sie braucht. Diese Mappe enthält deshalb nur, was ohne "
                 "Manifest auffindbar ist. Was wirklich gebraucht wird, steht "
                 "in `TAGESBLATT.md` unter Requisiten.\n")
    return "\n".join(z) + "\n"


def lies_mich(sess: Path) -> None:
    """Die Wegweiser-Datei fuer den EDITOR — nicht fuer den Trainer.

    Sie beantwortet die drei Fragen, an denen man sonst suchen muss: Wo
    aendere ich den Folientext, wo ein Bild, womit baue ich neu. Sie wird
    wie jedes Erzeugnis bei jedem Lauf ueberschrieben.
    """
    tag = sess.name
    decks = sorted(f.name for f in sess.glob(f"{tag}*-*.md"))
    paper = sorted(f.name for f in sess.glob("P-*.md"))
    modul = sorted(f.name for f in sess.glob("M*.md"))
    z = [ERZEUGT.format(d=date.today().isoformat(),
                        q="tools/mappe_bauen.py"),
         f"# {tag} — was liegt hier, und was aendere ich wo\n",
         "## Ich will den Text einer Folie aendern\n"]
    z += [f"- `{d}` — das Deck. Folientext und Sprechnotizen stehen hier, "
          f"sonst nirgends." for d in decks] or ["- Diese Session hat kein Deck.\n"]
    # Nur nennen, was es hier wirklich gibt — ein Wegweiser, der auf
    # fehlende Dateien zeigt, schickt den Editor ins Leere (19.10.2026).
    if (sess / "assets").is_dir():
        z.append("\n## Ich will ein Bild aendern\n")
        z.append("- `assets/` — die fertigen PNG. Nie von Hand bearbeiten.")
        if (sess / "assets" / "quellen").is_dir():
            z.append("- `assets/quellen/compositions/` — die HTML-Quelle je "
                     "Bild. Dort aendern, dann neu rendern.")
        if (sess / "assets" / "FREIGABE.md").exists():
            z.append("- `assets/FREIGABE.md` — ohne Zeile dort legt der "
                     "Builder das Bild nicht auf die Folie.")
        z.append("")
    z.append("## Ich will aendern, was der Trainer in die Hand bekommt\n")
    if (sess / "requisiten" / "manifest.json").exists():
        z.append("- `requisiten/manifest.json` — die Liste. Jeder Eintrag "
                 "nennt Folie, Art und (wenn es eine gibt) die Datei.")
    else:
        z.append("- **Diese Session hat noch kein `requisiten/manifest.json`.** "
                 "Was sie braucht, steht als Prosa in den `TUN:`-Bloecken des "
                 "Decks und unter „Requisiten\" im Tagesblatt — der "
                 "Mappen-Bauer kann es deshalb nicht packen.")
    if (sess / "requisiten").is_dir():
        z.append("- `requisiten/` — das Material selbst.")
    z.append("")
    if paper or modul:
        z.append("## Weitere Quellen dieser Session\n")
        z += [f"- `{m}` — das Handout-Modul" for m in modul]
        z += [f"- `{p_}` — das Short Paper" for p_ in paper]
        z.append("")
    z.append("## Ich will alles neu bauen\n")
    z.append("```\ncd praesentationen\n./bau " + tag + "\n```\n")
    # Nicht versprechen, was diese Session gar nicht hat.
    teile = []
    if decks:
        teile.append("Deck und PDF mit Notizenseiten")
    if paper:
        teile.append("Short Paper")
    teile.append("die Sitzungsmappe")
    z.append("Das baut " + ", ".join(teile[:-1]) +
             (" und " if len(teile) > 1 else "") + teile[-1] +
             " in einem Zug.\n")
    z.append("## Finger weg\n")
    z.append("- `FUER-DEN-TRAINER/` — wird bei **jedem** Bau geloescht und "
             "neu erzeugt. Aenderungen dort sind nach dem naechsten Lauf weg.")
    (sess / "LIES-MICH.md").write_text("\n".join(z) + "\n", encoding="utf-8")


def baue(sess: Path) -> tuple[str, int, int]:
    tag = sess.name
    daten = laden(sess)
    ziel_wurzel = sess / "FUER-DEN-TRAINER"
    mappe = ziel_wurzel / f"Sitzungsmappe-{tag}"

    # Wegwerfen statt pflegen: kein Zwischenzustand, keine Altlast.
    if ziel_wurzel.exists():
        shutil.rmtree(ziel_wurzel)
    mappe.mkdir(parents=True)

    gelegt: list[str] = []
    gepackt = 0

    # Tagesblatt immer obenauf — es trägt den Ablauf.
    if (sess / "TAGESBLATT.md").exists():
        shutil.copy2(sess / "TAGESBLATT.md", mappe / "TAGESBLATT.md")

    # 02_Deck: die gebauten Artefakte dieser Session
    for muster in ("*.pptx", "*.pdf"):
        for f in sorted(sess.glob(muster)):
            if kopiere(f, mappe / "02_Deck"):
                gepackt += 1
                if "02_Deck" not in gelegt:
                    gelegt.append("02_Deck")

    # Requisiten nach Art verteilen
    fehlt: list[dict] = []
    wurzel = sess / "requisiten"
    eintraege = daten.get("requisiten") or []

    # Nennt das Manifest einen ganzen Ordner (laeufe/), dann decken dessen
    # Dateien alle Einzeleintraege darunter ab. Ohne diese Vorfilterung lag
    # lauf-3-mit-mappe.md zweimal in der Mappe (gefunden 19.10.2026).
    ordner_eintraege = {e["datei"].rstrip("/") for e in eintraege
                        if e.get("datei", "").endswith("/")}
    gesehen: set[str] = set()

    for e in eintraege:
        art = e.get("art")
        datei = e.get("datei")
        # Alles, was keine Datei nennt, kann kein Werkzeug packen — es
        # gehoert in die Checkliste, nicht ins Nichts. Vor dem 19.10.2026
        # fielen die druck-Posten hier lautlos heraus.
        if art in ("trainer", "session") or not datei:
            fehlt.append(e)
            continue
        norm = datei.rstrip("/")
        if norm in gesehen:
            continue                      # derselbe Pfad zweimal im Manifest
        if "/" in norm and norm.split("/")[0] in ordner_eintraege:
            continue                      # steckt schon im Ordner-Eintrag
        gesehen.add(norm)
        q = (wurzel / datei).resolve()
        if art == "asset":
            continue                      # steckt schon im Deck
        # Der Zielordner folgt dem PFAD, nicht nur der Art: ein Eintrag
        # art=datei kann auf laeufe/, uebergabe/ oder mappe/ zeigen. Vorher
        # landete alles davon in 05_Mappe und wurde danach ein zweites Mal
        # am richtigen Ort abgelegt — 05_Mappe war ein Sammelbecken mit
        # Doppelungen (gefunden 19.10.2026).
        ordner = NACH_PFAD.get(_quelle_ordner(datei), ORDNER.get(art, "05_Mappe"))
        if q.name.startswith("handout-"):
            ordner = "03_Kanal"
        if kopiere(q, mappe / ordner):
            gepackt += 1
            if ordner not in gelegt:
                gelegt.append(ordner)

    # Ordner, die als Ganzes mitgehen, auch ohne Einzeleintrag
    for name, ordner in (("laeufe", "07_PlanB"), ("uebergabe", "06_Uebergabe"),
                         ("mappe", "05_Mappe")):
        q = wurzel / name
        if name in ordner_eintraege or any(
                d.startswith(name + "/") for d in gesehen):
            continue                      # das Manifest hat ihn schon
        if q.is_dir() and not (mappe / ordner).exists():
            (mappe / ordner).mkdir(parents=True, exist_ok=True)
            for f in sorted(q.iterdir()):
                kopiere(f, mappe / ordner)
                gepackt += 1
            if ordner not in gelegt:
                gelegt.append(ordner)

    # Handouts und Module in den Kanal-Ordner
    for f in sorted(list(sess.glob("P-*.md")) + list(sess.glob("M*.md"))):
        if kopiere(f, mappe / "03_Kanal"):
            gepackt += 1
            if "03_Kanal" not in gelegt:
                gelegt.append("03_Kanal")
    for f in sorted(wurzel.glob("handout-*.pdf")):
        if kopiere(f, mappe / "03_Kanal"):
            gepackt += 1

    # Vorführprojekt auf dem Stand, den das Manifest nennt
    klon_fehler = ""
    vp = daten.get("vorfuehrprojekt") or {}
    if vp.get("repo") and vp.get("tag"):
        klon_fehler = vorfuehrprojekt(vp["repo"], vp["tag"],
                                      mappe / "08_Vorfuehrprojekt")
        if not klon_fehler:
            gelegt.append("08_Vorfuehrprojekt")
            gepackt += 1

    (mappe / "01_ZUERST-LESEN.md").write_text(
        anleitung(sess, daten, gelegt, fehlt, klon_fehler), encoding="utf-8")
    lies_mich(sess)

    # ZIP daneben, damit der Trainer eine Datei zieht statt eines Baums
    zpfad = ziel_wurzel / f"Sitzungsmappe-{tag}.zip"
    with zipfile.ZipFile(zpfad, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(mappe.rglob("*")):
            if p.is_file():
                z.write(p, p.relative_to(ziel_wurzel))
    return tag, gepackt, len(fehlt)


def main() -> None:
    args = [a for a in sys.argv[1:] if a != "--alle"]
    if "--alle" in sys.argv:
        wurzel = Path(args[0] if args else "sessions")
        ziele = sorted(p for p in wurzel.iterdir() if p.is_dir())
    else:
        ziele = [Path(a) for a in args]
    if not ziele:
        raise SystemExit(__doc__)
    ohne = 0
    for s in ziele:
        if not s.is_dir():
            print(f"  ! {s}: kein Ordner")
            continue
        tag, n, f = baue(s)
        kein = "" if (s / "requisiten" / "manifest.json").exists() else "  (kein Manifest)"
        ohne += 0 if kein == "" else 1
        print(f"  {tag:<6} {n:>3} Posten gepackt, {f} nur als Checkliste{kein}")
    if ohne:
        print(f"\n{ohne} Session(en) ohne Manifest — die Mappe trägt dort nur, "
              f"was ohne Manifest auffindbar ist.")


if __name__ == "__main__":
    main()
