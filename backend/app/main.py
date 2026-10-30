"""Vorlesen: liest Text vor, Satz für Satz. Die eine Stelle für Sprachausgabe im Verbund: Apps schicken Text (über den
Baustein `appkern.vorlesen`), Vorlesen teilt ihn an Satzgrenzen und liefert den Ton Satz für Satz als Strom. Das
Sprechmodell bleibt isoliert im Klangwerk, erreicht nur über die Leitstelle; Stimme und Tempo wählt man hier.

    uvicorn app.main:app --port 8671
"""

import os
from pathlib import Path

import httpx
from fastapi import FastAPI

from appkern.app import Geruest
from appkern.einstellungen import Angebot, Option

from .api import router
from .einstellungen import AppEinstellungen
from .fassung import FASSUNG, WURZEL
from .sprechdienst import Sprechdienst
from .stimmen import Stimmenquelle
from .verlauf import Verlaufsbuch
from .vorlesen import Vorleser


def stimmen_angebot(vorleser: Vorleser):
    """Auswahl für das Feld der Stimme: der Katalog und die freigegebenen eigenen Stimmen, kein eigener Wert."""

    async def anbieter() -> Angebot:
        stimmen, stand = await vorleser.stimmenwahl()
        optionen = [Option(wert=s.name, titel=s.titel, hinweis="eigene Stimme" if s.art == "eigen" else "Katalog")
                    for s in stimmen]
        return Angebot(optionen=optionen, eigener_wert=False, stand=stand or f"{len(optionen)} Stimmen")

    return anbieter


def app_bauen(daten: Path, transport: httpx.AsyncBaseTransport | None = None) -> FastAPI:
    """`transport` nur für Tests (Kellerwolke und Leitstelle nachgestellt)."""
    geruest = Geruest(name="Vorlesen", kennung="vorlesen", rolle="liest Text vor, Satz für Satz", symbol="fa-volume-high",
                      farbe="#1f9e78", fassung=FASSUNG, daten=daten, einstellungen=AppEinstellungen,
                      oberflaeche=WURZEL / "frontend" / "dist", transport=transport)
    stand = lambda: geruest.einstellungen.stand  # noqa: E731
    dienst = Sprechdienst(lambda: geruest.leitstelle, lambda: stand().dienst_sprechen, lambda: stand().dienst_klonen)
    quelle = Stimmenquelle(geruest, lambda: stand().vertonung_adresse)
    verlauf = Verlaufsbuch(geruest.db, lambda: stand().verlauf_behalten)
    geruest.begleiter_anmelden(verlauf)
    geruest.einstellungen.anbieten("dienst_sprechen", geruest.leitstelle_angebot("stimme"))
    vorleser = Vorleser(dienst, verlauf, stand, quelle)
    geruest.einstellungen.anbieten("dienst_klonen", geruest.leitstelle_angebot("stimme_klonen"))
    geruest.einstellungen.anbieten("stimme", stimmen_angebot(vorleser))
    geruest.einstellungen.anbieten("vertonung_adresse", geruest.verbund.angebot("Vertonung", "vertonung", quelle.adresse))
    geruest.verbund.anmelden("Vertonung", quelle.adresse)
    app = geruest.fastapi()
    app.state.geruest = geruest
    app.state.vorleser = vorleser
    app.include_router(router(geruest, vorleser))
    geruest.oberflaeche_ausliefern(app)
    return app


def daten_ordner() -> Path:
    """Wo die App ihre Daten hält: `VORLESEN_DATEN` (im Container /app/daten), sonst daten/ im Repo."""
    return Path(os.environ.get("VORLESEN_DATEN") or WURZEL / "daten")


app = app_bauen(daten_ordner())
