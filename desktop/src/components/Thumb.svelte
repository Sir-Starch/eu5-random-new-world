<script lang="ts" module>
  // A world's picture in the library, fetched once per version of the file.
  import { app } from "../lib/app.svelte";

  const cache = new Map<string, Promise<string>>();
</script>

<script lang="ts">
  let { id, version, alt = "" }: { id: string; version: string; alt?: string } = $props();
  let source = $state("");

  $effect(() => {
    const key = `${id}|${version}`;
    if (!version) {
      source = "";
      return;
    }
    let found = cache.get(key);
    if (!found) {
      found = app.call<string>("thumbnail", { id }).then((url) => url ?? "");
      cache.set(key, found);
    }
    void found.then((url) => {
      if (`${id}|${version}` === key) source = url;
    });
  });
</script>

{#if source}
  <img src={source} {alt} draggable="false" />
{:else}
  <span class="blank" aria-hidden="true"></span>
{/if}

<style>
  img,
  .blank {
    display: block;
    width: 100%;
    height: 100%;
    object-fit: cover;
    border-radius: inherit;
  }
  .blank {
    background:
      repeating-linear-gradient(135deg, transparent 0 6px, var(--line) 6px 7px),
      var(--field);
  }
</style>
