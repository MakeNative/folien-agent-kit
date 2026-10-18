---
name: assets
description: "Erzeugt und prüft alle Bild-/Clip-/Foto-Assets eines abgenommenen Decks: asset-planner, Maschinengate, asset-generator, asset-validator, eine Fixrunde, Builder-Overlay. Triggers on: /folien-kit:assets <deck-name>"
argument-hint: "<deck-name>"
---

Du orchestrierst, du baust nicht selbst (FP-01, FP-02). Voraussetzung:
Das Deck ist abgenommen (Gates grün, Fixrunden durch) — Assets auf ein
Deck in Bewegung sind Wegwerfarbeit. Freigabe-Wahrheit: AUSSCHLIESSLICH
`FREIGABE.md` (AS-05); der Plan-Status endet bei `erzeugt`, du setzt
nie einen Freigabe-Status.

1. **Planner.** Spawn `asset-planner` mit dem Deck. Ergebnis:
   `praesentationen/pptx/assets/<deck>/ASSET-PLAN.md` + gepflegtes
   `FIKTIV-REGISTER.md` (Register ZUERST — Hook-Reihenfolge). Meldet
   der Planner Folien mit mehr als einer Marke (AS-07), ist das ein
   Deck-Fix VOR allem Weiteren. Offene Programm-Entscheidungen
   (Eigentümer für Route offen, Fiktivnamen nahe an realen Produkten)
   fragst du im Chat, bevor es weitergeht.
2. **Gate.** `python3 "${CLAUDE_PLUGIN_ROOT}/tools/assets_pruefen.py"
   praesentationen/decks/<deck>.md` — Befunde als Fix-Auftrag zurück an
   den Planner, maximal zwei Runden. (Der Hook fährt dasselbe Gate bei
   jedem Schreiben von Plan/Ledger/Freigabe; das Gate loggt sich
   selbst ins Laufprotokoll.)
3. **Kosten-Gate.** Zähle die foto-Blöcke. Bei mehr als fünf nennst du
   die Zahl (plus möglichen Retry = ×2) im Chat und WARTEST auf das Go
   — Credits sind echtes Geld.
4. **Generator.** Spawn `asset-generator` mit Plan und Ablagepfaden.
   Die Werkzeuge (HyperFrames-CLI, higgsfield-CLI) sind im Hauptkonto
   angemeldet; bricht eine CLI mit Auth-Fehler ab, stoppst du und
   meldest es im Chat statt Workarounds zu bauen.
5. **Gate** erneut (Status erzeugt ⇒ Datei + Ledger).
6. **Validator.** Spawn `asset-validator` (getrennte Instanz, liest
   Plan + Dateien + Deck; schreibt FREIGABE.md im strikten Format mit
   Stand-Datum). Leg seinen Bericht als Datei ab:
   `praesentationen/decks/pruefberichte/<deck>-asset-validator.md`
   (Pilot-Lektion aus `deck`: unabgelegte Befunde sind verlorene
   Befunde). Abgelehnte Dateien ⇒ EINE gebündelte Fixrunde an den
   Generator (per SendMessage, nummerierte Befunde); der Generator
   regeneriert (neue Ledger-Zeile ⇒ alte Freigabe verfällt maschinell),
   danach Validator erneut — er prüft nur Dateien ohne gültige
   Freigabe. Nach der zweiten Ablehnung liegt das Problem im Plan →
   zurück zu Schritt 1, oder Block ehrlich auf Route/Status `offen`
   mit Eigentümer-Zeile drehen.
7. **Gate** final — muss still sein.
8. **Overlay-Build.** Deck neu bauen
   (`.venv-pptx/bin/python praesentationen/pptx/bau_deck.py
   praesentationen/decks/<deck>.md praesentationen/pptx/<deck>.pptx
   --pruefen`) — der Builder legt NUR Dateien mit gültiger
   FREIGABE-Zeile über die Platzhalter; `offen`-Blöcke behalten ihre
   BILD-FOLGT-Fläche (gewollt). Liefert `--pruefen` Befunde, gehen
   Overlay-bedingte (z. B. Flächen-/Inhalts-Checks) an dich bzw. den
   Builder-Maintainer — NICHT als Fixauftrag an den folien-writer.
   Sichtstichprobe: mindestens eine Asset-Folie im gerenderten PDF
   per Read ansehen.
9. **Deck-Fix nach Freigabe** (Wiederholungslauf): Ändert sich ein
   Deck nach erteilten Freigaben, rendert der Generator die
   betroffenen mocks/clips aus dem bestehenden `_projekte/<deck>`-
   Projekt neu (neue Ledger-Zeile ⇒ Freigabe verfällt), dann Schritt 6
   bis 8. Fotos bleiben unberührt, solange ihr Block unverändert ist.
10. **Protokoll.** Je Agentenlauf ein `agentenlauf`-Ereignis MIT Token
    und Dauer, je Validator-Lauf ein `pruefergebnis`-Ereignis (rolle,
    deck, befunde, uebernommen, verworfen, verworfen_grund) ins
    Laufprotokoll — ohne das ist `evaluieren` blind (FP-05).

MP4-Clips werden nicht in die PPTX eingebettet; sie liegen als
Trainer-Material im Asset-Ordner und die Folie trägt das Standbild.

Memory: nach dem Lauf nur protokoll-belegte Handwerksregeln in die
Memories von asset-planner und asset-generator; asset-validator bleibt
leer (FP-03 — Messinstrument).
