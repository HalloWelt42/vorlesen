"""Verträge von Vorlesen: die Anfrage, die Zeilen des Stroms (NDJSON, unterschieden an `art`), der Verlauf und die
Stimmen. Die Modelle stehen im Schema der App; Apps lesen den Vertrag dort, der Appkern (`appkern.vorlesen`) reicht
die Zeilen unverändert an den Vorleser der Oberfläche."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from appkern.vorlesen import TEXT_HOECHSTENS

from .einstellungen import Sprache


class Vorleseanfrage(BaseModel):
    text: str = Field(min_length=1, max_length=TEXT_HOECHSTENS)
    #: nur zum Probehören in der Oberfläche: ohne gelten Stimme, Sprache und Tempo aus den Einstellungen
    stimme: str | None = Field(None, pattern=r"^([a-z][a-z_]{0,39}|privat:[0-9a-fA-F-]{36})$",
                               description="feste Stimme aus dem Katalog oder privat:<Kennung> einer freigegebenen eigenen")
    sprache: Sprache | None = None
    tempo: float | None = Field(None, ge=0.5, le=2.0)


class _Zeile(BaseModel):
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)   # `art` steht im Schema als Pflicht


class StromSatz(_Zeile):
    """Ein gesprochener Satz, sobald er fertig ist (ein zu langer Satz kommt in mehreren Stücken)."""
    art: Literal["satz"] = "satz"
    nr: int = Field(ge=0, description="Nummer, ab 0, ohne Lücken")
    text: str = Field(description="Was gesprochen wurde")
    von_zeichen: int = Field(ge=0, description="Lage des Satzes im Eingabetext in Zeichen (ab 0), zum Mitlesen")
    bis_zeichen: int = Field(ge=0, description="Ende im Eingabetext, ausschließlich")
    dauer_ms: int = Field(ge=0)
    ton: str = Field(description="Base64 einer WAV, PCM 16 Bit, mono, wie der Sprechdienst sie liefert")


class StromEnde(_Zeile):
    """Letzte Zeile, wenn alles gesprochen ist."""
    art: Literal["ende"] = "ende"
    saetze: int = Field(ge=0)
    dauer_ms: int = Field(ge=0, description="Summe der Sätze, ohne Pausen")


class StromFehler(_Zeile):
    """Letzte Zeile, wenn das Sprechen mitten im Strom scheitert."""
    art: Literal["fehler"] = "fehler"
    meldung: str


StromZeile = Annotated[StromSatz | StromEnde | StromFehler, Field(discriminator="art")]

Zustand = Literal["laeuft", "fertig", "abgebrochen", "fehler"]


class Vorlesung(BaseModel):
    """Eine Vorlesung im Verlauf: wer, wie viel, wie schnell der erste Ton kam und wie sie ausging."""
    id: str
    beginn: str = Field(description="Zeitpunkt (ISO 8601, Ortszeit mit Versatz)")
    wer: str = Field(description="Person oder App, die vorlesen ließ")
    app: str | None = Field(None, description="die rufende App; leer: diese Oberfläche")
    anfang: str = Field(description="die ersten Worte des Texts")
    zeichen: int
    saetze: int = 0
    ton_ms: int = 0
    erster_ms: int | None = Field(None, description="Wartezeit bis zum ersten Satz")
    dauer_ms: int = 0
    stimme: str = Field(description="Name der Stimme, wie man sie wählt")
    tempo: float
    zustand: Zustand = "laeuft"
    meldung: str = ""


class Verlauf(BaseModel):
    laufend: list[Vorlesung]
    eintraege: list[Vorlesung]
    weitere: bool = Field(description="es gibt ältere Einträge (seitenweise mit `ab`)")


class Stimme(BaseModel):
    name: str = Field(description="Wert für die Wahl: Name im Katalog oder privat:<Kennung>")
    titel: str
    art: Literal["katalog", "eigen"] = "katalog"


class Stimmen(BaseModel):
    stimmen: list[Stimme]
    sprachen: dict[str, str]
    stand: str = Field("", description="leer, wenn der Katalog geholt ist; sonst warum nicht")
