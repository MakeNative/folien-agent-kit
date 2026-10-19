---
name: deck
description: "Baut und prüft ein Dünn-Deck aus einem Handout-Modul: Spezifikation, folien-writer, maschinelles Gate, drei unabhängige Prüfer, Fix-Entscheidung. Triggers on: /folien-kit:deck <deck-name | spezifikation>"
argument-hint: "<deck-name oder Pfad zur Spezifikation>"
---

Du orchestrierst, du baust nicht selbst (FP-01, FP-02).

1. **Spezifikation.** Liegt keine vor, schreib sie zuerst nach
   praesentationen/sessions/<TAG>/SPEZIFIKATION-<TAG>.md: Session und Board-Titel,
   Budget (F-01-Richtwert), Leinwandzeit, Handout-Modul, die 5–8 Punkte, die
   die Leinwand tragen MUSS — jede als maschinenlesbare Zeile:
   `MUSS: <schlagwort> — Handout: <Modul> F<n> — <n> min`.
   Der Handout-Anker ist vor dem Writer-Lauf per Grep zu prüfen (FP-04:
   was das Handout nicht trägt, kann kein Deck tragen — Pilotlauf: zwei von
   vier Spez-Lücken wären so für null Token vorab gefallen); die
   Minutensumme muss unter der Leinwandzeit liegen. Wird ein MUSS-Punkt
   später gestrichen, bleibt seine Zeile stehen und bekommt
   ` — GESTRICHEN (<grund>)` — sonst meldet F-07. Dazu: was ausdrücklich
   Handout bleibt. Frag den Nutzer im Chat, wenn eine Programm-Entscheidung
   fehlt.
2. **Writer.** Spawn `folien-writer` mit Spezifikation und Handout-Modul.
3. **Gate.** `python3 "${CLAUDE_PLUGIN_ROOT}/tools/folien_pruefen.py"
   praesentationen/sessions/<TAG>/<name>.md` — Befunde gehen als Fix-Auftrag an den
   Writer zurück, maximal zwei Runden; danach liegt das Problem in der
   Spezifikation.
4. **Prüfer, parallel:** `belegkette-pruefer`, `trainer-leser`,
   `publikum-entwickler` — je mit dem Deck (Publikum ohne Handout!).
5. **Entscheiden.** Leg zuerst jeden Prüferbericht als Datei ab
   (praesentationen/pruefberichte/<deck>-<rolle>.md) — 46 erzeugte und
   0 lesbare Befunde waren die teuerste Protokolllücke des Pilotlaufs. Dann
   sortierst du die Befunde (behebbar jetzt / Programm-Entscheidung /
   verworfen mit Grund), beauftragst den Writer mit der Fix-Liste, fährst
   das Gate erneut und nimmst ab. Streicht die Fix-Liste einen MUSS-Punkt,
   zieh die Spezifikation im selben Schritt nach (GESTRICHEN-Zeile) —
   im Pilot verschwand so ein Pflichtpunkt unter grünem Gate.
6. **Protokoll.** Jeder Schritt steht im Laufprotokoll (die Werkzeuge
   schreiben selbst); Agentenläufe trägst du mit Token und Dauer nach
   (ereignis `agentenlauf`), Blockaden meldet der Hook. Zusätzlich je
   Prüfer ein Ereignis `pruefergebnis` mit `rolle`, `deck`, `befunde`,
   `uebernommen`, `verworfen` und `verworfen_grund` (je Befund eine Kurzzeile mit Regel-Bezug, kein Sammelstring) —
   ohne diese Zeile kann `evaluieren` Rauschen nicht von Ertrag trennen
   (FP-05).

Memory: trage nach dem Lauf nur protokoll-belegte Handwerksregeln in die
Memories von folien-writer und trainer-leser ein; publikum-entwickler bleibt
leer (FP-03).
