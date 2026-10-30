<script lang="ts" generics="T extends string">
  // The tabs of a pane, drawn in its header.
  let {
    options,
    value,
    label,
    onchange,
  }: {
    options: { value: T; label: string; count?: number | string }[];
    value: T;
    label: string;
    onchange: (value: T) => void;
  } = $props();
</script>

<div class="tabs" role="tablist" aria-label={label}>
  {#each options as option (option.value)}
    <button
      class="tab"
      class:on={value === option.value}
      role="tab"
      aria-selected={value === option.value}
      title={option.label}
      onclick={() => onchange(option.value)}
    >
      {option.label}{#if option.count}<span class="count num">{option.count}</span>{/if}
    </button>
  {/each}
</div>
