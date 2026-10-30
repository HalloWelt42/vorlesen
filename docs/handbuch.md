---
zweck: "Liest Text vor, Satz für Satz: die eine Stelle für Sprachausgabe aller Apps; Stimme und Tempo werden hier gewählt, das Sprechmodell bleibt im Klangwerk."
geraet: [pi]
abhaengigkeiten: [kellerwolke, leitstelle, klangwerk, appkern]
daten:
  - "Pi: `{{wurzel}}/daten/vorlesen.sqlite` (Einstellungen mit Stimme, Sprache und Tempo, Verlauf der Vorlesungen ohne den Text, nur sein Anfang, Protokoll)"
sicherung:
  - "nach der Regel des Appkerns eine Kopie von `vorlesen.sqlite` nach `{{wurzel}}/sicherungen`, wöchentlich und vor dem Ausrollen (nur, wenn die jüngste älter als 24 Stunden ist), nie ohne Änderung, höchstens drei Stände (Einstellungen, Sicherung)"
schluessel_orte:
  - "Pi: Einstellungen im Verzeichnis `vorlesen.sqlite`: App-Schlüssel der Kellerwolke, Schlüssel der Leitstelle (in der Oberfläche unter Einstellungen, verdeckt)"
  - "Pi: `{{wurzel}}/.env`, Modus 0600, für Werte, die nicht ins Repo gehören"
  - "Pi: `{{wurzel}}/zertifikate/`, Blattzertifikat mit Schlüssel aus der Hausstelle (vom Ausrollen)"
einrichten: einrichten.sh
stand: 54ec546
---

# Vorlesen

## Zweck

Vorlesen ist die eine Stelle für Sprachausgabe im Verbund. Eine App schickt Text (über den Baustein `appkern.vorlesen`
des [[Appkern]], mit ihrem App-Schlüssel und im Auftrag der Person), Vorlesen teilt ihn an Satzgrenzen und liefert
den Ton Satz für Satz als Strom; die Wiedergabe beginnt nach dem ersten Satz. Gesprochen wird nur vom Sprechdienst
des [[Klangwerk]] über die [[Leitstelle]]: das Modell bleibt dort isoliert und wird in keine App eingebaut.

Stimme, Sprache und Tempo wählt man hier (Seite Vorlesen, mit Probe vor dem Speichern); sie gelten für alle Apps. Zur
Wahl stehen nur die festen Stimmen aus dem Katalog des Sprechdienstes, geklonte Stimmen sind auf diesem Weg nicht
erreichbar. Der Verlauf zeigt, was gerade und zuletzt vorgelesen wurde, von wem und wie es ausging. Kunden sind etwa
die [[Pinnwand]] (Beschreibung, Kommentare, Tagesplan, Berichte); die [[Vertonung]] bleibt für Videos und lange Werke.

Auf dem Pi läuft sie als Compose-Projekt aus `compose.pi.yml` hinter ihrem Vorschaltdienst `vorne`. Adresse:
{{adresse}}.

## Was sie braucht

- Pi nach [[Grundlage Pi]] mit Docker; Mac nach [[Grundlage Mac]] für Entwicklung, Ausrollen und Hausstelle.
- [[Kellerwolke]]: Konto zum Anmelden und ein App-Schlüssel für Vorlesen. Apps, die vorlesen lassen, melden sich mit
  ihrem eigenen App-Schlüssel desselben Kontos an.
- [[Leitstelle]]: Anwendung "Vorlesen" mit der Fähigkeit stimme.
- [[Klangwerk]] am Mac mit dem Dienst sprechen (über den [[Maschinenraum]]).

## Neu einrichten

Zwei Wege. Aus der Sicherung: die jüngste Kopie von `vorlesen.sqlite` zurückspielen; dann sind Schlüssel, Stimme,
Tempo und Verlauf wie vorher. Frisch: leere Datenbank, erste Einrichtung mit neuem App-Schlüssel, Leitstelle unter
Einstellungen; Stimme und Tempo gelten ab Werk (Deutsch, Serena, Tempo 1).

### 1. Repo und Entwicklungsumgebung am Mac

```
git clone {{repo}} {{ordner}}
cd {{ordner}} && ./einrichten.sh
```

Python-Umgebung, Oberfläche, Appkern auf einen Commit, Git-Haken; das Ausrollen prüft mit dieser Umgebung. Der Eintrag
fürs Stellwerk (Entwicklung am Mac) liegt als `stellwerk.toml` im Repo und als Kopie unter
`~/Stellwerk/apps/vorlesen.toml`.

Probe: `test -f frontend/dist/index.html && backend/.venv/bin/python -c "import appkern"` endet ohne Fehler.

### 2. Ordner auf dem Pi

Auf dem Pi `mkdir -p {{wurzel}}/daten {{wurzel}}/sicherungen` (sonst legt Docker sie für root an). Aus der Sicherung
die jüngste Kopie als `{{wurzel}}/daten/vorlesen.sqlite` ablegen (Besitzer `pi`).

Probe: `stat -c %U {{wurzel}}/daten` meldet `pi`.

### 3. Ausrollen

Am Mac `tools/ausrollen.sh`: Tests, Appkern-Stand, Zertifikat, Bau, Start und Prüfung von Fassung, HTTP/2 und
Symbolen. Vorher läuft `handbuch freigabe` (Prüfung der Seite, Probelauf, Handbuch).

Probe: `curl -s --cacert "$(mkcert -CAROOT)/rootCA.pem" {{adresse}}/api/v1/app` meldet `"fassung": "{{fassung}}"`.

### 4. Erste Einrichtung

Aus der Sicherung entfällt sie. Frisch: in der [[Kellerwolke]] einen App-Schlüssel für Vorlesen anlegen, {{adresse}}
öffnen und mit dem Einrichtungscode aus `{{wurzel}}/daten/einrichtungscode` (auf dem Pi) die Adresse der Kellerwolke
und den Schlüssel eintragen; danach mit dem eigenen Kellerwolke-Konto anmelden.

Probe: `/api/v1/app` meldet `"einrichtung_noetig": false` und den Besitzer.

### 5. Leitstelle und Stimme

Aus der Sicherung stehen sie im Verzeichnis. Frisch: in der [[Leitstelle]] die Anwendung "Vorlesen" mit der Fähigkeit
stimme anlegen, ihren Schlüssel unter Einstellungen, Verbindungen eintragen und "Adresse dieser App" auf {{adresse}}
setzen. Unter Vorlesen Stimme, Sprache und Tempo wählen und eine Probe hören.

Probe: in der Fußleiste sind Kellerwolke und Leitstelle grün, und "Probe vorlesen" spricht hörbar; der Verlauf zeigt
die Probe als fertig.

### 6. Apps anschließen

In jeder App, die vorlesen soll, unter Einstellungen, Verbindungen das Feld "Vorlesen" auf {{adresse}} setzen (die
Auswahl bietet die App aus dem Verzeichnis an). Die [[Pinnwand]] bekommt die Adresse über ihre Umgebung beim
Ausrollen.

Probe: in der App steht Vorlesen in der Fußleiste grün, und ein Lautsprecher liest vor; im Verlauf hier steht die App.

## Sicherung und Rückspielen

Nach der Regel der Sicherung aus dem [[Appkern]] legt die App einmal je Woche, das Ausrollen vor dem Neustart (nur,
wenn die jüngste älter als 24 Stunden ist) eine stimmige Kopie von `vorlesen.sqlite` nach
`{{wurzel}}/sicherungen/vorlesen-<Zeit>.sqlite`; hat sich seit der jüngsten nichts geändert, entsteht keine, und
höchstens drei bleiben (Werte unter Einstellungen, Sicherung). Ton hält die App nie; er entsteht beim Vorlesen und geht
gleich an den Leser.

Zurückspielen: auf dem Pi im Ordner {{wurzel}} `docker compose -f compose.pi.yml stop vorlesen`, die Kopie als
`daten/vorlesen.sqlite` ablegen (alte `-wal` und `-shm` daneben entfernen), `docker compose -f compose.pi.yml start
vorlesen`. Probe wie in Schritt 3.

## Wenn etwas klemmt

- Kein Ton, Meldung "Der Sprechdienst kann gerade nicht": die Leitstelle meldet den Sprechdienst nicht (Klangwerk
  sprechen nicht gestartet, oder der Mac schläft); der erste Satz wartet, bis die Leitstelle ihn gestartet hat.
- Eine App zeigt keinen Lautsprecher: in ihren Einstellungen fehlt die Adresse von Vorlesen, oder sie steht in der
  Fußleiste rot (Fassung, Zertifikat, Schlüssel prüfen).
- "Die App Vorlesen lässt das nicht zu": der App-Schlüssel der rufenden App gehört nicht dem Konto, dem Vorlesen
  gehört, und es steht nicht unter Zugang, Weitere Konten.
- Die Stimme fehlt in der Auswahl: der Katalog kommt vom Sprechdienst; antwortet er nicht, ist die Auswahl leer, die
  gespeicherte Stimme gilt trotzdem.
