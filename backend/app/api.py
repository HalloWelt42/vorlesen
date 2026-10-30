"""Endpunkte von Vorlesen (alle hinter der Anmeldung: Menschen in dieser Oberfläche und andere Apps mit ihrem
App-Schlüssel, auf Wunsch im Auftrag der Person).

- `POST /api/v1/vorlesen/strom`: der Text Satz für Satz als NDJSON (`application/x-ndjson`), je Zeile eine `StromZeile`.
  Was vor dem ersten Satz scheitert, ist eine Antwort mit Grund; bricht der Leser ab, wird nichts mehr gesprochen.
- `GET /api/v1/stimmen`: Katalog des Sprechdienstes, die freigegebenen eigenen Stimmen und die Sprachen.
- `GET /api/v1/verlauf`: laufende und die jüngsten Vorlesungen, seitenweise."""

from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse, StreamingResponse

from appkern.anmeldung import Konto
from appkern.app import Geruest

from .einstellungen import SPRACHEN
from .modell import Stimmen, StromZeile, Verlauf, Vorleseanfrage
from .vorlesen import Abgelehnt, Vorleser


class NdjsonAntwort(StreamingResponse, JSONResponse):
    """Strom aus JSON-Zeilen; als `JSONResponse` gekennzeichnet, damit das Schema den Vertrag der Zeilen zeigt."""
    media_type = "application/x-ndjson"


def router(geruest: Geruest, vorleser: Vorleser) -> APIRouter:
    r = APIRouter(prefix="/api/v1", tags=["vorlesen"], dependencies=[geruest.pflicht])

    @r.post("/vorlesen/strom", response_class=NdjsonAntwort,
            responses={200: {"model": StromZeile, "description": "Je Zeile ein JSON-Objekt (`art`: satz, ende, fehler)"}})
    async def vorlesen_strom(a: Vorleseanfrage, konto: Konto = geruest.pflicht) -> NdjsonAntwort:
        try:
            auftrag = await vorleser.vorbereiten(a)
            zeilen = vorleser.strom(a, auftrag, konto)
            erste = await anext(zeilen)                  # scheitert der erste Satz, ist das noch eine Antwort mit Grund
        except Abgelehnt as f:
            raise HTTPException(f.status, f.meldung) from f

        async def alles() -> AsyncIterator[bytes]:
            yield erste
            async for z in zeilen:
                yield z

        return NdjsonAntwort(alles(), headers={"Cache-Control": "no-cache"})

    @r.get("/stimmen", response_model=Stimmen)
    async def stimmen() -> Stimmen:
        """Feste Stimmen des Katalogs und die eigenen, die die Vertonung Vorlesen freigibt."""
        liste, stand = await vorleser.stimmenwahl()
        return Stimmen(stimmen=liste, sprachen=SPRACHEN, stand=stand)

    @r.get("/verlauf", response_model=Verlauf)
    async def verlauf(ab: int = Query(0, ge=0), anzahl: int = Query(50, ge=1, le=200)) -> Verlauf:
        eintraege, weitere = await vorleser.verlauf.eintraege(ab=ab, anzahl=anzahl)
        return Verlauf(laufend=vorleser.verlauf.laufend(), eintraege=eintraege, weitere=weitere)

    return r
