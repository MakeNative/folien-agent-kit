---
name: tagesdetail
description: "Baut und prüft die Durchführungs-Tagesblätter des Programms (W0, S1–S5, T1–T20): tagesdetail-writer, Maschinengate, board-treue-pruefer + trainer-leser, eine Fixrunde. Triggers on: /folien-kit:tagesdetail <tag-ids|alle>"
argument-hint: "<tag-ids, z. B. T1 T2 T3 — oder: alle>"
---

Du orchestrierst, du baust nicht selbst (FP-01, FP-02). Wahrheit der
Straße ist das Trio Board-Abzug → Modul → Deck; Lücken werden
gemeldet, nie gefüllt (TD-01).

1. **Abzug aktualisieren.** Vor dem ersten Writer-Lauf prüfst DU, ob
   `praesentationen/BOARD-ABZUG.md` den aktuellen Board-Stand trägt
   (Figma-Zugriff hat nur der Orchestrator — die Agenten lesen den
   Abzug). Ein veralteter Abzug macht jede Prüfung wertlos; neue
   Frames als datierten Nachtrag anhängen, wie etabliert.
2. **Writer.** Spawn `tagesdetail-writer` je Welle (4–6 Tage je
   Instanz, nach Wochen gruppiert — W0+S, W1, W2, W3, W4). Im Prompt:
   die Tag-IDs, die zugehörigen Modul-/Deck-Dateien und die Liste der
   zulässigen Programm-Entscheidungen samt Datum (nur die darf der
   Writer etikettieren).
3. **Gate.** `python3 "${CLAUDE_PLUGIN_ROOT}/tools/tagesdetail_pruefen.py"
   praesentationen/tagesdetails/` — Befunde als Fix-Auftrag zurück an
   den Writer, maximal zwei Runden. (Der Hook fährt dasselbe Gate bei
   jedem Schreiben eines Tagesblatts.)
4. **Prüfer, parallel:** `board-treue-pruefer` (Quellen-Echtheit,
   erfundene Zahlen, still gefüllte Lücken, Karten-Vollständigkeit)
   und `trainer-leser` (hält den Tag probehalber NUR mit dem Blatt —
   jede Stelle, an der er improvisieren müsste, ist ein Befund).
5. **Entscheiden.** Befunde sortieren (behebbar jetzt /
   Programm-Entscheidung / verworfen mit Grund), EINE konsolidierte
   Fixrunde an den Writer, Gate erneut, abnehmen. Widersprüche
   zwischen Board-Karte und Deck/Modul sind Programm-Entscheidungen —
   im Chat melden, nicht still auflösen.
6. **Ablage + Protokoll.** Prüfberichte nach
   `praesentationen/decks/pruefberichte/tagesdetails-<welle>-<rolle>.md`
   (dort liegen auch die Asset-Berichte — ein Ort für alle
   Prüfberichte dieses Projekts);
   je Agentenlauf ein `agentenlauf`-Ereignis mit Token und Dauer, je
   Prüfer ein `pruefergebnis`-Ereignis ins Laufprotokoll (FP-05).

Memory: nach dem Lauf nur protokoll-belegte Handwerksregeln in das
Memory des tagesdetail-writer; board-treue-pruefer bleibt leer
(FP-03 — Messinstrument).
