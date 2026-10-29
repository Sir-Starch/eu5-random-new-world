<script lang="ts">
  let {
    checked,
    label,
    hint = "",
    disabled = false,
    onchange,
  }: {
    checked: boolean;
    label: string;
    hint?: string;
    disabled?: boolean;
    onchange: (value: boolean) => void;
  } = $props();
</script>

<label class="toggle" class:disabled>
  <span class="text">
    <span class="label">{label}</span>
    {#if hint}<span class="hint">{hint}</span>{/if}
  </span>
  <input
    type="checkbox"
    role="switch"
    {checked}
    {disabled}
    onchange={(event) => onchange((event.currentTarget as HTMLInputElement).checked)}
  />
  <span class="track" aria-hidden="true"><span class="thumb"></span></span>
</label>

<style>
  .toggle {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 16px;
    cursor: pointer;
    position: relative;
  }
  .toggle.disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
  .text {
    display: grid;
    gap: 3px;
  }
  .label {
    font-weight: 550;
  }
  .hint {
    color: var(--text-3);
    font-size: 12.5px;
    line-height: 1.45;
  }
  input {
    position: absolute;
    opacity: 0;
    pointer-events: none;
  }
  .track {
    flex: none;
    width: 40px;
    height: 23px;
    border-radius: 999px;
    background: var(--panel-3);
    border: 1px solid var(--line-2);
    position: relative;
    transition: background var(--speed) var(--ease), border-color var(--speed) var(--ease);
    margin-top: 1px;
  }
  .thumb {
    position: absolute;
    top: 2px;
    left: 2px;
    width: 17px;
    height: 17px;
    border-radius: 50%;
    background: var(--text-2);
    transition: transform var(--speed) var(--ease), background var(--speed) var(--ease);
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.3);
  }
  input:checked + .track {
    background: var(--accent);
    border-color: transparent;
  }
  input:checked + .track .thumb {
    transform: translateX(17px);
    background: var(--on-accent);
  }
  input:focus-visible + .track {
    outline: 2px solid var(--accent);
    outline-offset: 2px;
  }
</style>
