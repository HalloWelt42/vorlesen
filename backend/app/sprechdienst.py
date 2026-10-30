"""Der Sprechdienst des Klangwerks, erreicht nur über die Leitstelle (`/v1/dienste/<dienst>/...`): `POST
/v1/audio/speech` spricht einen Satz und liefert WAV (PCM 16 Bit, mono), `GET /tts/voices` nennt den Katalog fester
Stimmen. Das Modell bleibt dort; diese App wählt nur Dienst, Stimme, Sprache und Tempo. Klonstimmen sind auf diesem Weg
nicht erreichbar (der Dienst kennt nur seinen Katalog)."""

from __future__ import annotations

import io
import time
import wave
from collections.abc import Callable

from appkern.leitstelle import Leitstelle, LeitstellenFehler
from appkern.leitstelle.arbeit import LAUFENDE_ARBEIT

#: so lange gilt der geholte Katalog
KATALOG_GILT_S = 600


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
                 uhr: Callable[[], float] = time.monotonic) -> None:
        self._ls = leitstelle
        self._dienst = dienst
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
