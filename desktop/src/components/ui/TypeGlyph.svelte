<script lang="ts">
  // A small picture of each world type: the shape of its land at a glance.
  let { kind }: { kind: string } = $props();

  const BLOBS: Record<string, string> = {
    supercontinent:
      "M14 22c4-8 14-12 24-10s14 0 20 4 8 12 4 18-2 12-10 14-16 4-24 0-14-6-16-12-2-10 2-14Z",
    continents:
      "M8 18c3-6 10-8 15-5s7 9 4 15-9 10-14 7-8-11-5-17Zm34 6c3-5 11-6 15-2s3 12-1 16-12 5-15 0-2-9 1-14Z",
    small_continents:
      "M10 14c2-4 8-5 10-1s0 9-4 10-8-5-6-9Zm28-2c3-3 8-2 9 2s-2 8-6 8-6-6-3-10ZM14 36c3-3 9-2 10 2s-3 8-7 7-6-6-3-9Zm28 2c3-4 9-3 10 1s-2 8-6 8-7-5-4-9Z",
    archipelago:
      "M10 16c2-3 6-3 7 0s-1 6-4 6-5-3-3-6Zm16-6c2-2 6-1 6 2s-3 5-5 4-3-4-1-6Zm18 4c2-3 7-2 7 1s-3 6-6 5-3-4-1-6ZM12 34c2-2 6-2 6 1s-2 5-5 4-3-3-1-5Zm18 2c3-3 8-2 8 2s-4 7-7 5-3-5-1-7Zm20-6c2-2 5-1 5 2s-2 4-4 4-3-4-1-6Z",
    islands:
      "M10 12a2 2 0 1 0 0 .1Zm12 8a2.5 2.5 0 1 0 0 .1Zm14-10a2 2 0 1 0 0 .1Zm12 12a2.5 2.5 0 1 0 0 .1ZM14 34a2.2 2.2 0 1 0 0 .1Zm14 6a2 2 0 1 0 0 .1Zm12-8a2.4 2.4 0 1 0 0 .1Zm14 8a2 2 0 1 0 0 .1ZM24 28a1.6 1.6 0 1 0 0 .1Zm28-14a1.6 1.6 0 1 0 0 .1Z",
  };
</script>

<svg viewBox="0 0 64 48" aria-hidden="true">
  <defs>
    <pattern id="waves-{kind}" width="8" height="6" patternUnits="userSpaceOnUse">
      <path d="M0 4q2-2 4 0t4 0" fill="none" stroke="currentColor" stroke-opacity="0.12" />
    </pattern>
  </defs>
  <rect width="64" height="48" rx="8" fill="url(#waves-{kind})" />
  {#if kind === "random"}
    <g fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round" stroke-linecap="round">
      <rect x="20" y="12" width="24" height="24" rx="5" class="land-stroke" />
      <circle cx="27" cy="19" r="1.6" fill="currentColor" />
      <circle cx="37" cy="29" r="1.6" fill="currentColor" />
      <circle cx="32" cy="24" r="1.6" fill="currentColor" />
    </g>
  {:else if kind === "chaos"}
    <g fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
      <path class="land-stroke" d="M32 8c10 0 16 7 16 15s-6 13-14 13-12-5-12-11 4-9 9-9 7 3 7 6-2 5-5 5" />
      <path d="m14 14 4 2m30 18 4 2M12 34l4-1m34-21 4-1" opacity="0.6" />
    </g>
  {:else}
    <path class="land" d={BLOBS[kind] ?? BLOBS.continents} />
  {/if}
</svg>

<style>
  svg {
    width: 100%;
    height: 100%;
    color: var(--sea);
  }
  .land {
    fill: color-mix(in srgb, var(--accent) 70%, var(--ok));
    stroke: color-mix(in srgb, var(--accent) 50%, #000);
    stroke-width: 0.8;
  }
  .land-stroke {
    stroke: var(--accent);
  }
</style>
