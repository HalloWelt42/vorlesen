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
from appkern.leitstelle import LeitstellenFehler

from .api import router, stimmtitel
from .einstellungen import AppEinstellungen
from .fassung import FASSUNG, WURZEL
from .sprechdienst import Sprechdienst
from .verlauf import Verlaufsbuch
from .vorlesen import Vorleser


def stimmen_angebot(dienst: Sprechdienst):
    """Auswahl für das Feld der Stimme: nur der Katalog des Sprechdienstes, kein eigener Wert."""

    async def anbieter() -> Angebot:
        try:
            namen, _ = await dienst.katalog()
        except LeitstellenFehler as f:
            return Angebot(optionen=[], eigener_wert=False, stand=f"Sprechdienst antwortet nicht: {f.meldung}")
        return Angebot(optionen=[Option(wert=n, titel=stimmtitel(n), hinweis="Katalog") for n in namen],
                       eigener_wert=False, stand=f"{len(namen)} Stimmen im Katalog")

    return anbieter


def app_bauen(daten: Path, transport: httpx.AsyncBaseTransport | None = None) -> FastAPI:
    """`transport` nur für Tests (Kellerwolke und Leitstelle nachgestellt)."""
    geruest = Geruest(name="Vorlesen", kennung="vorlesen", rolle="liest Text vor, Satz für Satz", symbol="fa-volume-high",
                      farbe="#1f9e78", fassung=FASSUNG, daten=daten, einstellungen=AppEinstellungen,
                      oberflaeche=WURZEL / "frontend" / "dist", transport=transport)
    stand = lambda: geruest.einstellungen.stand  # noqa: E731
    dienst = Sprechdienst(lambda: geruest.leitstelle, lambda: stand().dienst_sprechen)
    verlauf = Verlaufsbuch(geruest.db, lambda: stand().verlauf_behalten)
    geruest.begleiter_anmelden(verlauf)
    geruest.einstellungen.anbieten("dienst_sprechen", geruest.leitstelle_angebot("stimme"))
    geruest.einstellungen.anbieten("stimme", stimmen_angebot(dienst))
    vorleser = Vorleser(dienst, verlauf, stand)
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
