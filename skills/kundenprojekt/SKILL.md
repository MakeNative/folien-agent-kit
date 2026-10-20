---
name: kundenprojekt
description: "Setzt ein Kundenprojekt an die Stelle des Vorführprojekts: repo-leser nimmt es gegen BEDARFE.md auf, aufgaben-schneider schneidet die Requisiten, die Proben werden ausgeführt. Triggers on: /folien-kit:kundenprojekt <pfad-oder-url> [<TAG> ...]"
argument-hint: "<pfad-oder-url> [<TAG> ...]"
---

Du orchestrierst, du schneidest nicht selbst (FP-01, FP-02).

**Wofür das gut ist:** Die Decks sind so geschrieben, dass die Demos im
Projekt des Teilnehmers laufen — „sein Ticket in seinem Repo". Diese
Straße macht das vorbereitbar: Sie liest ein fremdes Projekt, sagt was
es hergibt, und schneidet daraus die Requisiten.

**Das Vorführprojekt bleibt der Rückfall.** Was hier nicht trägt, fällt
dorthin zurück — nicht aus.

## Vorab lesen

- `praesentationen/BEDARFE.md` — die 45 Bedarfe, davon 25 projektabhängig
- `praesentationen/PLAN-KUNDENPROJEKT-PROBE.md` — wie gemessen wird
- den letzten Bericht unter `pruefberichte/*-kundenprobe-*.md`

## Vor dem ersten Schritt

**Klon anlegen.** Nie im Arbeitsverzeichnis des Kunden arbeiten:

```
git clone --no-hardlinks <pfad-oder-url> <arbeitsordner>/<name>
```

Das Projekt läuft weiter, während die Straße liest. Und der Stand bleibt
reproduzierbar — ein Bericht ohne Commit-Kennung ist wertlos.

**Vertraulichkeit klären.** Liegt das Repo in einer fremden
Organisation, nennen alle Berichte Rollen statt Namen und tragen keine
Codeausschnitte. Frag im Chat, wenn du es nicht sicher weißt.

## Ablauf

1. **Repo-Leser.** Spawn `repo-leser` mit Klon und `BEDARFE.md`.
   Ergebnis: `DECKUNGSBERICHT.md` mit drei Urteilen je Bedarf und dem
   **ausgeführten** Testlauf.

   **Halt, wenn:** der eigene Codeanteil unter einem Zehntel liegt, oder
   die Testsuite nicht läuft. Beides meldest du im Chat, bevor es
   weitergeht — Schneiden auf einer solchen Grundlage kostet nur Zeit.

2. **Kosten- und Eingriffs-Gate.** Zähl die Bedarfe, die als *ableitbar
   mit Eingriff* geführt sind. Jeder Eingriff ins Kundenprojekt geht
   **einzeln** in den Chat, bevor der Schneider ihn anfasst.

3. **Aufgaben-Schneider.** Spawn `aufgaben-schneider` mit
   Deckungsbericht und Klon. Er schneidet je Bedarf das Requisit und
   **führt jede Probe aus**. Was zweimal nicht trägt, kommt als
   `nicht übertragbar` zurück.

4. **Gate.** `python3 "${CLAUDE_PLUGIN_ROOT}/tools/requisiten_pruefen.py"
   praesentationen` — jedes Requisit nennt Bedarf und Fundstelle.

5. **Validator.** Spawn `requisiten-validator`, getrennte Instanz. Er
   schreibt `FREIGABE.md` und prüft, was keine Maschine kann: Trägt die
   Datei, was die Folie verspricht? Reicht die Anleitung ohne das Deck?

6. **Bericht.** `pruefberichte/<datum>-kundenprobe-<repo>.md` mit den
   vier Zahlen: Deckung, Probe-Trefferquote, Nacharbeit, Dauer.

   **Die Trefferquote ist die Zahl, die zählt.** Deckung sagt, was das
   Repo hergibt; die Trefferquote sagt, ob die Requisiten tragen.

7. **Mappe.** `./bau <TAG>`, dann die Gegenprobe am fertigen Ordner.

## Was nicht erlaubt ist

- **Eine Sonderbehandlung für ein bestimmtes Repo.** Was du lernst, geht
  in `BEDARFE.md`, in einen Agenten oder in ein Gate. Ein Fix, der einen
  Repo-Namen enthält, ist keiner.
- **Ein Requisit ohne ausgeführte Probe**, wenn der Bedarf eine nennt.
- **Ein Schreibzugriff im Arbeitsverzeichnis des Kunden.**

## Bekannte Grenzen

Fünf Bedarfe waren in Lauf 1 nicht übertragbar, vier davon strukturell:
`S3 F15` (Systemzugang), `T13 F24` (CI ohne Zeitplan), `T13 F27` (der
Guard kommt mit unserer Lieferung), `T17b F6` (Remote-Betrieb). Dazu
`T1 F18` — Vorgänge liegen im Ticketsystem, nicht im Repo.

Sie werden **gemeldet und gemockt**, nicht erarbeitet (PE-2026-10-19f).
