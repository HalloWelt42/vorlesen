<script lang="ts">
  // Die Bereiche von Vorlesen in der gemeinsamen Schale: Vorlesen (Stimme, Sprache, Tempo wählen und Probe hören) und
  // Verlauf (was gerade und zuletzt vorgelesen wurde). Alle weiteren Einstellungen und das Protokoll bringt die Schale.
  import { Schale, type Bereich } from "appkern-oberflaeche";
  import Verlauf from "./seiten/Verlauf.svelte";
  import Vorlesen from "./seiten/Vorlesen.svelte";

  const bereiche: Bereich[] = [
    { schluessel: "vorlesen", titel: "Vorlesen", symbol: "fa-volume-high", seite: Vorlesen, reiter: true,
      hinweis: "Stimme, Sprache und Tempo für alle Apps wählen und Probe hören" },
    { schluessel: "verlauf", titel: "Verlauf", symbol: "fa-clock-rotate-left", seite: Verlauf, reiter: true,
      hinweis: "Was gerade und zuletzt vorgelesen wurde, von wem und wie es ausging" },
  ];
</script>

<Schale {bereiche} fassung={__APP_FASSUNG__} />
