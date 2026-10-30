# Vorlesen

Vorlesen liest Text vor, Satz für Satz: die eine Stelle für Sprachausgabe der eigenen Apps. Eine App schickt Text,
Vorlesen teilt ihn an Satzgrenzen und liefert den Ton Satz für Satz als Strom, damit die Wiedergabe sofort beginnt.
Gesprochen wird nur vom Sprechdienst des [Klangwerks](https://github.com/HalloWelt42/klangwerk) über die
[Leitstelle](https://github.com/HalloWelt42/leitstelle); das Modell bleibt dort isoliert. Stimme, Sprache und Tempo
wählt man hier, für alle Apps: feste Stimmen aus dem Katalog des Sprechdienstes oder eigene Stimmen, die die
[Vertonung](https://github.com/HalloWelt42/vertonung) für Vorlesen freigibt (gesprochen vom Klondienst des Klangwerks; die
Probe einer Stimme wird einmal geholt und eine halbe Stunde vorgehalten).

Eine App auf dem [Appkern](https://github.com/HalloWelt42/appkern): Anmeldung mit dem Kellerwolke-Konto, KI nur über
die Leitstelle, gestartet vom Stellwerk oder als Container.

## Schnittstelle

| Weg | Was |
|---|---|
| `POST /api/v1/vorlesen/strom` | `{"text": ...}` (bis 100.000 Zeichen); Antwort NDJSON, je Zeile `satz` (`nr`, `text`, `von_zeichen`, `bis_zeichen`, `dauer_ms`, `ton` als Base64-WAV), am Ende `ende`, bei einem Abbruch mittendrin `fehler`. Was vor dem ersten Satz scheitert, ist eine Antwort mit Grund. Bricht der Leser ab, wird nichts mehr gesprochen |
| `GET /api/v1/stimmen` | Katalog des Sprechdienstes, freigegebene eigene Stimmen (`privat:<Kennung>`) und die Sprachen |
| `GET /api/v1/verlauf` | laufende und die jüngsten Vorlesungen (`ab`, `anzahl`) |

Apps rufen Vorlesen nicht von Hand, sondern über den Baustein `appkern.vorlesen` (Feld `vorlesen_adresse`, Weg
`/api/v1/vorlesen` für den Vorleser der Oberfläche): mit ihrem App-Schlüssel der Kellerwolke und im Auftrag der Person.

## Einrichten

```bash
./einrichten.sh
```

Legt die Python-Umgebung an, holt die Pakete der Oberfläche und baut sie. Danach im Stellwerk starten (Eintrag
`stellwerk.toml`) und `http://127.0.0.1:8671` öffnen: die erste Einrichtung fragt nach der Adresse der
Kellerwolke und dem App-Schlüssel (in der Kellerwolke unter Einstellungen, Zugänge). Alles Weitere unter Einstellungen.

## Entwickeln

| Teil | Befehl |
|---|---|
| Backend | `cd backend && .venv/bin/uvicorn app.main:app --port 8671 --reload` |
| Oberfläche | `cd frontend && npm run dev` (Port 9671, leitet `/api` ans Backend) |
| Tests | `cd backend && .venv/bin/python -m pytest` |
| Symbole | `python3 tools/symbole.py` nach einer Änderung an `frontend/public/symbol.svg` |
| Fassung | `tools/version.sh minor` für eine neue Fähigkeit; jeder Commit zählt sonst selbst hoch |
| Appkern | `tools/appkern.sh` hebt Oberfläche und Backend auf denselben neuesten Commit |
| Ausrollen | `tools/ausrollen.sh` (Angaben in `deploy/ausrollen.toml`) |

Der Verbundtest (`tests/test_verbund.py`) spricht mit einer echten Kellerwolke und braucht `backend/.env.test` (nicht
im Repo) mit `KELLERWOLKE_ADRESSE`, `KELLERWOLKE_SCHLUESSEL`, `KELLERWOLKE_KENNUNG`, `KELLERWOLKE_PASSWORT`: ein eigener
Zugang nur für Tests, nicht der der Entwicklungsinstanz. Aufräumen und Zurückziehen der Aktionen kommen aus
`appkern.testen`.

## Prüfungen

Vor jedem Commit (Hook in `tools/git-hooks`, eingerichtet von `einrichten.sh`): Fassung hochzählen, nur gerade
Zeichen, Stil ohne `!important`, ohne einseitige Streifen und ohne Regeln auf Klassen der Schale. Beim Ausrollen: Tests,
gleicher Appkern in Oberfläche und Backend, Fassungen, HTTP/2, deckende Symbole. Von Hand vor dem Vorzeigen:
`docs/ABNAHME.md`.

## Aufbau

| Ort | Inhalt |
|---|---|
| `backend/app/main.py` | baut die App auf dem Gerüst |
| `backend/app/einstellungen.py` | eigene Einstellungen (dazu kommen Kellerwolke, Leitstelle, Konten) |
| `backend/app/vorlesen.py` | Text teilen, Satz für Satz sprechen lassen, Strom und Verlauf |
| `backend/app/sprechdienst.py` | Sprech- und Klondienst über die Leitstelle |
| `backend/app/stimmen.py` | eigene Stimmen aus der Vertonung, Probe im Zwischenspeicher |
| `backend/app/verlauf.py` | Verlauf der Vorlesungen |
| `backend/app/modell.py` | Verträge (Anfrage, Zeilen des Stroms, Verlauf, Stimmen) |
| `backend/app/api.py` | Endpunkte |
| `frontend/src/App.svelte` | Bereiche der App in der gemeinsamen Schale |
| `frontend/src/seiten/` | Vorlesen (Stimme, Tempo, Probe) und Verlauf |

---

## Lizenz

**Nicht-kommerzielle Nutzung** - Siehe [LICENSE](LICENSE)

Erlaubt: Private Nutzung, Installation, persönliche Anpassungen, Teilen mit Quellenangabe

Verboten: Kommerzielle Nutzung, Verkauf, Einbindung in kommerzielle Produkte

---

## Unterstützen

Vorlesen ist ein privates Hobby-Projekt. Kein Tracking, keine Werbung, keine Kompromisse.

Wenn dir das Projekt gefällt, kannst du ihm einen Stern geben - oder direkt hier:

[![Ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/HalloWelt42)

**Crypto:**

| Coin | Adresse |
|------|---------|
| BTC | `bc1qnd599khdkv3v3npmj9ufxzf6h4fzanny2acwqr` |
| DOGE | `DL7tuiYCqm3xQjMDXChdxeQxqUGMACn1ZV` |
| ETH | `0x8A28fc47bFFFA03C8f685fa0836E2dBe1CA14F27` |

Copyright (c) 2026 HalloWelt42
