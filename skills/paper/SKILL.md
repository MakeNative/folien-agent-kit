---
name: paper
description: "Baut und prüft das Short Paper zu einer Session: Grafiken aus den Deck-Skizzen (grafik-designer), papier-writer, maschinelles Gate SP-01..SP-05, Belegketten- und Publikums-Prüfung, Fix-Entscheidung. Triggers on: /folien-kit:paper <deck-name>"
argument-hint: "<deck-name, z. B. T1>"
---

Du orchestrierst, du schreibst nicht selbst (FP-01, FP-02). Voraussetzung:
das Deck ist abgenommen.

1. **Grafiken.** Für jede Schaubild-Folie des Decks (Form: Schaubild) spawn
   `grafik-designer` mit Skizze + Folie + Handout-Ausschnitt. Ergebnis:
   .mmd-Dateien unter praesentationen/grafiken/.
2. **Writer.** Spawn `papier-writer` mit Deck, Handout-Modul und den
   Grafik-Pfaden. Ziel: praesentationen/sessions/<TAG>/P-<TAG>.md, Wortbudget 900.
3. **Gate.** `python3 "${CLAUDE_PLUGIN_ROOT}/tools/papier_pruefen.py"
   praesentationen/sessions/<TAG>/P-<TAG>.md` — Befunde als Fix-Auftrag zurück,
   maximal zwei Runden.
4. **Prüfer, parallel:** `belegkette-pruefer` (Paper → Handout → Claim; die
   Vertiefungs-Verweise sind die Kette) und `publikum-entwickler` (liest NUR
   das Paper: findet er in 60 Sekunden, wie man X tut?).
5. **Entscheiden, abnehmen, protokollieren** wie in der deck-Skill
   (pruefergebnis je Prüfer, Berichte nach
   praesentationen/pruefberichte/, abnahme-Ereignis mit wortzahl).

Memory: nur protokoll-belegte Handwerksregeln für papier-writer und
grafik-designer; publikum bleibt leer (FP-03).
