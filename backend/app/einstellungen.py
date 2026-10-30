"""Einstellungen von Vorlesen. Kellerwolke, Leitstelle und weitere Konten bringt das Gerüst mit; hier kommen Stimme,
Sprache und Tempo dazu, die für alle Apps gelten, die über Vorlesen sprechen lassen (gewählt wird hier, nicht in den
Apps). Die Seite Einstellungen der Oberfläche entsteht daraus von selbst."""

from typing import Literal

from pydantic import Field

from appkern.app import Grundeinstellungen

SPRECHEN = {"gruppe": "Sprechen"}
VERLAUF = {"gruppe": "Verlauf"}

#: Sprachen des Sprechmodells (Namen, wie der Sprechdienst sie erwartet) mit ihrem deutschen Namen
SPRACHEN = {"german": "Deutsch", "english": "Englisch", "french": "Französisch", "spanish": "Spanisch",
            "italian": "Italienisch", "portuguese": "Portugiesisch", "russian": "Russisch", "japanese": "Japanisch",
            "korean": "Koreanisch", "chinese": "Chinesisch"}
Sprache = Literal["german", "english", "french", "spanish", "italian", "portuguese", "russian", "japanese", "korean",
                  "chinese"]


class AppEinstellungen(Grundeinstellungen):
    dienst_sprechen: str = Field("klangwerk-sprechen", title="Sprechdienst", json_schema_extra=SPRECHEN,
                                 description="Dienst der Leitstelle, der spricht (Fähigkeit stimme). Das Modell läuft "
                                             "dort, nie in dieser App.")
    stimme: str = Field("serena", title="Stimme", json_schema_extra=SPRECHEN,
                        description="Feste Stimme aus dem Katalog des Sprechdienstes. Geklonte Stimmen gibt es auf "
                                    "diesem Weg nicht.")
    sprache: Sprache = Field("german", title="Sprache", json_schema_extra={**SPRECHEN, "beschriftungen": SPRACHEN},
                             description="In dieser Sprache spricht die Stimme; die Texte sollten in ihr geschrieben sein.")
    tempo: float = Field(1.0, ge=0.5, le=2.0, title="Tempo", json_schema_extra={**SPRECHEN, "schritt": 0.05},
                         description="1 ist das gewohnte Tempo; kleiner liest langsamer, größer schneller.")
    verlauf_behalten: int = Field(500, ge=10, le=10_000, title="Verlauf behalten",
                                  json_schema_extra={**VERLAUF, "einheit": "Einträge"},
                                  description="So viele Vorlesungen bleiben im Verlauf (wann, wer, wie lang, wie es "
                                              "ausging); ältere fallen weg.")
