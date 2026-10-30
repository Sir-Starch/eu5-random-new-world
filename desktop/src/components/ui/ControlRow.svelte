<script lang="ts">
  import { app, t } from "../../lib/app.svelte";
  import type { ControlInfo, ValueState } from "../../lib/types";
  import Icon from "../Icon.svelte";

  let {
    control,
    value,
    disabled = false,
  }: { control: ControlInfo; value: ValueState; disabled?: boolean } = $props();

  let dragging = $state<number | null>(null);
  let typed = $state<string | null>(null);
  let last = 0;
  let pending: ReturnType<typeof setTimeout> | null = null;

  const position = $derived(dragging ?? value.position);
  const share = $derived((position / control.steps) * 100);
  const defaultShare = $derived((value.default_position / control.steps) * 100);
  const shown = $derived(typed ?? value.shown.toFixed(control.decimals));
  const about = $derived(t(`control.${control.key}.about`));
  const fallback = $derived(`${value.default.toFixed(control.decimals)}${control.unit ? ` ${control.unit}` : ""}`);

  function send(next: number): void {
    const now = performance.now();
    if (pending) clearTimeout(pending);
    const go = (): void => {
      last = performance.now();
      void app.call("set_position", { key: control.key, position: next });
    };
    if (now - last > 90) go();
    else pending = setTimeout(go, 90);
  }

  function slid(event: Event): void {
    dragging = Number((event.currentTarget as HTMLInputElement).value);
    send(dragging);
  }

  async function settled(): Promise<void> {
    if (dragging === null) return;
    if (pending) clearTimeout(pending);
    await app.call("set_position", { key: control.key, position: dragging });
    dragging = null;
  }

  async function commit(): Promise<void> {
    if (typed === null) return;
    const number = Number(typed.replace(",", "."));
    typed = null;
    if (Number.isFinite(number)) await app.call("set_value", { key: control.key, value: number });
  }
</script>

<div class="label" class:changed={value.changed} title={about}>{t(`control.${control.key}`)}</div>
<div class="control" class:changed={value.changed}>
  <div class="slider" style:--share={`${share}%`} style:--default={`${defaultShare}%`}>
    <span class="tick" title={fallback}></span>
    <input
      type="range"
      min="0"
      max={control.steps}
      step="1"
      value={position}
      {disabled}
      title={about}
      aria-label={t(`control.${control.key}`)}
      oninput={slid}
      onchange={settled}
      onpointerup={settled}
    />
  </div>
  <label class="number">
    <input
      class="input mono"
      inputmode="decimal"
      value={shown}
      {disabled}
      aria-label={t(`control.${control.key}`)}
      oninput={(event) => (typed = (event.currentTarget as HTMLInputElement).value)}
      onblur={commit}
      onkeydown={(event) => event.key === "Enter" && (event.currentTarget as HTMLInputElement).blur()}
    />
    <span class="unit">{control.unit}</span>
  </label>
  <button
    class="btn icon small ghost"
    title={`${t("reset")}: ${fallback}`}
    aria-label={t("reset")}
    disabled={!value.changed || disabled}
    onclick={() => app.call("reset_value", { key: control.key })}
  >
    <Icon name="undo" />
  </button>
</div>

<style>
  .label {
    color: var(--text-2);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .label.changed {
    color: var(--text);
    font-weight: 500;
  }
  .control {
    display: grid;
    grid-template-columns: minmax(80px, 1fr) 96px 22px;
    align-items: center;
    gap: 8px;
  }
  .slider {
    position: relative;
    height: 22px;
    display: flex;
    align-items: center;
  }
  .tick {
    position: absolute;
    left: calc(6px + (100% - 12px) * var(--default) / 100%);
    top: 15px;
    width: 1px;
    height: 5px;
    background: var(--text-3);
  }
  input[type="range"] {
    appearance: none;
    -webkit-appearance: none;
    width: 100%;
    height: 4px;
    margin: 0;
    border-radius: 2px;
    background: linear-gradient(90deg, var(--accent) var(--share), var(--line-2) var(--share));
    outline: none;
  }
  input[type="range"]:disabled {
    opacity: 0.5;
  }
  input[type="range"]::-webkit-slider-thumb {
    -webkit-appearance: none;
    width: 12px;
    height: 12px;
    border-radius: 50%;
    background: var(--raised);
    border: 1px solid var(--line-3);
  }
  input[type="range"]::-moz-range-thumb {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background: var(--raised);
    border: 1px solid var(--line-3);
  }
  input[type="range"]:hover::-webkit-slider-thumb {
    border-color: var(--accent);
  }
  input[type="range"]:focus-visible::-webkit-slider-thumb {
    border-color: var(--accent);
    box-shadow: 0 0 0 2px var(--accent-soft);
  }
  .number {
    position: relative;
    display: flex;
    align-items: center;
  }
  .number .input {
    height: 22px;
    text-align: right;
    padding-right: 26px;
  }
  .changed .number .input {
    color: var(--accent-text);
  }
  .unit {
    position: absolute;
    right: 6px;
    color: var(--text-3);
    font-size: 11.5px;
    pointer-events: none;
  }
</style>
