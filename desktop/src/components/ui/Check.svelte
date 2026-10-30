<script lang="ts">
  // A checkbox with its label and an optional line of explanation under it.
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

<label class="check" class:disabled>
  <input
    type="checkbox"
    {checked}
    {disabled}
    onchange={(event) => onchange((event.currentTarget as HTMLInputElement).checked)}
  />
  <span>{label}{#if hint}<span class="about">{hint}</span>{/if}</span>
</label>
