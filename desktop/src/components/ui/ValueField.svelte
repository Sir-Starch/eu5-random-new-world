<script lang="ts">
  // One exact value as a bar: its fill shows where the value stands between its limits and a
  // tick marks the world type's value. Drag to change it, click to type it, the arrow keys step
  // it (with Shift by a tenth) and Backspace puts the world type's value back.
  import { tick } from "svelte";
  import { app, t } from "../../lib/app.svelte";
  import type { ControlInfo, ValueState } from "../../lib/types";
  import Icon from "../Icon.svelte";

  let {
    control,
    value,
    disabled = false,
  }: { control: ControlInfo; value: ValueState; disabled?: boolean } = $props();

  let bar = $state<HTMLDivElement>();
  let dragging = $state<number | null>(null);
  let editing = $state(false);
  let press: { x: number; moved: boolean } | null = null;
  let last = 0;
  let pending: ReturnType<typeof setTimeout> | null = null;

  const position = $derived(dragging ?? value.position);
  const share = $derived((position / control.steps) * 100);
  const defaultShare = $derived((value.default_position / control.steps) * 100);
  const name = $derived(t(`control.${control.key}`));
  const about = $derived(t(`control.${control.key}.about`));
  const unit = $derived(control.unit ? ` ${control.unit}` : "");
  const shown = $derived(`${value.shown.toFixed(control.decimals)}${unit}`);
  const fallback = $derived(`${value.default.toFixed(control.decimals)}${unit}`);

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

  function at(event: PointerEvent): number {
    if (!bar) return position;
    const rect = bar.getBoundingClientRect();
    const share = Math.min(1, Math.max(0, (event.clientX - rect.left) / rect.width));
    return Math.round(share * control.steps);
  }

  function down(event: PointerEvent): void {
    if (disabled || event.button !== 0 || !bar) return;
    bar.setPointerCapture(event.pointerId);
    press = { x: event.clientX, moved: false };
  }

  function move(event: PointerEvent): void {
    if (!press) return;
    if (!press.moved && Math.abs(event.clientX - press.x) < 3) return;
    press.moved = true;
    const next = at(event);
    if (next !== dragging) {
      dragging = next;
      send(next);
    }
  }

  async function up(): Promise<void> {
    if (!press) return;
    const moved = press.moved;
    press = null;
    if (!moved) {
      editing = true;
      return;
    }
    if (dragging === null) return;
    if (pending) clearTimeout(pending);
    await app.call("set_position", { key: control.key, position: dragging });
    dragging = null;
  }

  function step(next: number): void {
    const clamped = Math.max(0, Math.min(control.steps, next));
    if (clamped !== value.position) void app.call("set_position", { key: control.key, position: clamped });
  }

  function key(event: KeyboardEvent): void {
    if (disabled) return;
    const tenth = Math.max(1, Math.round(control.steps / 10));
    const by = event.shiftKey ? tenth : 1;
    if (event.key === "ArrowLeft" || event.key === "ArrowDown") step(value.position - by);
    else if (event.key === "ArrowRight" || event.key === "ArrowUp") step(value.position + by);
    else if (event.key === "PageDown") step(value.position - tenth);
    else if (event.key === "PageUp") step(value.position + tenth);
    else if (event.key === "Home") step(0);
    else if (event.key === "End") step(control.steps);
    else if (event.key === "Enter" || event.key === "F2") editing = true;
    else if (event.key === "Backspace" || event.key === "Delete") reset();
    else return;
    event.preventDefault();
  }

  function reset(): void {
    if (value.changed) void app.call("reset_value", { key: control.key });
  }

  async function commit(text: string): Promise<void> {
    if (!editing) return;
    editing = false;
    const number = Number(text.trim().replace(",", "."));
    if (text.trim() && Number.isFinite(number)) await app.call("set_value", { key: control.key, value: number });
    await tick();
    bar?.focus();
  }

  async function cancel(): Promise<void> {
    editing = false;
    await tick();
    bar?.focus();
  }

  function focused(node: HTMLInputElement): void {
    node.focus();
    node.select();
  }
</script>

<div class="value" class:changed={value.changed} class:disabled>
  {#if editing}
    <input
      class="input edit num"
      inputmode="decimal"
      value={value.shown.toFixed(control.decimals)}
      aria-label={name}
      use:focused
      onblur={(event) => commit(event.currentTarget.value)}
      onkeydown={(event) => {
        if (event.key === "Enter") void commit(event.currentTarget.value);
        else if (event.key === "Escape") {
          event.stopPropagation();
          void cancel();
        }
      }}
    />
  {:else}
    <div
      bind:this={bar}
      class="bar"
      role="slider"
      tabindex={disabled ? -1 : 0}
      aria-label={name}
      aria-valuemin={0}
      aria-valuemax={control.steps}
      aria-valuenow={position}
      aria-valuetext={shown}
      aria-disabled={disabled}
      title={`${about}\n${t("reset")}: ${fallback}`}
      style:--share={`${share}%`}
      style:--default={`${defaultShare}%`}
      onpointerdown={down}
      onpointermove={move}
      onpointerup={up}
      onpointercancel={() => {
        press = null;
        dragging = null;
      }}
      onkeydown={key}
    >
      <span class="fill"></span>
      <span class="tick"></span>
      <span class="name">{name}</span>
      <span class="number num">{shown}</span>
    </div>
  {/if}
  <button
    class="btn icon small ghost reset"
    title={`${t("reset")}: ${fallback}`}
    aria-label={`${t("reset")}: ${name}`}
    disabled={!value.changed || disabled}
    onclick={reset}
  >
    <Icon name="undo" />
  </button>
</div>

<style>
  .value {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 22px;
    align-items: center;
    gap: 2px;
  }
  .bar {
    position: relative;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    height: 24px;
    padding: 0 8px;
    border: 1px solid var(--line-2);
    border-radius: var(--radius);
    background: var(--field);
    overflow: hidden;
    cursor: ew-resize;
    font-size: 12.5px;
  }
  .bar:hover {
    border-color: var(--line-3);
  }
  .bar:focus-visible {
    outline: 1px solid var(--accent);
    outline-offset: 1px;
  }
  .fill {
    position: absolute;
    inset: 0 auto 0 0;
    width: var(--share);
    background: var(--fill);
  }
  .tick {
    position: absolute;
    left: var(--default);
    bottom: 0;
    width: 1px;
    height: 4px;
    background: var(--text-2);
  }
  .name,
  .number {
    position: relative;
    white-space: nowrap;
  }
  .name {
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    color: var(--text-2);
  }
  .number {
    flex: none;
  }
  .changed .name {
    color: var(--text);
    font-weight: 500;
  }
  .changed .number {
    color: var(--accent-text);
  }
  .disabled .bar {
    opacity: 0.5;
    cursor: default;
  }
  .edit {
    height: 24px;
    text-align: right;
  }
  .reset:disabled {
    opacity: 0.2;
  }
</style>
