<script lang="ts">
  // A place a record names, as a small button that pins its location on the map.
  import Icon from "../Icon.svelte";

  let { name, onclick }: { name: string; onclick: () => void } = $props();
</script>

<button class="hx-place" title={name} {onclick}><Icon name="pin" size={12} /><span>{name}</span></button>
