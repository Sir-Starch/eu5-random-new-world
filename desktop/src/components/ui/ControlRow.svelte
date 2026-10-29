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

<div class="row" class:changed={value.changed}>
  <div class="name" title={t(`control.${control.key}.about`)}>
    <span class="label">{t(`control.${control.key}`)}</span>
    <span class="about">{t(`control.${control.key}.about`)}</span>
  </div>
  <div class="slider" style:--share={`${share}%`} style:--default={`${defaultShare}%`}>
    <span class="tick" title={`${value.default.toFixed(control.decimals)}${control.unit ? ` ${control.unit}` : ""}`}></span>
    <input
      type="range"
      min="0"
      max={control.steps}
      step="1"
      value={position}
      {disabled}
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
    {#if control.unit}<span class="unit">{control.unit}</span>{/if}
  </label>
  <button
    class="btn icon small ghost reset"
    title={t("reset")}
    aria-label={t("reset")}
    disabled={!value.changed || disabled}
    onclick={() => app.call("reset_value", { key: control.key })}
  >
    <Icon name="undo" size={15} />
  </button>
</div>

<style>
  .row {
    display: grid;
    grid-template-columns: minmax(180px, 1.1fr) minmax(160px, 1.4fr) 112px 30px;
    align-items: center;
    gap: 16px;
    padding: 10px 4px;
    border-top: 1px solid var(--line);
  }
  .row:first-child {
    border-top: 0;
  }
  .name {
    display: grid;
    gap: 2px;
    min-width: 0;
  }
  .label {
    font-weight: 550;
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .changed .label::after {
    content: "";
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: var(--accent);
    box-shadow: 0 0 10px var(--accent);
  }
  .about {
    color: var(--text-3);
    font-size: 12px;
    line-height: 1.4;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }
  .slider {
    position: relative;
    height: 28px;
    display: flex;
    align-items: center;
  }
  .tick {
    position: absolute;
    left: calc(var(--default) * 0.98 + 1%);
    top: 4px;
    width: 2px;
    height: 20px;
    border-radius: 2px;
    background: var(--line-3);
    transform: translateX(-1px);
    pointer-events: auto;
  }
  input[type="range"] {
    appearance: none;
    -webkit-appearance: none;
    width: 100%;
    height: 6px;
    border-radius: 999px;
    background: linear-gradient(90deg, var(--accent) var(--share), var(--panel-3) var(--share));
    outline: none;
    cursor: pointer;
    margin: 0;
    position: relative;
  }
  input[type="range"]:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
  input[type="range"]::-webkit-slider-thumb {
    -webkit-appearance: none;
    width: 18px;
    height: 18px;
    border-radius: 50%;
    background: var(--text);
    border: 3px solid var(--accent);
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.35);
    transition: transform 100ms var(--ease);
  }
  input[type="range"]::-moz-range-thumb {
    width: 14px;
    height: 14px;
    border-radius: 50%;
    background: var(--text);
    border: 3px solid var(--accent);
  }
  input[type="range"]:hover::-webkit-slider-thumb {
    transform: scale(1.12);
  }
  input[type="range"]:focus-visible::-webkit-slider-thumb {
    box-shadow: 0 0 0 4px var(--accent-soft);
  }
  .number {
    position: relative;
    display: flex;
    align-items: center;
  }
  .number .input {
    text-align: right;
    padding-right: 30px;
    min-height: 32px;
  }
  .unit {
    position: absolute;
    right: 10px;
    color: var(--text-3);
    font-size: 12px;
    pointer-events: none;
  }
  @media (max-width: 1180px) {
    .row {
      grid-template-columns: 1fr 104px 30px;
    }
    .slider {
      grid-column: 1 / -1;
      grid-row: 2;
    }
  }
</style>
