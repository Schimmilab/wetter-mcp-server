# Agent Review Contract

Fünf Prüfregeln für automatisierte Code-Reviews in diesem Repository — für Copilot Code Review, Claude Code, Codex oder einen menschlichen Reviewer, der es eilig hat.

**Wozu das hier gut ist:** Ein Review-Agent ohne Projektkontext findet Syntax und Stil. Beides ist hier schon durch Linter und Tests abgedeckt. Was er *nicht* von allein findet, sind die Fehler, die dieses Projekt tatsächlich einmal gemacht hat — und genau die stehen unten. **Jede Regel hat einen echten Vorfall als Beleg.** Erfundene Best-Practice-Regeln sind bewusst nicht dabei; sie erzeugen Kommentar-Rauschen und trainieren Reviewer darauf, die Liste zu ignorieren.

**Wie zu lesen:** Jede Regel hat eine **Prüffrage** (das ist der Auftrag) und ein **Kein Treffer, wenn** (das begrenzt die Fehlalarme). Wenn beides nicht zutrifft, ist es kein Fund — dann bitte schweigen.

> ℹ️ **Übertragung nach `tibber-mcp-server` am 2026-07-30 — was dabei herauskam:** Die **Regeln 1–4 waren wortgleich übertragbar** und bilden damit den wiederverwendbaren Kern. **Regel 5 war es nicht** — sie hängt hier an `.env.example`, das es im Tibber-Repo gar nicht gibt (der Token kommt über den `env`-Block der MCP-Konfiguration). Dort kamen stattdessen zwei eigene Regeln dazu, die sich aus dem Zweck jenes Servers ergeben (Geldbeträge, Live-Verbindung). **Faustregel für weitere Repos: vier Regeln kopieren, den Rest aus dem konkreten Zweck ableiten.**

---

## 1 — Keine privaten Daten, und zwar auch nicht in der History

**Prüffrage:** Enthält der Diff eine echte Postadresse, einen echten Personennamen, eine private IP oder einen internen Hostnamen, eine Telefonnummer oder eine reale Mail-Adresse — auch in Beispielen, Docstrings, Testdaten oder Commit-Messages?

**Warum:** Beim Public-Release *dieses* Repos stand eine private Wohnadresse als Beispielort im Design-Dokument. Aufgefallen kurz vor dem Push; die Bereinigung ging nur noch über `git filter-repo` über die gesamte Historie. **Ein Secret-Scanner hätte das nicht gefunden** — es war kein Token, sondern eine Adresse. Für ein Wetter-Tool sind Ortsangaben der natürliche Beispielinhalt, das macht dieses Repo besonders anfällig.

**Die Grenze läuft bei der Genauigkeit, nicht beim Ortsnamen** — kalibriert am Bestand dieses Repos:

| Im Code | Bewertung |
|---|---|
| Straße + Hausnummer + PLZ (eine echte Hausanschrift) | 🔴 **Fund** |
| Koordinaten mit 5+ Nachkommastellen (Hausgenauigkeit) | 🔴 **Fund** |
| `DEFAULT_ORT = "Steinenbronn"`, `48.6667 / 9.1333` | ✅ **kein Fund** — Gemeindeebene, gerundet auf Ortsmitte, und in der README **offen als solche benannt**. Ein Wetter-Server braucht einen Default-Ort; das ist eine bewusste Entscheidung, keine Panne. |
| `Berlin`, `Stockholm`, `Bozen` in Beispielen | ✅ kein Fund |

**Kein Treffer, wenn:** die Ortsangabe auf Gemeindeebene bleibt und als Default dokumentiert ist. Ein Reviewer, der den vorhandenen `Steinenbronn`-Default meldet, hat die Regel überdehnt — dann lieber schweigen.

**Ebenfalls kein Fund: das öffentliche Pseudonym.** „Schimmi" / „Schimmilab" ist die Marke, unter der diese Repos ohnehin erscheinen (GitHub-Organisation, schimmilab.de) — ein Personenbezug, der bereits öffentlich ist, wird durch Nennung nicht privater. **Ein Fund ist der Klarname**, nicht das Pseudonym. Gleiches gilt für generische lokale Pfade wie `~/workspace/…`: sie verraten keine Struktur, die nicht ohnehin Konvention wäre.

> 🔎 **Diese Abgrenzung entstand aus einem Selbsttreffer.** Bei der Anwendung der Regel auf den eigenen Diff — vor dem ersten Push — stand in **genau dieser Tabelle** eine echte Hausanschrift als Negativbeispiel. Der Beleg für die Regel war selbst der Verstoß. Korrigiert vor dem Push, die Zeile beschreibt das Muster jetzt, statt es vorzuführen. **Lehre: ein Beispiel für „so sieht ein Leck aus" darf nie das echte Datum verwenden** — die Beschreibung reicht immer.

## 2 — Kein Filter, der still verwirft

**Prüffrage:** Verwirft der Code Eingaben, ohne zu melden, wie viele? Konkret: `if not x: continue`, `try/except: pass`, Regex-Filter, Typkonvertierungen mit stillem Fallback, `.get(key, default)` auf Pflichtfeldern. Wenn ja — wird **irgendwo** ausgewiesen, wie viele Datensätze bewertet und wie viele übersprungen wurden?

**Warum:** Das ist die teuerste wiederkehrende Fehlerklasse dieses Projekts, dreimal in zwei Wochen:
- Ein Auswertungsskript verglich Markdown-Zellen als exakte Strings und verwarf **12 von 15 Zeilen** — und gab aus den drei Restzeilen eine Korrelation aus, die das **Gegenteil** des dokumentierten Befunds behauptete.
- Ein Muster-Scanner gruppierte über exakte Stringgleichheit und meldete „keine wiederkehrenden Muster", obwohl **4 von 6 Einträgen** derselbe Vorgang waren.
- Ein Systemcheck meldete „✓ unauffällig", nachdem er **859 von 859** Prozessen übersprungen hatte.

**Der Kern in einem Satz: Ein Filter, der still verwirft, erzeugt keine Lücke, sondern eine falsche Zahl.** Eine ausgewiesene Abdeckung („7 von 16 Zeilen auswertbar") ist ehrlich; ein Ergebnis ohne Nenner ist es nicht.

**Kein Treffer, wenn:** das Verwerfen der Zweck der Funktion ist und der Umfang aus dem Rückgabewert hervorgeht (eine Suchfunktion muss nicht melden, was sie nicht gefunden hat).

## 3 — Fehler müssen sagen, was zu tun ist

**Prüffrage:** Nennt jede neue oder geänderte Fehlermeldung (a) was schiefging, (b) mit welchem Wert, und (c) was der Aufrufer dagegen tun kann? Ein MCP-Server antwortet einem Modell, nicht einem Menschen mit Debugger.

**Warum:** Der Bestand macht es richtig — `Ort '{name}' nicht gefunden.` nennt den konkreten Wert, `Wetterdienst nicht erreichbar: {exc}` unterscheidet Netzwerk- von Protokollfehler. Diese Qualität soll nicht durch eine beiläufig eingefügte `raise ValueError("invalid input")` verwässert werden. Ein Modell, das eine unspezifische Fehlermeldung bekommt, rät — und rät oft plausibel falsch.

**Kein Treffer, wenn:** die Meldung an einer Stelle steht, die der Aufrufer nie sieht (interne Assertion, Testcode).

## 4 — Abhängigkeiten brauchen eine Ober- und eine Untergrenze

**Prüffrage:** Hat jede Zeile in `dependencies` beide Grenzen? Eine reine Untergrenze (`>=3`) lässt jeden künftigen Major-Sprung ungetestet und unbemerkt einlaufen.

**Warum:** Eine Bestandsaufnahme über alle eigenen MCP-Server ergab Pins von `mcp>=0.9.0` bei installiertem `1.25.0` bis zu gar keiner Angabe — **nirgends eine Obergrenze.** Als das Protokoll auf eine zustandslose Fassung umgestellt wurde, hätte ein frisches `pip install` die neue SDK-Generation ungeprüft in produktiv laufende Server gezogen.

**Aktueller Stand dieses Repos — ein bekannter, offener Verstoß:** `fastmcp>=3` und `httpx>=0.27` in `pyproject.toml` haben beide keine Obergrenze. Ein Review, das diese Regel anwendet, muss das melden. **Das ist der Selbsttest für diese Datei:** Wenn ein Reviewer den Vertrag liest und trotzdem nichts sagt, wendet er ihn nicht an.

**Kein Treffer, wenn:** die Obergrenze bewusst offen ist und daneben als Kommentar begründet steht.

## 5 — Was die README verspricht, muss ausführbar sein

**Prüffrage:** Ändert der Diff einen Aufruf, einen Parameternamen, einen Env-Var-Namen oder ein Ausgabeformat, das in der README oder in `.env.example` steht — und wurde die Dokumentation mitgezogen?

**Warum:** Ein öffentlicher Server, dessen Quickstart nicht durchläuft, ist praktisch unbenutzbar; der Fehler fällt aber nie dem Autor auf, sondern nur Fremden — und die melden ihn nicht, sie gehen. Verwandter Fall aus demselben Bestand: ein Repo lag öffentlich auf GitHub, **ohne Lizenzdatei** — sichtbarer Code, den niemand legal verwenden darf. *Public heißt nicht nutzbar.*

**Kein Treffer, wenn:** die Änderung rein intern ist und keinen in der Dokumentation genannten Namen berührt.

---

## Was dieser Vertrag bewusst NICHT enthält

Damit der Reviewer nicht anfängt, Zeilen zu zählen:

- **Keine Stilregeln.** Formatierung, Importreihenfolge und Zeilenlänge macht `ruff`. Ein Agent, der das kommentiert, verschwendet Aufmerksamkeit.
- **Keine Testabdeckungs-Quoten.** Die Testsuite ist grün oder nicht; eine Prozentzahl sagt hier nichts.
- **Keine Architekturvorschläge.** Das Projekt ist 293 Zeilen groß. Wer hier Schichten einzieht, löst ein Problem, das es nicht gibt.

## Herkunft

Alle fünf Regeln stammen aus dokumentierten Vorfällen im eigenen Bestand, nicht aus einer allgemeinen Best-Practice-Liste. Der Vertrag ist bewusst **werkzeugunabhängig** formuliert — dieselbe Datei soll für Copilot Code Review, Claude Code und Codex taugen, statt dass für jedes Werkzeug eine eigene Prompt-Variante gepflegt wird.

---

## Spieltest 2026-07-30 — was greift, was ist Rauschen

Der Vertrag wurde gegen drei Eingaben geprüft, bevor er in Betrieb geht.

### A · Konstruierter Diff mit eingebauten Verstößen

| Regel | Eingebaut | Erkannt |
|---|---|---|
| 1 Private Daten | Hausanschrift in einem Docstring-Beispiel | ✅ |
| 2 Stiller Filter | `except KeyError: continue` · `if not q.strip(): continue` · `except …: pass` — drei Verwerfungen, kein Zähler | ✅ |
| 3 Fehlermeldung | `raise ValueError("invalid input")` — ohne Wert, ohne Handlungsanweisung | ✅ |
| 4 Dependency-Pin | `python-dateutil>=2.9` ohne Obergrenze | ✅ |
| 5 Doku-Bruch | `DEFAULT_ORT` liest plötzlich `DEFAULT_PLACE`, README und `.env.example` nennen weiter `DEFAULT_ORT` | ✅ — und das ist der **wertvollste** Fund: bestehende Konfigurationen brechen **still**, der Server läuft weiter und nimmt einfach den Default |

**Rauschtest im selben Diff, beide bestanden:** die rein internen Umbenennungen `loc → resolved` und `data → payload` lösten **keinen** Kommentar aus (kein in der Dokumentation genannter Name berührt), und der bestehende `Steinenbronn`-Default ebenfalls nicht.

> ⚠️ **Für sich genommen beweist Teil A wenig** — der Diff wurde gebaut, um die Regeln zu treffen. Ein Test, den man auf die eigene Erwartung hin konstruiert, bestätigt die Erwartung. Deshalb Teil B.

### B · Echter Commit aus der History (`675dfda`, 11.07.)

Angewendet auf einen unveränderten realen Commit (`server.py` + Tests, 97 Zeilen): **null Fehlalarme.**

Bemerkenswert ist Regel 1 an dieser Stelle. Der Commit führt den Default-Ort ein und trägt im Code den Kommentar *„Steinenbronn (Ortsmitte — öffentlich, nicht die Straßenadresse)"*. Ein Reviewer mit einer naiven „kein Wohnort im Code"-Regel hätte hier kommentiert — **die kalibrierte Fassung schweigt korrekt.** Die Grenze bei der *Genauigkeit* statt beim *Ortsnamen* zu ziehen, war die entscheidende Korrektur; sie entstand erst durch diesen Test.

### C · Aktueller Bestand

Ein echter, offener Verstoß: **`fastmcp>=3` und `httpx>=0.27` haben keine Obergrenze** (Regel 4). Kein konstruierter Fall — der Zustand steht so in `pyproject.toml`.

### Fazit

Fünf von fünf Regeln greifen auf konstruierte Verstöße, null Fehlalarme auf echtem Code, ein echter Fund im Bestand. **Die Regeln, die am meisten tragen, sind 2 und 5** — beide beschreiben Fehler, die *nicht auffallen*: ein Filter, der still verwirft, und eine Konfiguration, die still auf den Default zurückfällt. Regel 3 ist am nächsten an dem, was ein Standard-Linter ohnehin anmahnt, und damit die verzichtbarste.
