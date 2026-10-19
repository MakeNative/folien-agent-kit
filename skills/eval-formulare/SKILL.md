---
name: eval-formulare
description: "Baut und prüft die Evaluationsbögen des Programms in Notion: Spezifikation gegen den Board-Abzug, Maschinengate, formular-bauer, formular-validator, eine Fixrunde. Triggers on: /folien-kit:eval-formulare"
argument-hint: "[bogen-slug ...] — leer = alle Bögen der Spezifikation"
---

Du orchestrierst, du baust nicht selbst (FP-01, FP-02). Die Fragetexte
gehören dem Board; was nicht im `BOARD-ABZUG.md` steht, ist eine
Setzung und wird als solche markiert (FB-01, FB-02).

1. **Abzug prüfen.** Trägt `praesentationen/BOARD-ABZUG.md` den
   aktuellen Stand der Eval-Row? Figma liest nur der Orchestrator;
   neue Karten als datierten Nachtrag anhängen.
2. **Spezifikation schreibst DU**, nicht der Bauer:
   `praesentationen/eval/FORMULAR-SPEZ.md` — je Bogen Slug, Name,
   Kopf-Beschreibung, Anonym-Zeile, nummerierte Felder
   (`<Frage> — <Feldtyp>, <Pflicht/optional>`), interner
   Auswertungsblock. Jeder nicht wörtlich belegte Text trägt
   `*Setzung (Orchestrator, <Datum>)*`.
3. **Gate.** `python3 "${CLAUDE_PLUGIN_ROOT}/tools/formular_pruefen.py"
   praesentationen/eval/` — es prüft die Spezifikation gegen den
   Board-Wortlaut, BEVOR irgendetwas in Notion entsteht. Befunde
   korrigierst du in der Spezifikation, nicht im Bogen. (Der Hook
   fährt dasselbe Gate bei jedem Schreiben von Spez/Baulog/Freigabe.)
4. **Zielort klären.** Der Bau-Auftrag nennt die Notion-Parent-Seite.
   Existiert dort ein Bogen gleichen Namens, STOPPT der Bauer — dann
   entscheidest du (neue Version, anderer Name, Abbruch) im Chat.
5. **Bauer.** Spawn `formular-bauer` mit Spezifikation und Zielort.
   Nach dem Lauf trägst DU je gebautem Bogen eine Zeile ins
   `praesentationen/eval/BAULOG.md`:
   `<slug> — gebaut <YYYY-MM-DD> — <Notion-URL>`. Ohne Baulog-Zeile
   kann der Validator nicht freigeben (FB-G5).
6. **Gate** erneut (Baulog-Format, Slugs).
7. **Validator.** Spawn `formular-validator` (getrennte Instanz; liest
   die GEBAUTEN Bögen aus Notion zurück, schreibt
   `FORMULAR-FREIGABE.md` im strikten Format mit Stand-Datum =
   Datum der letzten Baulog-Zeile). Bericht ablegen unter
   `praesentationen/pruefberichte/eval-formulare-validator.md`.
   Abgelehnte Bögen ⇒ EINE gebündelte Fixrunde an den Bauer; danach
   neue Baulog-Zeile (die alte Freigabe verfällt maschinell) und
   Validator erneut. Nach der zweiten Ablehnung liegt das Problem in
   der Spezifikation → zurück zu Schritt 2.
8. **Gate** final — muss still sein.
9. **Protokoll.** Je Agentenlauf ein `agentenlauf`-Ereignis mit Token
   und Dauer, je Validator-Lauf ein `pruefergebnis`-Ereignis (FP-05).

Memory: nach dem Lauf nur protokoll-belegte Handwerksregeln in das
Memory des formular-bauer; der formular-validator bleibt leer
(FP-03 — Messinstrument).
