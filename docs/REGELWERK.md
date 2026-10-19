# Regelwerk folien-kit

Gilt für alle Decks unter `praesentationen/sessions/<TAG>/` eines Dokumentprojekts.
Die F-Regeln prüft `tools/folien_pruefen.py` maschinell; F-04 blockiert
zusätzlich der PreToolUse-Hook `guard-leinwand` beim Schreiben.

## Leinwand-Regeln (maschinell, F)

- **F-01** Folienbudget: Kopfzeile `Budget: <n> Folien`; mehr Folien als n
  sind ein Befund. Richtwerte: Briefing ≤ 12, Workshop-Input ≤ 8,
  Session-Rahmen ≤ 6, Abschluss ≤ 10 — das konkrete n setzt die Spezifikation.
- **F-02** ≤ 25 sichtbare Wörter je Folie. Nicht sichtbar (zählt nicht):
  Sprechnotiz:, Demo:, Jetzt du:, Handout:, Form:, Skizze:, Codezäune,
  Folientitel.
- **F-03** Ein Gedanke je Folie: höchstens ein zusammenhängender Bullet-Block.
- **F-04** Keine Fußnoten auf der Leinwand. Belege laufen über die
  Handout:-Zeile (Modul + Folie/Abschnitt); der Hook blockiert Verstöße.
- **F-05** Beispiel vor Regel: eine Regel:-Zeile verlangt eine
  Beispiel:-Zeile davor auf derselben Folie.
- **F-06** Leinwandzeit: Kopfzeile `Leinwandzeit: <n> min`; die Summe der
  `(~n min)`-Angaben darf sie nicht reißen. Richtwert: ≤ 25–30 min je
  90-Minuten-Session — der Rest ist Arbeit der Teilnehmer.

- **F-07** Abdeckung: jede `MUSS:`-Zeile der zugehörigen
  SPEZIFIKATION-<name>.md muss als Schlagwort im Deck vorkommen oder in der
  Spezifikation als `GESTRICHEN (<grund>)` begründet sein.

## Darstellungs-Regeln (geprüft von Agenten, D)

- **D-01** Jede Folie trägt `**Form:** <Typ>` aus dem Vokabular (Kernsatz ·
  Schaubild · Vergleich · Beleg-Folie · Zahl · Live-Demo · Jetzt du · Kasten ·
  Quellen); Schaubilder zusätzlich `**Skizze:** <ein Satz>`.
- **D-02** Jede Zahl auf der Leinwand trägt ihre Herkunft als Unterzeile:
  gemessen (wo) oder Programmziel. Zahlen ohne Herkunft sind verboten.
- **D-03** Jede Jetzt-du-Folie nennt Auftrag, Minuten und Fertig-Kriterium.
- **D-04** Spätestens jede dritte Folie ist aktiv (Demo oder Jetzt du);
  bewusste Ausnahmen stehen als ⚠-Zeile im Dramaturgie-Block.

## Short-Paper-Regeln (maschinell, SP)

Das Paper ist die dritte Schicht: Leinwand (Deck) → **Spickzettel (Paper)**
→ Tiefe (Handout-Modul). Gate: `tools/papier_pruefen.py`.

- **SP-01** Wortbudget-Kopfzeile, Richtwert 900 Wörter Fließtext.
- **SP-02** Pflichtstruktur: Was du jetzt kannst · Die Handgriffe ·
  Wenn es klemmt · Vertiefung — in dieser Reihenfolge.
- **SP-03** Jeder Handgriff trägt Kasten, Bild, Mermaid oder Screenshot-Marke.
- **SP-04** Keine Fußnoten im Paper; Belege nur als Verweise im
  Vertiefungs-Block (die Belegkette läuft Paper → Handout → Claim).
- **SP-05** „Was du jetzt kannst" hat höchstens 3 Sätze.

## Rollen-Regeln (FP)

- **FP-01** Die Skill entscheidet, Agenten liefern. Spezifikation, Gate-Läufe
  und Fix-Entscheidungen sind Skill-Arbeit; kein Agent verwaltet Gate-Dateien.
- **FP-02** Ersteller prüfen nicht: der folien-writer sieht keinen
  Prüfbericht vor Abgabe, die Prüfer (belegkette-pruefer, trainer-leser,
  publikum-entwickler) haben keine Schreibrechte.
- **FP-03** Das Publikum ist Messinstrument und bleibt memoryfrei; ein
  Publikum, das sich erinnert, misst nicht mehr. Writer und trainer-leser
  dürfen Handwerk im Memory halten (nur aus dem Protokoll Belegtes).
- **FP-04** Die Belegkette läuft Leinwand → Handout → Claim. Das Handout
  (die Module unter praesentationen/module/) ist die einzige Inhaltsquelle
  des Writers; neue Inhalte entstehen nie im Deck.
- **FP-05** Jede Blockade und jeder Gate-Lauf landet im Laufprotokoll
  `.claude/folien-log/lauf.jsonl` — sonst ist Evaluieren blind.

## Deck-Format

```
# <Deck-Name> — <Session, Board-Titel>
Budget: <n> Folien
Leinwandzeit: <n> min
Handout: praesentationen/module/<modul>.md

## Dramaturgie
<4–6 Zeilen: Hook, Problem-vor-Lösung, Aktiv-Rhythmus, Peak, Abschluss-Check>

## Folie 1: <Titel> (~n min)
**Form:** <Typ>
Beispiel: <der konkrete Fall zuerst>
Regel: <eine Zeile>
Sprechnotiz: <Trainer-Stimme, zählt nicht>
Handout: <Modul, Folie/Abschnitt>
```

## Asset-Regeln (AS) — Bild-, Clip- und Foto-Erzeugung für Decks

- **AS-01 · Plan vor Erzeugung.** Kein Asset ohne Block im
  `ASSET-PLAN.md` des Decks (`praesentationen/sessions/<TAG>/assets/`).
  Der Plan legt je Marke Route, Datei, Maße und den **zeichengenauen
  Bildtext** fest — der Generator erfindet keinen Text.
- **AS-02 · Routen.** `mock` (gebaute UI/Terminal-Mocks, HyperFrames —
  Pflicht, sobald Text im Bild tragend ist), `foto` (generative Bilder,
  Higgsfield — Stimmung, Räume, Menschen ohne Pflichttext), `clip`
  (Motion ≤ 30 s, HyperFrames motion-graphics), `offen` (nur ein echter
  System-Screenshot kann es liefern — bleibt Platzhalter mit Eigentümer
  und Stichtag). Generierte Fotos mit tragendem Text sind verboten;
  Ausnahme nur mit Validator-Freigabe Wort für Wort.
- **AS-03 · Nur Fiktives.** Keine echten Produktnamen, Logos, Personen,
  Firmen- oder Kundendaten in erzeugten Assets. Eigennamen kommen aus
  `praesentationen/pptx/assets/FIKTIV-REGISTER.md` und werden dort
  geführt — ein Name, überall dieselbe Schreibweise.
- **AS-04 · Ledger-Pflicht.** Jede erzeugte Datei hat einen Eintrag in
  `LEDGER.md` (Datei, Route, Werkzeug/Projektpfad oder Job, Prompt bzw.
  Quelle, Datum). Ohne Ledger gilt das Asset als nicht erzeugt.
- **AS-05 · Ersteller ≠ Prüfer, eine Freigabe-Wahrheit.** Freigaben
  stehen AUSSCHLIESSLICH in `FREIGABE.md` und kommen nur vom
  asset-validator (Bildtext Wort für Wort, AS-03-Scan, Maße,
  Lesbarkeit). Der Plan kennt nur die Stati geplant/offen/erzeugt.
  Zeilenformat strikt `F<nr>.<ext> — freigegeben (Stand <Datum>, …)`
  bzw. `… — ABGELEHNT: …`; letzte Zeile je Datei gewinnt. Das
  Stand-Datum muss das Datum der letzten Ledger-Zeile sein — dadurch
  verfällt JEDE Freigabe maschinell, sobald regeneriert wird. Der
  Validator nutzt Bash nur lesend (sips/afinfo/ffprobe).
- **AS-06 · Maschinengate.** `tools/assets_pruefen.py <deck.md>` prüft
  Marken↔Plan-Deckung, Routen-/Status-Whitelist, Pflichtfelder
  (Datei, Masse, Fiktiv bei mock/clip, Clip-Feld bei clip, Eigentümer
  bei offen, leerer Text-Block bei foto), Status-Logik (erzeugt ⇒
  Datei + Ledger; jede Datei ohne Ledger ist Befund), Freigabe-
  Konsistenz samt Regenerations-Schutz und Register-Pflicht. Es läuft
  per Hook bei jedem Schreiben von Plan/Ledger/Freigabe und loggt
  jeden Lauf ins Laufprotokoll.
- **AS-07 · Eine Marke je Folie.** Eine Folie trägt höchstens eine
  Bild-/Video-Marke; der Builder legt genau ein Asset je Folie über
  die erste Fläche. Mehr Marken sind ein Deck-Fix, kein Asset-Fall.

## Tagesdetail-Regeln (TD) — Durchführungsblätter je Programmtag

- **TD-01 · Quelle oder Lücke.** Jede Angabe eines Tagesblatts
  (`praesentationen/sessions/<TAG>/TAGESBLATT.md`) trägt eine Herkunft aus dem
  Vokabular Board | Modul <id> | Deck <id> |
  Programm-Entscheidung <Datum> | LÜCKE. Was keine Quelle hat, wird
  als LÜCKE markiert und im Lücken-Abschnitt gespiegelt — nie
  plausibel gefüllt. Programm-Entscheidungen darf der Writer nur
  etikettieren, wenn der Auftrag sie ihm nennt.
- **TD-01b · Programm-Entscheidungen sind belegpflichtig.** Das
  Etikett `Programm-Entscheidung <Datum>` ist nur zulässig, wenn die
  Entscheidung in `praesentationen/PROGRAMM-ENTSCHEIDUNGEN.md` mit
  Wortlaut, Tragweite und Geltungsbereich steht. Gesprächsentscheidungen
  ohne Eintrag sind für jeden Prüfer von einer Erfindung nicht zu
  unterscheiden — sie werden zuerst eingetragen, dann zitiert. Das Gate
  prüft die Daten gegen die Datei.
- **TD-02 · Minuten-Arithmetik.** Die Ablauf-Blocksumme ist gleich der
  Plan-Zeit; weicht die Plan-Zeit von der Board-Zeit ab, trägt das
  Blatt einen Überzug-Abschnitt mit begründetem Satz. Deck-Minuten
  werden übernommen, nicht neu verteilt.
- **TD-03 · Blatt ersetzt Karte.** Das Tagesblatt trägt alle
  Stichpunkte, das Ergebnis-Feld und die Badges seiner Board-Karte
  sowie alle Requisiten aus Demo-Regie/Plan B/BILDLISTE — der Trainer
  hält den Tag ohne weitere Lektüre.
- **TD-04 · Ersteller ≠ Prüfer.** Der tagesdetail-writer schreibt, der
  board-treue-pruefer prüft Quellen-Echtheit und still gefüllte
  Lücken, der trainer-leser die Durchführbarkeit. Widersprüche
  zwischen Board und Modul/Deck sind Programm-Entscheidungen, keine
  stillen Auflösungen.
- **TD-05 · Maschinengate.** `tools/tagesdetail_pruefen.py` prüft
  Kopffelder/Whitelists/Zeitformate (TD-G1), Zeilenformat samt
  Quellen-Vokabular — jede nicht-leere Zeile eines Pflichtabschnitts
  ist Bullet oder `keine`, Prosa und Tabellen sind Befunde (TD-G2),
  Arithmetik samt Überzug-Begründung (TD-G3), beidseitige
  Lücken-Spiegelung (TD-G4) sowie Verweise aus Kopf UND Zeilen-Quellen
  und das Soll-Ist der erwarteten Tage (TD-G5). Die Befund-Kürzel
  TD-G1…TD-G5 haben einen eigenen Namensraum — die Deck-Regeln
  D-01…D-04 dieses Regelwerks bedeuten etwas anderes. Das Gate läuft
  per Hook bei jedem Schreiben eines Tagesblatts und loggt ins
  Laufprotokoll.
- **TD-06 · Board-Badge wörtlich, Art normalisiert.** Das Blatt trägt
  das Board-Badge unverändert in `Badge:` und die maschinenlesbare
  Klasse in `Art:` (Live-Session, Gruppen-Session, Workshop,
  Eigenarbeit, Check-in, Messung, GF-Report, Abschlusstermin, intern).
  Zeitfelder dürfen jede Board-Form tragen (`90 min`, `30–45 min`,
  `90 + 30 min`, `3 h`, `—`); gerechnet wird mit der Plan-Zeit, die
  eine Einzelzahl sein muss.

## Formular-Regeln (FB) — Evaluationsbögen in Notion

- **FB-01 · Spezifikation vor Bau.** Kein Bogen ohne Block in
  `praesentationen/eval/FORMULAR-SPEZ.md` (Fragetext wörtlich vom
  Board, Feldtyp, Optionen, Pflicht/optional, Zielort, interne
  Auswertungshinweise). Der formular-bauer formuliert nichts um und
  ergänzt nichts.
- **FB-02 · Schutz der Antworten.** Getrennt Spezifiziertes bleibt
  getrennt (Testimonial-Freigaben a/b/c als drei Felder); anonyme
  Bögen tragen kein Namens-, Mail- oder Personenfeld; die
  GF-Kurzvariante ist ein eigener Bogen.
- **FB-03 · Regeln unsichtbar.** Interne Auswertungsregeln
  (z. B. Score ≤ 3 → 1:1) stehen auf der internen Auswertungs-Seite,
  nie im sichtbaren Bogen.
- **FB-06 · Werkzeuggrenzen von Notion (gemessen 10.10.2026).** Views
  lassen sich anlegen, aber nicht löschen und nicht umtypen; der
  Offen/Geschlossen-Zustand eines Formulars und die Kopf-Beschreibung
  einer Datenbank sind nicht rücklesbar; Pflichtfelder sind technisch
  nicht erzwingbar. Folgen: Der Bauer legt keine Formular-Ansichten an,
  „Pflicht" heißt „als Pflicht gekennzeichnet", und der Validator führt
  Unprüfbares als Messgrenze in der Freigabe-Zeile statt es zu
  behaupten.
- **FB-05 · Maschinengate und Regenerations-Schutz.**
  `tools/formular_pruefen.py` prüft das Spezifikations-Format (FB-G1),
  die Board-Treue jedes nicht als *Setzung* markierten Fragetextes
  VOR dem Bau (FB-G2), die Schutzregeln aus FB-02/FB-03 (FB-G3), das
  `BAULOG.md` (je Bau eine Zeile `<slug> — gebaut <Datum> — <URL>`,
  FB-G4) und die Freigabe-Konsistenz (FB-G5): freigegeben nur mit
  Baulog-Zeile, Stand-Datum gleich dem Datum der letzten Baulog-Zeile
  — ein Neubau entwertet die Freigabe maschinell. Das Gate läuft per
  Hook bei jedem Schreiben von Spez, Baulog oder Freigabe.
- **FB-04 · Eine Freigabe-Wahrheit.** Freigaben stehen AUSSCHLIESSLICH
  in `praesentationen/eval/FORMULAR-FREIGABE.md` und kommen nur vom
  formular-validator, der die GEBAUTEN Bögen per Notion-Abruf
  zurückliest (Wort für Wort gegen Board UND Spezifikation). Format
  strikt `<bogen-slug> — freigegeben (Stand <Datum>, <URL>, …)` bzw.
  `… — ABGELEHNT: …`; letzte Zeile je Bogen gewinnt. Der Bauer gibt
  nichts frei; der Validator schreibt in Notion nichts.

- **AS-08 · Kein Hintergrundkasten im Asset.** Ein Mock zeigt sein
  Objekt (Fenster, Terminal, Dialog, Blatt) — keine Grundfläche
  darunter. Eine andersfarbige Umrandung wird auf der weißen Folie zum
  sichtbaren Kasten und liest sich als Fehler (Befund Christian
  15.10.2026 an 36 von 53 Assets). Vollflächige Terminals, die den
  Rahmen füllen, sind davon nicht betroffen. Der Builder beschneidet
  einfarbige Ränder seit dem 15.10.2026 beim Einfügen automatisch
  (`Bau.asset_ohne_rahmen`) — das ist die Rückfalllinie, nicht die
  Entschuldigung: Neue Assets werden ohne Kasten geplant.
