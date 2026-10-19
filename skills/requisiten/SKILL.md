---
name: requisiten
description: "Stellt je Session das Demo-Material her und prüft es: requisiten-planner, Maschinengate, requisiten-bauer, requisiten-validator, eine Fixrunde, Mappenbau. Triggers on: /folien-kit:requisiten <TAG>"
argument-hint: "<TAG>"
---

Du orchestrierst, du baust nicht selbst (FP-01, FP-02).

**Was diese Straße löst:** Die Decks *beschreiben* Requisiten, die nie
*hergestellt* wurden. Der Trainer bekommt eine Mappe mit Deck und Handout
und muss vier bis zehn Dokumente selbst erfinden, deren Inhalt nur in der
Prosa des Decks steht.

**Freigabe-Wahrheit:** ausschließlich `requisiten/FREIGABE.md`, und die
schreibt nur der Validator.

## Vorab lesen

- `praesentationen/BEDARFE.md`, Abschnitt dieser Session — je Demo-Folie
  *verlangt · abgeleitet · Probe · Rückfall*
- `praesentationen/PLAN-VORFUEHRPROJEKT.md` — warum das Vorführprojekt
  der Rückfall ist und nicht die Welt

## Ablauf

1. **Planner.** Spawn `requisiten-planner` mit dem Session-Ordner.
   Ergebnis: `sessions/<TAG>/requisiten/manifest.json`. Meldet er einen
   `TUN:`-Block, der etwas verlangt, das in keiner Liste steht, ist das
   ein **Deck-Befund** — melden, nicht selbst reparieren.

2. **Gate.** `python3 "${CLAUDE_PLUGIN_ROOT}/tools/requisiten_pruefen.py"
   praesentationen` — Befunde als Fix-Auftrag zurück an den Planner,
   höchstens zwei Runden. Danach liegt der Fehler im Plan, nicht im Lauf.

3. **Bauer.** Spawn `requisiten-bauer` mit Manifest, Deck und Register.
   Er stellt die `datei`- und `vorlage`-Posten her und markiert jede
   selbst formulierte Zeile. Braucht er einen neuen Projektstand, legt
   er ihn an — und einen **veröffentlichten Tag verschiebt er nicht**.

4. **Gate** erneut: jede im Manifest genannte Datei existiert.

5. **Validator.** Spawn `requisiten-validator`, getrennte Instanz. Er
   schreibt `FREIGABE.md` und legt seinen Bericht unter
   `pruefberichte/<TAG>-requisiten-validator.md` ab. Abgelehnte Posten
   ⇒ **eine** gebündelte Fixrunde an den Bauer, nummerierte Befunde.
   Danach: zurück zum Planner oder ehrlich auf `offen` drehen.

6. **Demo-Probe.** Für jeden Bedarf mit einem `Probe`-Feld in
   `BEDARFE.md`: führ sie aus. Nicht lesen — **ausführen**. S2 F7
   verlangt zwei Läufe, die messbar auseinanderlaufen; ob sie das tun,
   sieht man nicht am Text.

7. **Mappe.** `./bau <TAG>`. Dann die Gegenprobe am fertigen Ordner:
   eine Demo-Folie durchgehen, nur mit der Mappe, ohne die Quelle.

## Was in den Chat gehört

- Ein Bedarf der Art `System` oder `Infra` (Zugang, CI, Remote-Betrieb).
  Das sind **organisatorische Voraussetzungen**, keine Pipeline-Leistung.
  Melden und mocken, nicht still übergehen.
- Jeder neue Name in der erfundenen Welt, bevor er benutzt wird.
- Eine Demo-Probe, die nicht die Wirkung erzeugt, die der Bedarf nennt.

## Kein Kosten-Gate

Anders als die `assets`-Straße: Hier entstehen Dokumente, keine Bilder
(Christian, 19.10.). Entsteht doch einmal ein Bild, läuft es über
`/folien-kit:assets`, und dort greift das Kosten-Gate.
