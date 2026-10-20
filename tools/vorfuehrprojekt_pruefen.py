#!/usr/bin/env python3
"""Prueft das Vorfuehrprojekt gegen das, was die Folien von ihm behaupten.

    vorfuehrprojekt_pruefen.py [projekt] [praesentationen]

Das Vorfuehrprojekt ist der Rueckfall jeder Demo. Weicht es von den
Bildern ab, merkt das niemand beim Bauen — sondern der Trainer in der
Session, wenn die Abbruchlinie schon gerissen ist.

Geprueft wird nur, was eine Folie sichtbar behauptet:
  - jeder im Fiktiv-Register genannte Projektpfad existiert
  - deliveryRetryPolicy.ts existiert NICHT (Pruefstein von S2 F2)
  - orderNotifier.ts hat genau die Zeilenzahl aus dem Dateikopf des Bildes
  - die im Bild gezeigten Zeilen stehen zeichengenau an ihrer Nummer
  - retryDelayMinutes steht auf dem Ausgangswert, nicht auf dem Zielwert
  - die Proben laufen und genau die eine ist offen
  - die zweite Domaene hat CLAUDE.md, einen @-Import und eine Regeldatei
    in einem Unterordner (T17 F11)
  - der Schutz-Hook ist eingetragen (T4 F16)
"""
from __future__ import annotations

import json
import re
import subprocess
import tempfile
import sys
from pathlib import Path

VERBOTEN = "src/services/deliveryRetryPolicy.ts"
AUSGANGSWERT = 5          # Betriebshandbuch 4.3 verlangt 15 — das ist die Demo
ZWEITE_DOMAENE = "zustell-doku"


def registerpfade(register: Path) -> set[str]:
    roh = re.findall(r"\b(?:src|protokolle|bin|werkzeug|berichte|wegwerf)/[\w./-]+",
                     register.read_text(encoding="utf-8"))
    # Satzzeichen am Ende gehoeren zum Text, nicht zum Pfad
    return {p.rstrip(".,;:") for p in roh if "/" in p.rstrip(".,;:")}


def bildzeilen(plan: Path) -> tuple[int | None, dict[int, str]]:
    """Zeilenzahl aus dem Dateikopf und die nummerierten Zeilen des Bildes."""
    if not plan.exists():
        return None, {}
    t = plan.read_text(encoding="utf-8")
    m = re.search(r"orderNotifier\.ts — (\d+) Zeilen", t)
    gesamt = int(m.group(1)) if m else None
    zeilen: dict[int, str] = {}
    for z in t.splitlines():
        m = re.match(r"^(\d{2,4})(\s.*)$", z)
        if m and 100 <= int(m.group(1)) <= 999:
            zeilen[int(m.group(1))] = m.group(2)
    return gesamt, zeilen


def main() -> int:
    projekt = Path(sys.argv[1] if len(sys.argv) > 1
                   else Path.home() / "StudioProjects/vorfuehrprojekt")
    praes = Path(sys.argv[2] if len(sys.argv) > 2
                 else Path.home() / "Documents/agentic-coding-guide/praesentationen")
    befunde: list[str] = []
    geprueft = 0

    if not projekt.is_dir():
        print(f"  ! kein Projekt unter {projekt}")
        return 2

    # 1 Registerpfade
    register = praes / "pptx" / "assets" / "FIKTIV-REGISTER.md"
    if register.exists():
        for p in sorted(registerpfade(register)):
            geprueft += 1
            if p != VERBOTEN and not (projekt / p).exists():
                befunde.append(f"Register nennt {p}, im Projekt fehlt es")

    # 2 Pruefstein
    geprueft += 1
    if (projekt / VERBOTEN).exists():
        befunde.append(f"{VERBOTEN} existiert — damit verliert S2 F2 "
                       f"seinen Beweis")

    # 3+4 Zeilenzahl und Bildzeilen
    quelle = projekt / "src" / "services" / "orderNotifier.ts"
    gesamt, zeilen = bildzeilen(praes / "sessions" / "S2" / "assets" / "ASSET-PLAN.md")
    if quelle.exists() and gesamt:
        ist = quelle.read_text(encoding="utf-8").splitlines()
        geprueft += 1
        if len(ist) != gesamt:
            befunde.append(f"orderNotifier.ts hat {len(ist)} Zeilen, das Bild "
                           f"nennt {gesamt}")
        for nr, text in sorted(zeilen.items()):
            geprueft += 1
            if nr > len(ist):
                befunde.append(f"Bild zeigt Zeile {nr}, Datei endet bei {len(ist)}")
            elif ist[nr - 1] != text:
                befunde.append(f"Zeile {nr} weicht vom Bild ab\n"
                               f"        ist : {ist[nr-1]!r}\n"
                               f"        Bild: {text!r}")

    # 5 Ausgangswert
    if quelle.exists():
        geprueft += 1
        m = re.search(r"const retryDelayMinutes = (\d+);",
                      quelle.read_text(encoding="utf-8"))
        if not m:
            befunde.append("retryDelayMinutes steht nicht im Nachtlauf")
        elif int(m.group(1)) != AUSGANGSWERT:
            befunde.append(f"retryDelayMinutes steht auf {m.group(1)}, der "
                           f"Ausgangsstand ist {AUSGANGSWERT} — sonst hat "
                           f"T0 F11 nichts zu zeigen")

    # 6 Proben
    pruefbefehl = projekt / "bin" / "test"
    if pruefbefehl.exists():
        geprueft += 1
        r = subprocess.run([str(pruefbefehl)], cwd=projekt,
                           capture_output=True, text=True, timeout=180)
        offen = re.search(r"(\d+) Probe\(n\) offen", r.stdout)
        if not offen:
            befunde.append("bin/test meldet keine Probenbilanz")
        elif offen.group(1) != "1":
            befunde.append(f"{offen.group(1)} Proben offen, erwartet ist "
                           f"genau 1 (die, die T0 F11 gruen macht)")

    # 6b Demo-Zweige: fremdes Rot darf nicht als Diff-Fund durchgehen
    #
    # Lehre vom 20.10.: Auf vorlauf/adresspruefung meldet bin/test ZWEI
    # Fehlschlaege — den gesetzten Korrektheitsfund des Diffs und den
    # absichtlichen TS-4871 von main. In der Pruef-Demo (T7 F12) sieht der
    # Teilnehmer zwei rote Zeilen und schreibt beide dem Diff zu. Gemessen
    # wird deshalb die DIFFERENZ zu main; zusaetzlich wird gemeldet, wenn
    # fremdes Rot mitlaeuft, denn dann muss das Requisit es benennen.
    ZWEIGE = {"vorlauf/adresspruefung": 1, "vorlauf/queue-uebersicht": 0}

    def offene_proben(wurzel):
        """Zahl der offenen Proben, oder None wenn bin/test nichts meldet."""
        r = subprocess.run([str(Path(wurzel) / "bin" / "test")], cwd=wurzel,
                           capture_output=True, text=True, timeout=180)
        m = re.search(r"(\d+) Probe\(n\) offen", r.stdout)
        return int(m.group(1)) if m else None

    if pruefbefehl.exists() and (projekt / ".git").exists():
        haupt = offene_proben(projekt)
        for zweig, soll in ZWEIGE.items():
            geprueft += 1
            with tempfile.TemporaryDirectory() as tmp:
                klon = Path(tmp) / "k"
                if subprocess.run(["git", "clone", "--no-hardlinks", "-q",
                                   str(projekt), str(klon)],
                                  capture_output=True).returncode != 0:
                    befunde.append(f"Zweig {zweig}: Klon fehlgeschlagen, "
                                   f"nicht geprueft")
                    continue
                if subprocess.run(["git", "checkout", "-q", zweig], cwd=klon,
                                  capture_output=True).returncode != 0:
                    befunde.append(f"Zweig {zweig} fehlt — T7 F12 braucht ihn")
                    continue
                ist = offene_proben(klon)
            if ist is None or haupt is None:
                befunde.append(f"Zweig {zweig}: bin/test meldet keine "
                               f"Probenbilanz")
                continue
            if ist - haupt != soll:
                befunde.append(
                    f"Zweig {zweig}: {ist - haupt} Fehlschlag(e) mehr als "
                    f"main, erwartet {soll} — der Diff traegt nicht die "
                    f"gesetzten Funde")
            elif ist > soll:
                befunde.append(
                    f"Zweig {zweig}: der Diff setzt {soll} Fehlschlag(e), "
                    f"bin/test zeigt aber {ist} — {ist - soll} davon kommt "
                    f"aus main (TS-4871) und gehoert nicht zum Diff. Das "
                    f"Requisit muss sagen, welche rote Zeile gemeint ist")

    # 6c Was die Verhaltens-Proben vom 20.10. am Aufbau gefunden haben
    hook = projekt / "werkzeug" / "pruefe-schreibziel.ts"
    geprueft += 1
    if hook.exists():
        h = hook.read_text(encoding="utf-8")
        if "**/*" not in h:
            befunde.append("der Schutz-Hook traegt das Muster \"**/*\" nicht "
                           "mehr — T4 F16 braucht den zu breiten Hook")
        # Die Meldung muss sagen, WELCHES Muster traf. Vorher nannte sie
        # immer berichte/, auch wenn "**/*" gegriffen hatte — und verdeckte
        # damit genau den Punkt, den T4 F16 zeigen will.
        if "Dateien unter berichte/ werden nicht" in h:
            befunde.append("der Schutz-Hook meldet immer \"berichte/\", auch "
                           "wenn \"**/*\" traf — die Meldung muss das "
                           "Muster nennen (Probe vom 20.10.)")

    btest = projekt / "bin" / "test"
    geprueft += 1
    if btest.exists():
        b = btest.read_text(encoding="utf-8")
        # Eine Probendatei deckt drei Quelldateien ab. Die Namenskonvention
        # test/<basename>.test.ts fand deshalb nur fuer orderNotifier.ts
        # etwas und meldete sonst "Could not find" — eine ungepruefte Datei
        # sah gruen aus. T0 F11 und der aufgaben-schneider verlassen sich
        # darauf.
        if "keine Probe deckt" not in b:
            befunde.append("bin/test sagt nicht, wenn keine Probe eine "
                           "Quelldatei abdeckt — T0 F11 verlaesst sich "
                           "darauf (Probe vom 20.10.)")

    claudemd = projekt / "CLAUDE.md"
    geprueft += 1
    if claudemd.exists():
        c = " ".join(claudemd.read_text(encoding="utf-8").split())
        if "T1 Folie 14" not in c or "T3 Folie 14" not in c:
            befunde.append("CLAUDE.md nennt die Plan-Modus-Demos nicht, vor "
                           "denen der Hook aus muss (T1 F14, T3 F14) — im "
                           "Plan-Modus wird die Plandatei geschrieben")

    # 7 zweite Domaene
    zd = projekt / ZWEITE_DOMAENE
    geprueft += 1
    if not (zd / "CLAUDE.md").exists():
        befunde.append(f"{ZWEITE_DOMAENE}/CLAUDE.md fehlt — T17 F11 braucht "
                       f"eine zweite Domaene")
    else:
        if "@" not in zd.joinpath("CLAUDE.md").read_text(encoding="utf-8"):
            befunde.append(f"{ZWEITE_DOMAENE}/CLAUDE.md bindet nichts per "
                           f"@pfad ein — dann zeigt /context nichts")
        unter = [p for p in zd.rglob("CLAUDE.md") if p.parent != zd]
        if not unter:
            befunde.append(f"{ZWEITE_DOMAENE}: keine Regeldatei in einem "
                           f"Unterordner — die Pointe von T17 F12 fehlt")

    # 7b Abdeckung der projektabhaengigen Bedarfe
    #     Je Bedarf eine Datei oder Marke, die beweist, dass das Projekt
    #     ihn traegt. Ohne diese Tabelle laesst sich "das Projekt ist
    #     fertig" nur behaupten, nicht messen.
    ABDECKUNG = {
        ("S2-kontext", 7): "protokolle/zustellung.log",
        ("S2-kontext", 8): "protokolle/zustellung.log",
        ("S2-kontext", 14): "protokolle/zustellung.log",
        ("S3-datenzugriff", 15): "werkzeug/ticketspur-server.ts",
        ("T0-grundlagen", 4): "VERSIONEN.md",
        ("T0-grundlagen", 5): "src/services/orderNotifier.ts",
        ("T0-grundlagen", 11): "bin/test",
        ("T1-kickoff", 9): "src/services/queueOverview.ts",
        ("T1-kickoff", 14): "src/services/orderNotifier.ts",
        ("T1-kickoff", 18): "vorgaenge/offen.md",
        ("T12-parallel", 11): "laeufe/deliveryQuota-endzustand.ts",
        ("T12-parallel", 24): "werkzeug/pruefe-zieldatei.ts",
        ("T13-autonomie", 12): "protokolle/lauf-verweigert.log",
        ("T13-autonomie", 16): "werkzeug/pruefe-schreibziel.ts",
        ("T13-autonomie", 24): "protokolle/laufliste.txt",
        ("T13-autonomie", 27): "werkzeug/mod-guard/plugin.json",
        ("T17-system", 11): "zustell-doku/CLAUDE.md",
        ("T17b-remote", 6): "laeufe/remote-uebersicht.txt",
        ("T20-abschluss", 13): "abnahmen/notizen.md",
        ("T3-anatomie", 10): "werkzeug/pruefe-schreibziel.ts",
        ("T3-anatomie", 14): "src/services/orderNotifier.ts",
        ("T3-anatomie", 16): "src/services/queueOverview.ts",
        ("T3-anatomie", 1): "laeufe/erosion-transkript.md",
        ("S3-datenzugriff", 23): "handzettel/einrichtung-ticketspur.md",
        ("T4-pipelines", 16): "berichte/wegwerf.txt",
        ("T7-evaluieren", 7): "laeufe/lauf-a-bericht.md",
        ("T7-evaluieren", 12): "src/services/addressCheck.ts",
    }
    offen = []
    for (deck, nr), pfad in sorted(ABDECKUNG.items()):
        geprueft += 1
        if not (projekt / pfad).exists():
            offen.append(f"{deck} F{nr}: {pfad} fehlt")
    befunde += offen

    # 7c Die zwei vorbereiteten Diffs (T3 F16, T7 F12) liegen als Zweig
    geprueft += 1
    r = subprocess.run(["git", "-C", str(projekt), "branch", "--format=%(refname:short)"],
                       capture_output=True, text=True)
    zweige = set(r.stdout.split())
    for z in ("vorlauf/queue-uebersicht", "vorlauf/adresspruefung"):
        if z not in zweige:
            befunde.append(f"Zweig {z} fehlt — ohne ihn gibt es keinen "
                           f"Aenderungsvergleich zum Pruefen")

    # 8 Schutz-Hook
    s = projekt / ".claude" / "settings.json"
    geprueft += 1
    if not s.exists():
        befunde.append(".claude/settings.json fehlt — T4 F16 verlangt den "
                       "fertigen Eintrag")
    else:
        try:
            d = json.loads(s.read_text(encoding="utf-8"))
            if not d.get("hooks", {}).get("PreToolUse"):
                befunde.append("kein PreToolUse-Hook in settings.json")
        except json.JSONDecodeError as e:
            befunde.append(f"settings.json ist kein gueltiges JSON — {e}")

    print(f"{geprueft} Pruefungen, {len(befunde)} Befund(e)")
    for b in befunde:
        print("  ! " + b)
    return 1 if befunde else 0


if __name__ == "__main__":
    sys.exit(main())
