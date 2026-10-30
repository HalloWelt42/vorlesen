<script lang="ts">
  // Verlauf: was gerade vorgelesen wird und die letzten Vorlesungen, je mit Zeit, wer (Person oder App), Länge, wie
  // schnell der erste Ton kam und wie es ausging. Läuft etwas, fragt die Seite alle 2 Sekunden nach, sonst alle 15;
  // ältere Einträge seitenweise.
  import { hole, seitenFehler, seitenSignal, wann } from "appkern-oberflaeche";

  type Zustand = "laeuft" | "fertig" | "abgebrochen" | "fehler";
  interface Vorlesung {
    id: string; beginn: string; wer: string; app: string | null; anfang: string; zeichen: number; saetze: number;
    ton_ms: number; erster_ms: number | null; dauer_ms: number; stimme: string; tempo: number; zustand: Zustand; meldung: string;
  }
  interface Verlauf { laufend: Vorlesung[]; eintraege: Vorlesung[]; weitere: boolean }

  const SEITE = 50;
  const STAND: Record<Zustand, { text: string; klasse: string; symbol: string }> = {
    laeuft: { text: "liest", klasse: "laeuft", symbol: "fa-volume-high" },
    fertig: { text: "fertig", klasse: "fertig", symbol: "fa-check" },
    abgebrochen: { text: "angehalten", klasse: "offen", symbol: "fa-stop" },
    fehler: { text: "Fehler", klasse: "warn", symbol: "fa-triangle-exclamation" },
  };
  const signal = seitenSignal();
  let verlauf = $state<Verlauf | null>(null);
  let ab = $state(0);
  let fehler = $state("");

  async function laden(): Promise<void> {
    try {
      verlauf = await hole<Verlauf>(`/verlauf?ab=${ab}&anzahl=${SEITE}`, { signal });
      fehler = "";
    } catch (f) {
      fehler = seitenFehler(f);
    }
  }

  $effect(() => {
    let uhr: ReturnType<typeof setTimeout> | undefined;
    const weiter = async (): Promise<void> => {
      await laden();
      if (!signal.aborted) uhr = setTimeout(weiter, verlauf?.laufend.length ? 2000 : 15000);
    };
    void weiter();
    return () => clearTimeout(uhr);
  });

  function sekunden(ms: number): string {
    const s = ms / 1000;
    if (s < 60) return `${s.toFixed(1).replace(".", ",")} s`;
    return `${Math.floor(s / 60)} Min ${Math.round(s % 60)} s`;
  }

  function meta(v: Vorlesung): string {
    const teile = [wann(v.beginn), v.app && v.app !== v.wer ? `${v.wer} über ${v.app}` : v.wer,
      `${v.saetze} ${v.saetze === 1 ? "Satz" : "Sätze"}`, `Ton ${sekunden(v.ton_ms)}`];
    if (v.erster_ms !== null) teile.push(`erster Ton nach ${sekunden(v.erster_ms)}`);
    teile.push(`${v.stimme}, Tempo ${v.tempo.toFixed(2).replace(".", ",")}`);
    return teile.join(" · ");
  }

  function blaettern(n: number): void {
    ab = Math.max(0, ab + n);
    void laden();
  }
</script>

{#snippet zeile(v: Vorlesung)}
  {@const s = STAND[v.zustand]}
  <div class="zeile vl-zeile" title={v.meldung || undefined}>
    <span class="art"><i class="fa-solid {s.symbol}"></i></span>
    <div class="vl-inhalt">
      <div class="name">{v.anfang}</div>
      <div class="meta">{meta(v)}</div>
      {#if v.meldung}<div class="meta vl-meldung">{v.meldung}</div>{/if}
    </div>
    <span class="stand-pille {s.klasse}">{#if v.zustand === "laeuft"}<i class="fa-solid fa-circle-notch fa-spin"></i> {/if}{s.text}</span>
  </div>
{/snippet}

<div class="seiten-kopf"><h1>Verlauf</h1></div>
<div class="rollfeld">
  {#if fehler}<div class="fehlertext">{fehler}</div>{/if}
  {#if verlauf?.laufend.length}
    <h2 class="vl-abschnitt">Gerade</h2>
    {#each verlauf.laufend as v (v.id)}{@render zeile(v)}{/each}
    <h2 class="vl-abschnitt">Zuletzt</h2>
  {/if}
  {#each verlauf?.eintraege ?? [] as v (v.id)}
    {@render zeile(v)}
  {:else}
    <p class="leer">{verlauf ? "Noch nichts vorgelesen. Eine Probe gibt es unter Vorlesen." : "Lädt ..."}</p>
  {/each}
  {#if verlauf && (ab > 0 || verlauf.weitere)}
    <div class="knopfzeile vl-seiten">
      <button class="knopf" disabled={ab === 0} onclick={() => blaettern(-SEITE)}><i class="fa-solid fa-chevron-left"></i>Neuere</button>
      <button class="knopf" disabled={!verlauf.weitere} onclick={() => blaettern(SEITE)}>Ältere<i class="fa-solid fa-chevron-right"></i></button>
    </div>
  {/if}
</div>

<style>
  .vl-zeile { grid-template-columns: 44px minmax(0, 1fr) auto; cursor: default; }
  .vl-inhalt { min-width: 0; }
  .vl-inhalt .meta { white-space: normal; }
  .vl-meldung { color: var(--warn); }
  .vl-abschnitt { font-size: var(--klein); color: var(--text-2); margin: 6px 0 8px; }
  .vl-seiten { justify-content: center; margin: 8px 0 16px; }
</style>
