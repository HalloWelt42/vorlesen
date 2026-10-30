"""Eigene Stimmen: sie liegen in der Kellerwolke und gehören der Vertonung; dort steht auch, wer sie nutzen darf
(Einstellung "Private Stimmen für": `vorlesen` gibt alle frei, `vorlesen:<Kennung>` genau eine). Vorlesen fragt die
Vertonung mit seinem eigenen App-Schlüssel und bekommt nur, was sie Vorlesen freigibt; gesammelte fremde Stimmen fragt
es nie ab. Eine Wahrheit: dieselbe Quelle und Erlaubnisliste wie Vertonung und TubeVault.

Die Probe einer Stimme (Referenz mit Text und Sprache) wird einmal geholt und eine Weile gemerkt, damit der erste Ton
schnell kommt; danach fragt Vorlesen wieder, so gilt eine zurückgenommene Freigabe bald auch hier."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass

from appkern.app import Geruest
from appkern.verbund import ABFRAGE, VerbundFehler

#: so lange gilt eine geholte Probe samt Freigabe
REFERENZ_GILT_S = 1800


class NichtFreigegeben(Exception):
    """Die Stimme gibt es nicht oder die Vertonung gibt sie Vorlesen nicht frei; `meldung` in Worten."""

    def __init__(self, meldung: str) -> None:
        super().__init__(meldung)
        self.meldung = meldung


@dataclass(frozen=True)
class Eigene:
    id: str
    name: str


@dataclass(frozen=True)
class Referenz:
    id: str
    name: str
    ton: bytes             # die Probe als Datei, wie die Vertonung sie hält (WAV)
    text: str              # was in der Probe gesprochen wird (leer: unbekannt)
    sprache: str           # Sprache der Probe, kurz (de, en ...)


class Stimmenquelle:
    def __init__(self, geruest: Geruest, adresse: Callable[[], str], uhr: Callable[[], float] = time.monotonic) -> None:
        self.g = geruest
        self._adresse = adresse
        self._uhr = uhr
        self._gemerkt: dict[str, tuple[float, Referenz]] = {}

    def adresse(self) -> str:
        return self._adresse().strip().rstrip("/")

    async def eigene(self) -> list[Eigene]:
        """Die eigenen Stimmen, die die Vertonung Vorlesen freigibt (leer, wenn keine oder keine Vertonung)."""
        if not self.adresse():
            return []
        try:
            antwort = await self.g.verbund.anfrage("GET", self.adresse(), "/api/v1/stimmen", timeout=ABFRAGE,
                                                   params={"bereich": "privat"})
        except VerbundFehler as f:
            if f.status in (401, 403):
                return []                       # Vorlesen steht nicht auf der Erlaubnisliste: keine eigenen Stimmen
            raise
        return [Eigene(id=str(s["id"]), name=str(s["name"])) for s in antwort.json() if s.get("bereich") == "privat"]

    async def referenz(self, stimme_id: str) -> Referenz:
        """Probe, Text und Sprache einer freigegebenen eigenen Stimme; einmal geholt, eine Weile gemerkt."""
        gemerkt = self._gemerkt.get(stimme_id)
        if gemerkt and self._uhr() - gemerkt[0] < REFERENZ_GILT_S:
            return gemerkt[1]
        if not self.adresse():
            raise NichtFreigegeben("Eigene Stimmen gibt es erst mit der Adresse der Vertonung (Einstellungen, Verbindungen)")
        try:
            s = (await self.g.verbund.anfrage("GET", self.adresse(), f"/api/v1/stimmen/{stimme_id}", timeout=ABFRAGE)).json()
            if s.get("bereich") != "privat":
                raise NichtFreigegeben("Das ist keine eigene Stimme")
            ton = (await self.g.verbund.anfrage("GET", self.adresse(), f"/api/v1/inhalt/stimmen/{stimme_id}/probe")).content
        except VerbundFehler as f:
            self._gemerkt.pop(stimme_id, None)
            if f.status in (401, 403, 404, 422):
                raise NichtFreigegeben("Diese Stimme gibt die Vertonung für Vorlesen nicht frei (Vertonung, Einstellungen, "
                                       "Stimmen, Private Stimmen für)") from f
            raise
        angaben = s.get("angaben") or {}
        r = Referenz(id=stimme_id, name=str(s.get("name") or "eigene Stimme"), ton=ton,
                     text=str(angaben.get("referenztext") or ""), sprache=str(angaben.get("sprache") or "de"))
        self._gemerkt[stimme_id] = (self._uhr(), r)
        return r
