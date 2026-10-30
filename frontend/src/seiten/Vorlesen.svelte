<script lang="ts">
  // Vorlesen: oben gleich die Probe (HELF-67, Nutzer: "damit man selber gleich schneller testen kann"), darunter Stimme,
  // Sprache und Tempo als Vorgabe für alle Apps ohne eigene Vorlesestimme (dieselben Felder wie unter Einstellungen,
  // Sprechen). Die Probe spricht mit dem, was gerade gewählt ist, auch ungespeichert. Gespielt wird mit dem
  // Vorleser des Appkerns (Satz für Satz, mit Vorlauf); der laufende Satz steht unter dem Text.
  import { Auswahl, einstellungen, einstellungenLaden, einstellungenSpeichern, einstellungenVerwerfen, einstellungSetzen,
           einstellungsWert, hole, seitenFehler, VorleseKnopf, vorleser } from "appkern-oberflaeche";

  interface Stimmen { stimmen: { name: string; titel: string; art: "katalog" | "eigen" }[]; sprachen: Record<string, string>; stand: string }

  const FELDER = ["stimme", "sprache", "tempo"];
  const BEISPIEL = "Guten Tag. Hier spricht die App Vorlesen. Jeder Satz kommt einzeln an, darum beginnt der Ton sofort. "
    + "Am 30. Oktober um 14:30 Uhr zeigte das Thermometer 12,5 Grad.";

  let text = $state(BEISPIEL);
  let fehler = $state("");
  let meldung = $state("");
  let katalog = $state<Stimmen | null>(null);
  $effect(() => {
    void einstellungenLaden().then(() => (fehler = "")).catch((f) => (fehler = seitenFehler(f)));
    void hole<Stimmen>("/stimmen").then((s) => (katalog = s)).catch((f) => (fehler = seitenFehler(f)));
  });
  const stimme = $derived(String(einstellungsWert("stimme") ?? ""));
  const sprache = $derived(String(einstellungsWert("sprache") ?? "german"));
  const tempo = $derived(Number(einstellungsWert("tempo") ?? 1));
  const stimmen = $derived([{ wert: "", titel: "Vorgabe des Sprechdienstes", hinweis: "die Stimme ab Werk" },
    ...(katalog?.stimmen ?? []).map((s) => ({ wert: s.name, titel: s.titel, hinweis: s.art === "eigen" ? "eigene Stimme" : "Katalog" }))]);
  const sprachen = $derived(Object.entries(katalog?.sprachen ?? {}).map(([wert, titel]) => ({ wert, titel })));
  const offen = $derived(FELDER.filter((n) => n in einstellungen.entwurf).length);
  /** Die Probe spricht mit der Wahl, wie sie gerade auf der Seite steht (auch ungespeichert) */
  const probe = $derived({ stimme, sprache, tempo });
  const liest = $derived(vorleser.kennung === "probe");

  async function speichern(): Promise<void> {
    try {
      const n = await einstellungenSpeichern();
      meldung = `${n} ${n === 1 ? "Einstellung" : "Einstellungen"} gespeichert; sie gelten ab jetzt für alle Apps.`;
    } catch (f) {
      meldung = `Nicht gespeichert: ${seitenFehler(f) || "die App antwortet nicht"}`;
    }
  }
</script>

<div class="seiten-kopf"><h1>Vorlesen</h1></div>
<div class="rollfeld">
  <div class="karte">
    <h2><i class="fa-solid fa-headphones"></i>Probe</h2>
    <p class="karte-unter">Ein eigener Text oder der Beispielsatz, mit der Stimme, die unten gewählt ist; ein zweites Tippen hält an.</p>
    <textarea class="vl-text" rows="3" bind:value={text} aria-label="Text für die Probe"></textarea>
    <div class="knopfzeile vl-probe">
      <VorleseKnopf kennung="probe" text={() => text} pfad="/vorlesen/strom" daten={probe} immer beschriftung="Probe vorlesen"
                    titel="Den Text mit der gewählten Stimme vorlesen" />
      {#if text !== BEISPIEL}<button class="knopf ohne" onclick={() => (text = BEISPIEL)}>Beispiel</button>{/if}
    </div>
    {#if liest}
      <p class="vl-satz" aria-live="polite">
        {#if vorleser.wartet}<i class="fa-solid fa-hourglass-half"></i>Der erste Satz wird gesprochen ...
        {:else if vorleser.satz}<i class="fa-solid fa-volume-high"></i>{vorleser.satz.text}{/if}
      </p>
    {/if}
    {#if vorleser.fehler && !liest}<div class="fehlertext">{vorleser.fehler}</div>{/if}
  </div>
  <div class="karte">
    <h2><i class="fa-solid fa-sliders"></i>Stimme und Tempo</h2>
    <p class="karte-unter">So klingt das Vorlesen in allen Apps, die keine eigene Vorlesestimme gewählt haben. Zur Wahl stehen die festen
      Stimmen des Sprechdienstes und die eigenen, die die Vertonung für Vorlesen freigibt.</p>
    {#if fehler}<div class="fehlertext">{fehler}</div>{/if}
    <div class="feld">
      <div class="was"><div class="name">Stimme</div>
        <div class="beschreibung">{katalog?.stand || "Feste Stimme aus dem Katalog oder freigegebene eigene Stimme."}</div></div>
      <Auswahl wert={stimme} optionen={stimmen} symbol="fa-user" titel="Stimme wählen" onwahl={(w) => einstellungSetzen("stimme", w)} />
    </div>
    <div class="feld">
      <div class="was"><div class="name">Sprache</div>
        <div class="beschreibung">In dieser Sprache spricht die Stimme; die Texte sollten in ihr geschrieben sein.</div></div>
      <Auswahl wert={sprache} optionen={sprachen} symbol="fa-language" titel="Sprache wählen" onwahl={(w) => einstellungSetzen("sprache", w)} />
    </div>
    <div class="feld">
      <div class="was"><div class="name">Tempo <span class="vl-wert">{tempo.toFixed(2).replace(".", ",")}</span></div>
        <div class="beschreibung">1 ist das gewohnte Tempo; kleiner liest langsamer, größer schneller.</div></div>
      <input class="vl-tempo" type="range" min="0.5" max="2" step="0.05" value={tempo} aria-label="Tempo"
             oninput={(e) => einstellungSetzen("tempo", Number(e.currentTarget.value))} />
    </div>
    {#if offen}
      <div class="vl-leiste" role="status">
        <span><b>{offen}</b> {offen === 1 ? "Änderung" : "Änderungen"} noch nicht gespeichert; die Probe spricht schon so</span>
        <span class="knopfzeile">
          <button class="knopf ohne" onclick={einstellungenVerwerfen}>Verwerfen</button>
          <button class="knopf primaer" onclick={speichern}><i class="fa-solid fa-floppy-disk"></i>Speichern</button>
        </span>
      </div>
    {/if}
    {#if meldung}<p class="karte-unter" role="status">{meldung}</p>{/if}
  </div>

</div>

<style>
  .vl-text { width: 100%; min-height: 96px; padding: 10px 12px; border-radius: var(--r2); border: 1px solid var(--rand);
             background: var(--flaeche); color: var(--text); font: inherit; line-height: 1.5; resize: vertical; }
  .vl-text:focus { outline: none; border-color: var(--akzent); box-shadow: 0 0 0 3px var(--akzent-weich); }
  .vl-probe { margin: 10px 0 14px; }
  .vl-satz { display: flex; gap: 10px; align-items: baseline; margin: 0 0 14px; color: var(--text-2); }
  .vl-satz i { color: var(--akzent); }
  .vl-wert { font-weight: 400; color: var(--text-2); }
  .vl-tempo { width: 100%; accent-color: var(--akzent); }
  .vl-leiste { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; justify-content: space-between;
               padding: 10px 0 14px; border-top: 1px solid var(--rand); }
</style>
