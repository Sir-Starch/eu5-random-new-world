<script lang="ts">
  // Adjoining buttons of which one is chosen; a value of null chooses none (a custom value).
  let {
    options,
    value,
    disabled = false,
    label = "",
    onchange,
  }: {
    options: { value: string; label: string; title?: string }[];
    value: string | null;
    disabled?: boolean;
    label?: string;
    onchange: (value: string) => void;
  } = $props();
</script>

<div class="segmented" role="radiogroup" aria-label={label || undefined}>
  {#each options as option (option.value)}
    <button
      type="button"
      role="radio"
      aria-checked={value === option.value}
      class:on={value === option.value}
      title={option.title}
      {disabled}
      onclick={() => onchange(option.value)}
    >
      {option.label}
    </button>
  {/each}
</div>

<style>
  .segmented {
    display: flex;
    min-width: 0;
  }
  button {
    flex: 1 1 0;
    min-width: 0;
    height: 26px;
    padding: 0 8px;
    border: 1px solid var(--line-2);
    border-radius: 0;
    margin-left: -1px;
    background: var(--raised);
    color: var(--text);
    font: 400 12.5px var(--font);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  button:first-child {
    margin-left: 0;
    border-radius: var(--radius) 0 0 var(--radius);
  }
  button:last-child {
    border-radius: 0 var(--radius) var(--radius) 0;
  }
  button:hover:not(:disabled):not(.on) {
    background: var(--raised-hover);
  }
  button.on {
    position: relative;
    z-index: 1;
    background: var(--accent-soft);
    border-color: var(--accent);
    font-weight: 500;
  }
  button:focus-visible {
    z-index: 2;
  }
  button:disabled {
    opacity: 0.5;
  }
</style>
