<script lang="ts" module>
  // Line icons on a 16-unit grid with a one-pixel stroke, for toolbars and small buttons.
  const PATHS: Record<string, string> = {
    plus: "M8 3v10M3 8h10",
    search: "M7 2.5a4.5 4.5 0 1 0 0 9 4.5 4.5 0 0 0 0-9ZM10.3 10.3l3.7 3.7",
    x: "M4 4l8 8M12 4l-8 8",
    check: "M3 8.5 6.5 12 13 4.5",
    chevronDown: "M4.5 6.5 8 10l3.5-3.5",
    chevronRight: "M6.5 4.5 10 8l-3.5 3.5",
    copy: "M5.5 5.5h7v8h-7ZM3.5 10.5v-8h7",
    paste: "M5.5 1.5h5v2h-5ZM5.5 2.5h-2v11h9v-11h-2",
    folder: "M1.5 3.5h4.5l1.5 1.5h7v8.5h-13Z",
    open: "M1.5 12.5v-9h4.5l1.5 1.5h5.5v2M1.5 12.5l2.2-5h10.8l-2.2 5Z",
    file: "M3.5 1.5h6l3 3v10h-9ZM9.5 1.5v3h3",
    star: "M8 1.8 9.9 5.7l4.2.6-3 3 .7 4.3L8 11.6l-3.8 2 .7-4.3-3-3 4.2-.6Z",
    zoomIn: "M7 2.5a4.5 4.5 0 1 0 0 9 4.5 4.5 0 0 0 0-9ZM10.3 10.3l3.7 3.7M5 7h4M7 5v4",
    zoomOut: "M7 2.5a4.5 4.5 0 1 0 0 9 4.5 4.5 0 0 0 0-9ZM10.3 10.3l3.7 3.7M5 7h4",
    fit: "M2.5 6V2.5H6M10 2.5h3.5V6M13.5 10v3.5H10M6 13.5H2.5V10",
    expand: "M9.5 2.5h4v4M13.5 2.5 9 7M6.5 13.5h-4v-4M2.5 13.5 7 9",
    shrink: "M13.5 2.5l-4 4M9.5 3v3.5H13M2.5 13.5l4-4M3 9.5h3.5V13",
    borders: "M2.5 2.5h11v11h-11ZM8 2.5v4l-3 2.5v4.5M8 6.5l5.5 2",
    labels: "M3.5 4.5v-2h9v2M8 2.5v11M6 13.5h4",
    grid: "M2.5 2.5h11v11h-11ZM2.5 6.2h11M2.5 9.8h11M6.2 2.5v11M9.8 2.5v11",
    image: "M2.5 3.5h11v9h-11ZM2.5 10.5l3-3 2.5 2.5 2-2 3.5 3.5M10.5 6v.01",
    download: "M8 2v8M4.5 6.5 8 10l3.5-3.5M2.5 13.5h11",
    compare: "M8 1.5v13M2.5 3.5h3.5v9h-3.5ZM10 3.5h3.5v9H10Z",
    warning: "M8 2 14.5 13.5h-13ZM8 6.5V10M8 11.8v.2",
    alert: "M8 1.5a6.5 6.5 0 1 0 0 13 6.5 6.5 0 0 0 0-13ZM8 4.5v4.5M8 11v.5",
    info: "M8 1.5a6.5 6.5 0 1 0 0 13 6.5 6.5 0 0 0 0-13ZM8 7v4.5M8 4.5v.5",
    settings:
      "M6.79 3.15L6.84 1.5L9.16 1.5L9.21 3.15L10.58 3.72L11.77 2.59L13.41 4.23L12.28 5.42L12.85 6.79L14.5 6.84L14.5 9.16L12.85 9.21L12.28 10.58L13.41 11.77L11.77 13.41L10.58 12.28L9.21 12.85L9.16 14.5L6.84 14.5L6.79 12.85L5.42 12.28L4.23 13.41L2.59 11.77L3.72 10.58L3.15 9.21L1.5 9.16L1.5 6.84L3.15 6.79L3.72 5.42L2.59 4.23L4.23 2.59L5.42 3.72ZM8 6a2 2 0 1 0 0 4 2 2 0 0 0 0-4Z",
    undo: "M3.5 6.5h6.5a3.5 3.5 0 0 1 0 7H6M6 3.5l-3 3 3 3",
    trash: "M2.5 4.5h11M6.5 4.5v-2h3v2M4 4.5l.7 9h6.6l.7-9",
    sidebarLeft: "M2.5 3.5h11v9h-11ZM6.5 3.5v9",
    sidebarRight: "M2.5 3.5h11v9h-11ZM9.5 3.5v9",
  };

  export const ICONS = Object.keys(PATHS);
</script>

<script lang="ts">
  let {
    name,
    size = 16,
    fill = false,
    label = "",
  }: { name: string; size?: number; fill?: boolean; label?: string } = $props();
</script>

<svg
  width={size}
  height={size}
  viewBox="0 0 16 16"
  fill={fill ? "currentColor" : "none"}
  stroke="currentColor"
  stroke-width="1"
  stroke-linecap="round"
  stroke-linejoin="round"
  role={label ? "img" : undefined}
  aria-label={label || undefined}
  aria-hidden={label ? undefined : "true"}
>
  <path d={PATHS[name] ?? PATHS.info} />
</svg>

<style>
  svg {
    flex: none;
    display: block;
  }
</style>
