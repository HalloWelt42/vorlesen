"""Vorlesen: Text an Satzgrenzen teilen (`appkern.saetze`), jeden Satz beim Sprechdienst sprechen lassen und als
Zeile des Stroms liefern, sobald er da ist; so beginnt die Wiedergabe nach dem ersten Satz. Was vor dem ersten Satz
scheitert, wird zu einer Antwort mit Grund (die Ausnahme geht hinaus); danach kommt eine Zeile `fehler`. Bricht der
Leser ab, endet die Arbeit: es wird kein weiterer Satz bestellt. Jede Vorlesung steht im Verlauf."""

from __future__ import annotations

import base64
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass

from appkern.anmeldung import Konto
from appkern.leitstelle import LeitstellenFehler
from appkern.saetze import hat_worte, saetze, stuecke

from .einstellungen import AppEinstellungen
from .modell import StromEnde, StromFehler, StromSatz, Vorleseanfrage
from .sprechdienst import Sprechdienst, dauer_ms
from .verlauf import Laufend, Verlaufsbuch


class Abgelehnt(Exception):
    """Vorlesen geht nicht, bevor etwas gesprochen ist; `status` für die Antwort."""

    def __init__(self, meldung: str, status: int = 400) -> None:
        super().__init__(meldung)
        self.meldung = meldung
        self.status = status


@dataclass(frozen=True)
class Stueck:
    """Ein Stück Text für einen Aufruf des Sprechdienstes und die Lage seines Satzes im Eingabetext."""
    text: str
    von: int
    bis: int


@dataclass(frozen=True)
class Auftrag:
    stuecke: list[Stueck]
    stimme: str
    sprache: str
    tempo: float


def zerlegen(text: str) -> list[Stueck]:
    """Sätze, zu lange in Stücke zerlegt; ohne Worte fällt ein Stück weg."""
    return [Stueck(s, satz.von, satz.bis) for satz in saetze(text) for s in stuecke(satz.text) if hat_worte(s)]


def wer(konto: Konto) -> tuple[str, str | None]:
    """(wer, rufende App) für den Verlauf."""
    if konto.im_auftrag:
        return konto.name, konto.im_auftrag
    if konto.app:
        return konto.app, konto.app
    return konto.name, None


def grund(f: LeitstellenFehler) -> str:
    return f"Der Sprechdienst kann gerade nicht: {f.meldung}"


def zeile(z: StromSatz | StromEnde | StromFehler) -> bytes:
    return z.model_dump_json().encode() + b"\n"


class Vorleser:
    def __init__(self, sprechdienst: Sprechdienst, verlauf: Verlaufsbuch, einstellungen: Callable[[], AppEinstellungen]) -> None:
        self.dienst = sprechdienst
        self.verlauf = verlauf
        self._e = einstellungen

    async def vorbereiten(self, a: Vorleseanfrage) -> Auftrag:
        """Teilt den Text und legt Stimme, Sprache und Tempo fest; abgelehnt mit Grund, bevor etwas spricht. Eine Stimme aus der
        Anfrage (Probehören) muss im Katalog stehen, sobald er bekannt ist."""
        e = self._e()
        teile = zerlegen(a.text)
        if not teile:
            raise Abgelehnt("Es gibt nichts vorzulesen")
        stimme = a.stimme or e.stimme
        if a.stimme:
            katalog = self.dienst.gemerkte_stimmen()
            if katalog is None:
                try:
                    katalog, _ = await self.dienst.katalog()
                except LeitstellenFehler:
                    katalog = None                        # nicht prüfbar: der Sprechdienst kennt ohnehin nur seinen Katalog
            if katalog is not None and a.stimme not in katalog:
                raise Abgelehnt(f"Die Stimme {a.stimme} steht nicht im Katalog des Sprechdienstes")
        return Auftrag(teile, stimme, a.sprache or e.sprache, a.tempo or e.tempo)

    async def strom(self, a: Vorleseanfrage, auftrag: Auftrag, konto: Konto) -> AsyncIterator[bytes]:
        name, app = wer(konto)
        lauf = self.verlauf.beginnen(wer=name, app=app, text=a.text, stimme=auftrag.stimme, tempo=auftrag.tempo)
        zustand, meldung = "abgebrochen", ""
        try:
            async for z in self._saetze(auftrag, lauf):
                yield z
            zustand = "fertig"
        except LeitstellenFehler as f:
            zustand, meldung = "fehler", grund(f)
            if not lauf.eintrag.saetze:
                raise Abgelehnt(meldung, 503 if f.status in (0, 503) else 502) from f
            yield zeile(StromFehler(meldung=meldung))
        finally:
            self.verlauf.abschliessen(lauf, zustand, meldung)       # ohne Warten: auch beim Abbruch

    async def _saetze(self, auftrag: Auftrag, lauf: Laufend) -> AsyncIterator[bytes]:
        nr, gesamt = 0, 0
        for s in auftrag.stuecke:
            wav = await self.dienst.sprechen(s.text, stimme=auftrag.stimme, sprache=auftrag.sprache, tempo=auftrag.tempo,
                                             arbeit=f"vorlesen-{lauf.eintrag.id}")
            ms = dauer_ms(wav)
            lauf.satz(ms)
            yield zeile(StromSatz(nr=nr, text=s.text, von_zeichen=s.von, bis_zeichen=s.bis, dauer_ms=ms,
                                  ton=base64.b64encode(wav).decode("ascii")))
            nr += 1
            gesamt += ms
        yield zeile(StromEnde(saetze=nr, dauer_ms=gesamt))
