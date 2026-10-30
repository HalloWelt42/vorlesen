"""Verlauf: was vorgelesen wurde, von wem, wie lang, wie schnell der erste Ton kam und wie es ausging. Laufende
Vorlesungen stehen im Speicher (sie ändern sich je Satz), fertige in der Datenbank der App, die jüngsten
`verlauf_behalten`. Den Text selbst hält die App nicht, nur seinen Anfang zum Wiedererkennen.

Das Abschließen ist ein gewöhnlicher Aufruf ohne Warten: es kommt auch dann an, wenn der Strom abgebrochen wird (dann
darf im Aufräumen nichts mehr warten); geschrieben wird in einer eigenen Aufgabe."""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import Callable
from datetime import datetime

from appkern.app import Begleiter
from appkern.datenbank import Datenbank

from .modell import Vorlesung, Zustand

log = logging.getLogger("vorlesen")
ANFANG_ZEICHEN = 80
FELDER = ("id", "beginn", "wer", "app", "anfang", "zeichen", "saetze", "ton_ms", "erster_ms", "dauer_ms", "stimme", "tempo",
          "zustand", "meldung")
STUFEN = [
    """
    CREATE TABLE vorlesung (
        id         TEXT PRIMARY KEY,
        beginn     TEXT NOT NULL,
        wer        TEXT NOT NULL,
        app        TEXT,
        anfang     TEXT NOT NULL,
        zeichen    INTEGER NOT NULL,
        saetze     INTEGER NOT NULL,
        ton_ms     INTEGER NOT NULL,
        erster_ms  INTEGER,
        dauer_ms   INTEGER NOT NULL,
        stimme     TEXT NOT NULL,
        tempo      REAL NOT NULL,
        zustand    TEXT NOT NULL,
        meldung    TEXT NOT NULL
    );
    CREATE INDEX vorlesung_beginn ON vorlesung (beginn);
    """,
]


def anfang(text: str) -> str:
    kurz = " ".join(text.split())
    return kurz if len(kurz) <= ANFANG_ZEICHEN else kurz[:ANFANG_ZEICHEN - 3].rstrip() + "..."


class Laufend:
    """Eine Vorlesung, während sie läuft; misst ihre Zeiten selbst."""

    def __init__(self, eintrag: Vorlesung, uhr: Callable[[], float]) -> None:
        self.eintrag = eintrag
        self._uhr = uhr
        self._beginn = uhr()

    def satz(self, ton_ms: int) -> None:
        e = self.eintrag
        if e.erster_ms is None:
            e.erster_ms = round((self._uhr() - self._beginn) * 1000)
        e.saetze += 1
        e.ton_ms += ton_ms

    def ende(self, zustand: Zustand, meldung: str = "") -> Vorlesung:
        e = self.eintrag
        e.zustand, e.meldung = zustand, meldung
        e.dauer_ms = round((self._uhr() - self._beginn) * 1000)
        return e


class Verlaufsbuch(Begleiter):
    def __init__(self, db: Datenbank, behalten: Callable[[], int], uhr: Callable[[], float] | None = None) -> None:
        self.db = db
        self._behalten = behalten
        self._uhr = uhr or (lambda: asyncio.get_running_loop().time())
        self._laufend: dict[str, Laufend] = {}
        self._schreibt: set[asyncio.Task] = set()

    async def starten(self) -> None:
        await self.db.einrichten("vorlesen_verlauf", STUFEN)

    async def stoppen(self) -> None:
        if self._schreibt:
            await asyncio.gather(*self._schreibt, return_exceptions=True)

    def beginnen(self, *, wer: str, app: str | None, text: str, stimme: str, tempo: float) -> Laufend:
        e = Vorlesung(id=uuid.uuid4().hex, beginn=datetime.now().astimezone().isoformat(timespec="seconds"), wer=wer,
                      app=app, anfang=anfang(text), zeichen=len(text), stimme=stimme, tempo=tempo)
        lauf = Laufend(e, self._uhr)
        self._laufend[e.id] = lauf
        return lauf

    def abschliessen(self, lauf: Laufend, zustand: Zustand, meldung: str = "") -> None:
        """Ohne zu warten: aus dem Speicher nehmen und das Schreiben anstoßen."""
        e = lauf.ende(zustand, meldung)
        self._laufend.pop(e.id, None)
        aufgabe = asyncio.get_running_loop().create_task(self._schreiben(e), name=f"verlauf-{e.id}")
        self._schreibt.add(aufgabe)
        aufgabe.add_done_callback(self._schreibt.discard)

    async def _schreiben(self, e: Vorlesung) -> None:
        behalten = self._behalten()

        def arbeit(v) -> None:
            v.execute(f"INSERT INTO vorlesung ({', '.join(FELDER)}) VALUES ({', '.join('?' for _ in FELDER)})",
                      [getattr(e, f) for f in FELDER])
            v.execute("DELETE FROM vorlesung WHERE id NOT IN (SELECT id FROM vorlesung ORDER BY beginn DESC, rowid DESC "
                      "LIMIT ?)", (behalten,))

        try:
            await self.db.transaktion(arbeit)
        except Exception:  # noqa: BLE001 - der Verlauf darf das Vorlesen nie stören
            log.exception("Verlauf nicht geschrieben")

    def laufend(self) -> list[Vorlesung]:
        return sorted((l.eintrag.model_copy() for l in self._laufend.values()), key=lambda e: e.beginn, reverse=True)

    async def eintraege(self, *, ab: int = 0, anzahl: int = 50) -> tuple[list[Vorlesung], bool]:
        """Die Einträge, jüngste zuerst, ab dem `ab`-ten (seitenweise), und ob es ältere gibt."""
        zeilen = await self.db.zeilen(f"SELECT {', '.join(FELDER)} FROM vorlesung ORDER BY beginn DESC, rowid DESC "
                                      "LIMIT ? OFFSET ?", [anzahl + 1, ab])
        return [Vorlesung.model_validate(z) for z in zeilen[:anzahl]], len(zeilen) > anzahl
