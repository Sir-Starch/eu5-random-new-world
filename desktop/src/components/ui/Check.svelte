<script lang="ts">
  import Icon from "../Icon.svelte";

  // A checkbox with its label and an optional line of explanation under it. `info` is a longer
  // explanation: an info mark ends the line, and the whole checkbox shows it as its tooltip.
  let {
    checked,
    label,
    hint = "",
    info = "",
    disabled = false,
    onchange,
  }: {
    checked: boolean;
    label: string;
    hint?: string;
    info?: string;
    disabled?: boolean;
    onchange: (value: boolean) => void;
  } = $props();
</script>

<label class="check" class:disabled title={info || undefined}>
  <input
    type="checkbox"
    {checked}
    {disabled}
    onchange={(event) => onchange((event.currentTarget as HTMLInputElement).checked)}
  />
  <span>{label}{#if hint}<span class="about">{hint}{#if info}<span class="info-mark"><Icon name="info" size={13} /></span>{/if}</span>{/if}</span>
</label>
