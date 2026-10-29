<script lang="ts">
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
    display: inline-flex;
    flex-wrap: wrap;
    gap: 3px;
    padding: 3px;
    border-radius: 11px;
    background: var(--bg-2);
    border: 1px solid var(--line);
  }
  button {
    min-height: 30px;
    padding: 0 14px;
    border: 0;
    border-radius: 8px;
    background: transparent;
    color: var(--text-2);
    font: 550 13px var(--font);
    cursor: pointer;
    transition: all var(--speed) var(--ease);
    white-space: nowrap;
  }
  button:hover:not(:disabled):not(.on) {
    background: var(--hover);
    color: var(--text);
  }
  button.on {
    background: var(--panel-3);
    color: var(--text);
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.25), inset 0 0 0 1px var(--line-2);
  }
  button:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
</style>
