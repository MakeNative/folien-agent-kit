# folien-agent-kit

Agenten-Pipeline für Dünn-Decks: Leinwand-Foliensätze mit harten Budgets, dazu das
Short Paper zur Session und die Schaubilder, die beide gemeinsam nutzen. Die Leinwand
trägt einen Gedanken je Folie und keinen Beleg-Apparat; die Belegkette läuft
Leinwand → Handout → Claim.

## Voraussetzung

Dieses Kit baut **keine** Inhalte. Es setzt ein Dokumentprojekt voraus, in dem belegte
Handout-Module liegen — erzeugt mit dem
[recherche-agent-kit](https://github.com/MakeNative/recherche-agent-kit). Ohne Handout-Modul
hat der folien-writer nichts, woraus er eine Folie belegen könnte, und das Gate schlägt fehl.

## Warum so

Ein Deck fällt nicht durch falsche Aussagen auseinander, sondern durch zu volle Folien und
durch Behauptungen, die das Handout nicht trägt. Beides lässt sich messen statt bereden:

- **Harte Budgets, maschinell geprüft.** `tools/folien_pruefen.py` misst nach jedem
  Schreiben die Regeln F-01…F-06. Kein Ermessen, kein „passt schon".
- **Fußnoten sind auf der Leinwand blockiert.** Ein PreToolUse-Hook verhindert sie, statt
  sie hinterher anzumahnen.
- **Drei unabhängige Prüfer statt Selbstkontrolle.** Der Writer prüft sich nicht selbst ab;
  Belegkette, Trainer-Probelauf und ein skeptisches Publikum laufen getrennt.

## Installation

```bash
/plugin marketplace add MakeNative/folien-agent-kit
/plugin install folien-kit@folien-kit-marketplace
```

Python 3 wird gebraucht, sonst nichts — die Werkzeuge nutzen nur die Standardbibliothek.

## Was drin ist

**7 Agenten** (`agents/`):

| Agent | Rolle |
|---|---|
| `folien-writer` | baut das Deck aus einem Handout-Modul, nach Spezifikation |
| `papier-writer` | schreibt das Short Paper zur Session |
| `grafik-designer` | übersetzt eine Skizze-Zeile in eine Mermaid-Grafik samt Alt-Text |
| `belegkette-pruefer` | prüft Folie → Handout-Stelle → Claim |
| `trainer-leser` | hält das Deck probehalber ab und meldet, wo die Session kippt |
| `publikum-entwickler` | sitzt als skeptischer Entwickler drin, memoryfrei als Messinstrument |
| `lauf-auswerter` | wertet Laufprotokoll und Gate-Berichte über die Pipeline selbst aus |
| `folien-layout-pruefer` | prüft das PowerPoint-Rendering jeder Folie auf überlappenden, abgeschnittenen und überlaufenden Text |

**3 Skills** (`skills/`):

| Skill | Was sie tut |
|---|---|
| `/folien-kit:deck` | Spezifikation → Bau → Gate → drei Prüfer → Fix-Entscheidung |
| `/folien-kit:paper` | Short Paper zur Session, geprüft gegen SP-01…SP-05 |
| `/folien-kit:evaluieren` | wertet einen oder mehrere Deck-Läufe aus |

**Gates und Regeln:**

- `tools/folien_pruefen.py` — maschinelles Gate F-01…F-06, mit Selbsttest
- `tools/layout_pruefen.py` — Layout-Gate für gebaute PPTX: rendert mit PowerPoint (macOS), bricht bei Ersatzschrift ab, misst Wortüberlappung und Überlauf mit echten Glyphenbreiten; Selbsttest `tools/layout_selbsttest.py`. Nie auf einem LibreOffice-Rendering abnehmen: headless ersetzt es Schriften still.
- `hooks/guard-leinwand.py` — blockiert Fußnoten auf Folien (PreToolUse)
- `hooks/guard-folien.py` — misst nach jedem Schreiben (PostToolUse)
- `docs/REGELWERK.md` — F-, D- und FP-Regeln sowie das Deck-Format

## Ablaufspuren

Logs: `.claude/folien-log/lauf.jsonl` im Dokumentprojekt. Memories:
`.claude/agent-memory/folien-kit-<agent>/` — das Publikum bleibt memoryfrei, damit es als
Messinstrument taugt.

## MakeNative

Dieses Kit ist Teil von [MakeNative](https://makenative.de). Wir arbeiten jeden Tag mit
Agenten-Pipelines wie dieser und bringen anderen bei, sie für ihre eigenen Prozesse zu
bauen. Für Entwickler genauso wie für alle, die ihre Arbeit mit KI automatisieren wollen.

Du willst das für deine Arbeit lernen? Trag dich in die Liste ein:
[Bewerbung Starter-Kohorte](https://tally.so/r/5ByYj6?utm_source=github&utm_medium=readme&utm_campaign=starter-kohorte)

Christian Eichmüller · [LinkedIn](https://linkedin.com/in/christianeichmueller)
