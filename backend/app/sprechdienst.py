"""Die Sprechdienste des Klangwerks, erreicht nur über die Leitstelle (`/v1/dienste/<dienst>/...`). Feste Stimmen:
`POST /v1/audio/speech` beim Sprechdienst spricht einen Satz und liefert WAV (PCM 16 Bit, mono), `GET /tts/voices` nennt
den Katalog. Eigene Stimmen: `POST /tts/clone` beim Klondienst mit der Probe der Stimme (aus der Vertonung, siehe
stimmen.py), die Datei holt man bei derselben Instanz ab. Die Modelle bleiben dort; diese App wählt nur Dienst, Stimme,
Sprache und Tempo."""

from __future__ import annotations

import io
import time
import wave
from collections.abc import Callable

from appkern.leitstelle import Leitstelle, LeitstellenFehler
from appkern.leitstelle.arbeit import LAUFENDE_ARBEIT

from .stimmen import Referenz

#: so lange gilt der geholte Katalog
KATALOG_GILT_S = 600
#: Sprachen des Modells in der Kurzform der Vertonung (Sprache einer Probe)
KURZ = {"german": "de", "english": "en", "french": "fr", "spanish": "es", "italian": "it", "portuguese": "pt",
        "russian": "ru", "japanese": "ja", "korean": "ko", "chinese": "zh"}


def modus(referenz: Referenz, sprache: str) -> str:
    """Wie eine eigene Stimme spricht: mit Referenztext (icl) übernimmt das Modell Klang und Sprechweise der Probe;
    spricht sie eine andere Sprache als ihre Probe, brächte das deren Akzent mit, dann nur der Stimmabdruck (wie die
    Vertonung, Messung K1 18.10.2026). Ohne Referenztext bleibt nur der Abdruck."""
    return "icl" if referenz.text.strip() and KURZ.get(sprache, sprache) == referenz.sprache else "abdruck"


class KeineLeitstelle(LeitstellenFehler):
    """Die App ist noch nicht mit einer Leitstelle verbunden."""

    status = 503


def dauer_ms(wav: bytes) -> int:
    """Länge einer WAV in Millisekunden; 0, wenn der Kopf nicht lesbar ist."""
    try:
        with wave.open(io.BytesIO(wav)) as w:
            return round(w.getnframes() * 1000 / w.getframerate())
    except (wave.Error, EOFError, ZeroDivisionError):
        return 0


class Sprechdienst:
    def __init__(self, leitstelle: Callable[[], Leitstelle | None], dienst: Callable[[], str],
                 klondienst: Callable[[], str] = lambda: "klangwerk-klonen", uhr: Callable[[], float] = time.monotonic) -> None:
        self._ls = leitstelle
        self._dienst = dienst
        self._klondienst = klondienst
        self._uhr = uhr
        self._katalog: tuple[float, str, list[str], list[str]] | None = None

    def _leitstelle(self) -> Leitstelle:
        ls = self._ls()
        if ls is None:
            raise KeineLeitstelle("Keine Leitstelle eingerichtet (Einstellungen, Verbindungen)")
        return ls

    async def katalog(self) -> tuple[list[str], list[str]]:
        """(Stimmen, Sprachen) des Sprechdienstes, eine Weile gemerkt."""
        dienst = self._dienst()
        if self._katalog and self._katalog[1] == dienst and self._uhr() - self._katalog[0] < KATALOG_GILT_S:
            return self._katalog[2], self._katalog[3]
        antwort = await self._leitstelle().dienst(dienst).json("GET", "/tts/voices", titel="Stimmen des Katalogs")
        stimmen = sorted(str(s) for s in antwort.get("speakers") or [])
        sprachen = [str(s) for s in antwort.get("languages") or []]
        self._katalog = (self._uhr(), dienst, stimmen, sprachen)
        return stimmen, sprachen

    def gemerkte_stimmen(self) -> list[str] | None:
        """Der zuletzt geholte Katalog, ohne zu fragen (None, wenn keiner da ist)."""
        return self._katalog[2] if self._katalog else None

    async def sprechen(self, text: str, *, stimme: str, sprache: str, tempo: float, arbeit: str) -> bytes:
        """Ein Stück Text als WAV. `arbeit` hält alle Sätze einer Vorlesung als eine Arbeit bei der Leitstelle zusammen
        (sie lässt das Modell einer begonnenen Arbeit für andere stehen)."""
        marke = LAUFENDE_ARBEIT.set(arbeit)
        try:
            antwort = await self._leitstelle().dienst(self._dienst()).anfrage(
                "POST", "/v1/audio/speech", titel="Vorlesen", prioritaet="hoch",
                json={"input": text, "voice": stimme, "language": sprache, "speed": tempo, "response_format": "wav"})
        finally:
            LAUFENDE_ARBEIT.reset(marke)
        return antwort.content

    async def klonen(self, text: str, *, referenz: Referenz, sprache: str, tempo: float, arbeit: str) -> bytes:
        """Ein Stück Text mit einer eigenen Stimme als WAV; die Probe geht mit (aus dem Zwischenspeicher)."""
        marke = LAUFENDE_ARBEIT.set(arbeit)
        try:
            dienst = self._leitstelle().dienst(self._klondienst())
            async with dienst.gebunden():         # die Datei liegt bei der Instanz, die gesprochen hat
                antwort = await dienst.json(
                    "POST", "/tts/clone", titel="Vorlesen", prioritaet="hoch",
                    data={"text": text, "ref_text": referenz.text, "language": sprache, "speed": str(tempo),
                          "modus": modus(referenz, sprache)},
                    files={"ref_audio": ("referenz.wav", referenz.ton, "audio/wav")})
                datei = (await dienst.anfrage("GET", f"/tts/audio/{antwort['filename']}", titel="Vorlesen")).content
        finally:
            LAUFENDE_ARBEIT.reset(marke)
        return datei
