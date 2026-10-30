"""Vorlesen gegen eine nachgestellte Kellerwolke und Leitstelle: einrichten, anmelden, vorlesen Satz für Satz (über die
Leitstelle beim Sprechdienst, Stimme und Tempo aus den Einstellungen), Ablehnung vor dem ersten Satz als Antwort,
Abbruch mitten im Strom als Zeile, eine andere App mit ihrem Schlüssel im Auftrag der Person, Verlauf und Stimmen."""

import asyncio
import base64
import io
import json
import wave
from pathlib import Path

import httpx
import pytest

from app.main import app_bauen

DIENST = "/v1/dienste/klangwerk-sprechen"
KLONEN = "/v1/dienste/klangwerk-klonen"
EIGENE = "11111111-2222-3333-4444-555555555555"      # die Vertonung gibt sie Vorlesen frei
GESPERRT = "99999999-2222-3333-4444-555555555555"    # private Stimme, nicht freigegeben


def wav(dauer_s: float, rate: int = 24000) -> bytes:
    puffer = io.BytesIO()
    with wave.open(puffer, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"\0\0" * int(dauer_s * rate))
    return puffer.getvalue()


class Welt:
    """Kellerwolke mit zwei Sitzungen (probe, anna über die App Pinnwand) und eine Leitstelle mit dem Sprechdienst."""

    def __init__(self) -> None:
        self.gesprochen: list[dict] = []
        self.koepfe: list[httpx.Headers] = []
        self.katalog_rufe = 0
        self.geklont: list[dict] = []
        self.proben_rufe = 0

    def __call__(self, request: httpx.Request) -> httpx.Response:
        pfad = request.url.path
        if request.url.host == "kw.test":
            return self.kellerwolke(request, pfad)
        if request.url.host == "ls.test":
            return self.leitstelle(request, pfad)
        if request.url.host == "vt.test":
            return self.vertonung(request, pfad)
        return httpx.Response(404, json={"detail": "nicht da"})

    @staticmethod
    def kellerwolke(request: httpx.Request, pfad: str) -> httpx.Response:
        benutzer = {"id": "1", "name": "probe", "rolle": "mitglied", "aktiv": True}
        if pfad == "/api/v1/ablage/ich":
            schluessel = request.headers.get("authorization", "")
            if schluessel == "Bearer kw_app_x":
                return httpx.Response(200, json={"app": "Vorlesen", "konto": "probe", "rechte": []})
            if schluessel == "Bearer kw_app_pinnwand":
                return httpx.Response(200, json={"app": "Pinnwand", "konto": "probe", "rechte": []})
            return httpx.Response(401, json={"detail": "unbekannt"})
        if pfad == "/api/v1/auth/login":
            if json.loads(request.content)["passwort"] != "geheim":
                return httpx.Response(401, json={"detail": "Anmeldung fehlgeschlagen"})
            return httpx.Response(200, json={"token": "t1", "benutzer": benutzer})
        if pfad == "/api/v1/auth/status":
            sitzung = request.headers.get("x-kellerwolke-sitzung")
            if sitzung == "t1":
                return httpx.Response(200, json={"angemeldet": True, "benutzer": benutzer, "app": "Vorlesen"})
            if sitzung == "t-pinnwand":
                return httpx.Response(200, json={"angemeldet": True, "benutzer": benutzer, "app": "Pinnwand"})
            return httpx.Response(200, json={"angemeldet": False, "benutzer": None})
        return httpx.Response(404, json={"detail": "nicht da"})

    def leitstelle(self, request: httpx.Request, pfad: str) -> httpx.Response:
        self.koepfe.append(request.headers)
        if pfad == "/v1/models":
            return httpx.Response(200, json={"data": [
                {"id": "klangwerk-sprechen", "x-leitstelle": {"name": "Klangwerk Sprechen", "faehigkeiten": ["stimme"]}}]})
        if pfad == f"{DIENST}/tts/voices":
            self.katalog_rufe += 1
            return httpx.Response(200, json={"speakers": ["serena", "aiden", "uncle_fu"], "languages": ["german", "english"]})
        if pfad == f"{KLONEN}/tts/clone":
            inhalt = request.content.decode("latin-1")
            self.geklont.append({"modus": "icl" if 'name="modus"\r\n\r\nicl' in inhalt else "abdruck",
                                 "probe": "PROBE-WAV" in inhalt})
            return httpx.Response(200, json={"filename": "klon_1.wav", "duration": 1.0})
        if pfad == f"{KLONEN}/tts/audio/klon_1.wav":
            return httpx.Response(200, content=wav(1.0), headers={"content-type": "audio/wav"})
        if pfad == f"{DIENST}/v1/audio/speech":
            koerper = json.loads(request.content)
            if "Kaputt" in koerper["input"]:
                return httpx.Response(503, json={"error": {"code": "dienst_weg", "message": "Dienst klangwerk-sprechen startet"}})
            self.gesprochen.append(koerper)
            return httpx.Response(200, content=wav(0.05 * len(koerper["input"])), headers={"content-type": "audio/wav"})
        return httpx.Response(404, json={"detail": "nicht da"})


    def vertonung(self, request: httpx.Request, pfad: str) -> httpx.Response:
        """Die Vertonung, so weit Vorlesen sie fragt: nur die freigegebene eigene Stimme, mit Probe und Text."""
        if pfad == "/api/v1/app":
            return httpx.Response(200, json={"fassung": "0.20.0"})
        if request.headers.get("authorization") != "Bearer kw_app_x":
            return httpx.Response(401, json={"detail": "Anmeldung fehlt"})
        if pfad == "/api/v1/stimmen" and request.url.params.get("bereich") == "privat":
            return httpx.Response(200, json=[{"id": EIGENE, "name": "Meine Stimme", "bereich": "privat"}])
        if pfad == f"/api/v1/stimmen/{EIGENE}":
            return httpx.Response(200, json={"id": EIGENE, "name": "Meine Stimme", "bereich": "privat",
                                             "angaben": {"name": "Meine Stimme", "bereich": "privat", "sprache": "de",
                                                         "referenztext": "Das ist meine Probe."}})
        if pfad == f"/api/v1/inhalt/stimmen/{EIGENE}/probe":
            self.proben_rufe += 1
            return httpx.Response(200, content=b"RIFF-PROBE-WAV", headers={"content-type": "audio/wav"})
        if GESPERRT in pfad:
            return httpx.Response(403, json={"detail": "Private Stimmen sind dieser App nicht erlaubt"})
        return httpx.Response(404, json={"detail": "nicht da"})


@pytest.fixture
async def umgebung(tmp_path: Path):
    welt = Welt()
    app = app_bauen(tmp_path / "daten", transport=httpx.MockTransport(welt))
    geruest = app.state.geruest
    await geruest.starten()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        yield app, welt, c
    await geruest.stoppen()


async def einrichten(c: httpx.AsyncClient, app) -> dict[str, str]:
    r = await c.post("/api/v1/einrichtung", json={"kellerwolke_adresse": "http://kw.test", "kellerwolke_schluessel": "kw_app_x"})
    assert r.json()["besitzer"] == "probe"
    await app.state.geruest.einstellungen.aendern({"leitstelle_adresse": "http://ls.test", "leitstelle_schluessel": "ls_x"})
    return {"X-Kellerwolke-Sitzung": (await c.post("/api/v1/anmeldung", json={"kennung": "probe", "passwort": "geheim"})).json()["token"]}


def zeilen(r: httpx.Response) -> list[dict]:
    return [json.loads(z) for z in r.text.splitlines() if z.strip()]


async def verlauf_abwarten(c, h, anzahl: int) -> dict:
    for _ in range(200):
        v = (await c.get("/api/v1/verlauf", headers=h)).json()
        if len(v["eintraege"]) >= anzahl:
            return v
        await asyncio.sleep(0.01)
    pytest.fail("Verlauf wurde nicht geschrieben")


async def test_vorlesen_satz_fuer_satz(umgebung):
    app, welt, c = umgebung
    h = await einrichten(c, app)
    assert (await c.post("/api/v1/vorlesen/strom", json={"text": "Hallo."})).status_code == 401
    text = "Am 12. September kam Anna. Sie las vor!\n\nDann war Ruhe"
    r = await c.post("/api/v1/vorlesen/strom", headers=h, json={"text": text})
    assert r.status_code == 200 and r.headers["content-type"].startswith("application/x-ndjson")
    z = zeilen(r)
    assert [x["art"] for x in z] == ["satz", "satz", "satz", "ende"]
    assert [x["text"] for x in z[:3]] == ["Am 12. September kam Anna.", "Sie las vor!", "Dann war Ruhe"]
    assert [text[x["von_zeichen"]:x["bis_zeichen"]] for x in z[:3]] == [x["text"] for x in z[:3]]
    assert z[0]["dauer_ms"] == 1300 and base64.b64decode(z[0]["ton"])[:4] == b"RIFF"
    assert z[3] == {"art": "ende", "saetze": 3, "dauer_ms": sum(x["dauer_ms"] for x in z[:3])}
    # Stimme, Sprache und Tempo aus den Einstellungen; eine Arbeit für alle Sätze, nur über die Leitstelle
    assert {(g["voice"], g["language"], g["speed"]) for g in welt.gesprochen} == {("serena", "german", 1.0)}
    arbeiten = {k.get("x-leitstelle-arbeit") for k in welt.koepfe if k.get("x-leitstelle-arbeit")}
    assert len(arbeiten) == 1
    v = await verlauf_abwarten(c, h, 1)
    e = v["eintraege"][0]
    assert (e["wer"], e["app"], e["saetze"], e["zustand"], e["zeichen"]) == ("probe", None, 3, "fertig", len(text))
    assert e["anfang"].startswith("Am 12. September") and e["erster_ms"] is not None and v["laufend"] == []


async def test_stimme_tempo_einstellungen_und_probe(umgebung):
    app, welt, c = umgebung
    h = await einrichten(c, app)
    r = await c.patch("/api/v1/einstellungen", headers=h, json={"werte": {"stimme": "aiden", "tempo": 1.2}})
    assert r.status_code == 200
    await c.post("/api/v1/vorlesen/strom", headers=h, json={"text": "Eins."})
    assert (welt.gesprochen[-1]["voice"], welt.gesprochen[-1]["speed"]) == ("aiden", 1.2)
    # Probehören mit einer anderen Katalogstimme; was nicht im Katalog steht, gibt es nicht
    await c.post("/api/v1/vorlesen/strom", headers=h, json={"text": "Zwei.", "stimme": "uncle_fu", "tempo": 0.8})
    assert (welt.gesprochen[-1]["voice"], welt.gesprochen[-1]["speed"]) == ("uncle_fu", 0.8)
    r = await c.post("/api/v1/vorlesen/strom", headers=h, json={"text": "Drei.", "stimme": "zeit_stimme"})
    assert r.status_code == 400 and "nicht im Katalog" in r.json()["detail"]
    stimmen = (await c.get("/api/v1/stimmen", headers=h)).json()
    assert [s["titel"] for s in stimmen["stimmen"]] == ["Aiden", "Serena", "Uncle Fu"] and stimmen["sprachen"]["german"] == "Deutsch"
    angebot = (await c.get("/api/v1/einstellungen/angebot/stimme", headers=h)).json()
    assert [o["wert"] for o in angebot["optionen"]] == ["aiden", "serena", "uncle_fu"] and not angebot["eigener_wert"]
    assert welt.katalog_rufe == 1                                   # der Katalog wird eine Weile gemerkt


async def test_ablehnung_vorher_und_fehler_mittendrin(umgebung):
    app, welt, c = umgebung
    h = await einrichten(c, app)
    r = await c.post("/api/v1/vorlesen/strom", headers=h, json={"text": " ... - "})
    assert r.status_code == 400 and "nichts vorzulesen" in r.json()["detail"]
    r = await c.post("/api/v1/vorlesen/strom", headers=h, json={"text": "Kaputt gleich am Anfang."})
    assert r.status_code == 503 and "startet" in r.json()["detail"]
    r = await c.post("/api/v1/vorlesen/strom", headers=h, json={"text": "Erst gut. Dann Kaputt. Nie mehr."})
    z = zeilen(r)
    assert [x["art"] for x in z] == ["satz", "fehler"] and "startet" in z[1]["meldung"]
    v = await verlauf_abwarten(c, h, 2)
    assert [e["zustand"] for e in v["eintraege"]] == ["fehler", "fehler"]


async def test_andere_app_im_auftrag_der_person(umgebung):
    app, welt, c = umgebung
    await einrichten(c, app)
    h = {"Authorization": "Bearer kw_app_pinnwand", "X-Kellerwolke-Sitzung": "t-pinnwand"}
    r = await c.post("/api/v1/vorlesen/strom", headers=h, json={"text": "Von der Pinnwand."})
    assert [x["art"] for x in zeilen(r)] == ["satz", "ende"]
    v = await verlauf_abwarten(c, {"Authorization": "Bearer kw_app_pinnwand"}, 1)
    assert (v["eintraege"][0]["wer"], v["eintraege"][0]["app"]) == ("probe", "Pinnwand")


async def test_ohne_leitstelle(umgebung):
    app, welt, c = umgebung
    r = await c.post("/api/v1/einrichtung", json={"kellerwolke_adresse": "http://kw.test", "kellerwolke_schluessel": "kw_app_x"})
    assert r.status_code == 200
    h = {"X-Kellerwolke-Sitzung": (await c.post("/api/v1/anmeldung", json={"kennung": "probe", "passwort": "geheim"})).json()["token"]}
    r = await c.post("/api/v1/vorlesen/strom", headers=h, json={"text": "Hallo."})
    assert r.status_code == 503 and "Leitstelle" in r.json()["detail"]


async def test_eigene_stimme_ueber_die_vertonung(umgebung):
    app, welt, c = umgebung
    h = await einrichten(c, app)
    # ohne Vertonung nur der Katalog
    assert all(s["art"] == "katalog" for s in (await c.get("/api/v1/stimmen", headers=h)).json()["stimmen"])
    await app.state.geruest.einstellungen.aendern({"vertonung_adresse": "http://vt.test"})
    stimmen = (await c.get("/api/v1/stimmen", headers=h)).json()["stimmen"]
    assert {"name": f"privat:{EIGENE}", "titel": "Meine Stimme", "art": "eigen"} in stimmen
    angebot = (await c.get("/api/v1/einstellungen/angebot/stimme", headers=h)).json()
    assert f"privat:{EIGENE}" in [o["wert"] for o in angebot["optionen"]]
    r = await c.patch("/api/v1/einstellungen", headers=h, json={"werte": {"stimme": f"privat:{EIGENE}"}})
    assert r.status_code == 200
    for text in ("Eins. Zwei.", "Drei."):
        z = zeilen(await c.post("/api/v1/vorlesen/strom", headers=h, json={"text": text}))
        assert z[-1]["art"] == "ende"
    # gesprochen hat der Klondienst mit Probe und Text (deutsch: icl); die Probe kam einmal für alle Sätze
    assert len(welt.geklont) == 3 and all(g["probe"] and g["modus"] == "icl" for g in welt.geklont)
    assert welt.proben_rufe == 1 and welt.gesprochen == []
    # englisch gesprochen: nur der Abdruck
    await c.post("/api/v1/vorlesen/strom", headers=h, json={"text": "Hello.", "sprache": "english"})
    assert welt.geklont[-1]["modus"] == "abdruck"
    # nicht freigegeben: abgelehnt, bevor etwas spricht
    r = await c.post("/api/v1/vorlesen/strom", headers=h, json={"text": "Hallo.", "stimme": f"privat:{GESPERRT}"})
    assert r.status_code == 403 and "nicht frei" in r.json()["detail"]
    v = await verlauf_abwarten(c, h, 3)
    assert v["eintraege"][0]["stimme"] == "Meine Stimme"
