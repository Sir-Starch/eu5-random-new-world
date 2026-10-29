<script lang="ts" module>
  // Stroke icons on a 24-unit grid, drawn for this window.
  const PATHS: Record<string, string> = {
    plus: "M12 5v14M5 12h14",
    globe:
      "M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18Zm-9 9h18M12 3c2.5 2.6 3.8 5.6 3.8 9s-1.3 6.4-3.8 9c-2.5-2.6-3.8-5.6-3.8-9S9.5 5.6 12 3Z",
    map: "m3 6.5 6-2.5 6 2.5 6-2.5v13.5l-6 2.5-6-2.5-6 2.5Zm6-2.5v13.5m6-11v13.5",
    layers: "m12 3 9 5-9 5-9-5 9-5Zm-9 9 9 5 9-5m-18 4 9 5 9-5",
    search: "M10.5 4a6.5 6.5 0 1 0 0 13 6.5 6.5 0 0 0 0-13Zm4.8 11.3L20 20",
    settings:
      "M12 9.2a2.8 2.8 0 1 0 0 5.6 2.8 2.8 0 0 0 0-5.6Zm7.4 3.9.1-1.1-.1-1.1 2-1.6-2-3.4-2.4.9a7.6 7.6 0 0 0-1.9-1.1L14.7 3h-4l-.4 2.6c-.7.3-1.3.6-1.9 1.1L6 5.8 4 9.2l2 1.6L5.9 12l.1 1.1-2 1.6 2 3.4 2.4-.9c.6.5 1.2.8 1.9 1.1l.4 2.7h4l.4-2.7c.7-.3 1.3-.6 1.9-1.1l2.4.9 2-3.4Z",
    info: "M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18Zm0 8v5m0-8.5v.5",
    star: "m12 3.5 2.6 5.4 5.9.8-4.3 4.1 1 5.8L12 16.8l-5.2 2.8 1-5.8-4.3-4.1 5.9-.8Z",
    copy: "M9 9h10v11H9Zm-4 6V4h10",
    paste: "M9 4h6v3H9Zm-3 1.5H5v15h14v-15h-1",
    dice: "M5 4h14a1 1 0 0 1 1 1v14a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1Zm3.5 3.5h.01m7 0h.01m-3.5 4.5h.01m-3.5 4.5h.01m7 0h.01",
    refresh: "M20 11a8 8 0 0 0-14.3-4.9L4 8m0-4v4h4m-4 5a8 8 0 0 0 14.3 4.9L20 16m0 4v-4h-4",
    play: "M7 4.5v15l12-7.5Z",
    stop: "M6 6h12v12H6Z",
    x: "M6 6l12 12M18 6 6 18",
    check: "m5 12.5 4.5 4.5L19 7",
    chevronDown: "m6 9 6 6 6-6",
    chevronRight: "m9 6 6 6-6 6",
    chevronLeft: "m15 6-6 6 6 6",
    folder: "M3 6.5A1.5 1.5 0 0 1 4.5 5H9l2 2.5h8.5A1.5 1.5 0 0 1 21 9v9.5a1.5 1.5 0 0 1-1.5 1.5h-15A1.5 1.5 0 0 1 3 18.5Z",
    file: "M6 3h8l5 5v13H6Zm8 0v5h5",
    open: "M4 20V5.5A1.5 1.5 0 0 1 5.5 4H10l2 2h6.5A1.5 1.5 0 0 1 20 7.5V9M4 20l3.2-8.2A1.5 1.5 0 0 1 8.6 11H21l-3.4 8.1a1.5 1.5 0 0 1-1.4.9Z",
    download: "M12 4v11m-5-5 5 5 5-5M5 20h14",
    upload: "M12 20V9m-5 5 5-5 5 5M5 4h14",
    trash: "M4 7h16M10 11v6m4-6v6M6 7l1 13h10l1-13M9 7V4h6v3",
    eye: "M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12Zm9.5-3a3 3 0 1 0 0 6 3 3 0 0 0 0-6Z",
    eyeOff:
      "M3 3l18 18M10.6 6.1A9 9 0 0 1 12 6c6 0 9.5 6 9.5 6a16 16 0 0 1-2.9 3.5M6.6 7.4C3.9 9.2 2.5 12 2.5 12S6 18 12 18c1.6 0 3-.4 4.2-1m-6.3-7.1a3 3 0 0 0 4.2 4.2",
    sparkles:
      "M10 3.5 11.6 8 16 9.5 11.6 11 10 15.5 8.4 11 4 9.5 8.4 8Zm8 9 .9 2.6 2.6.9-2.6.9L18 19.5l-.9-2.6-2.6-.9 2.6-.9Z",
    queue: "M4 6h12M4 12h12M4 18h8m6-3 3 3-3 3",
    image: "M4 5h16v14H4Zm0 11 4.5-4.5 3.5 3.5 2.5-2.5L20 17M15.5 8.5h.01",
    compare: "M12 3v18M4 6h5v12H4Zm11 0h5v12h-5",
    fit: "M4 9V4h5m6 0h5v5m0 6v5h-5m-6 0H4v-5",
    zoomIn: "M10.5 4a6.5 6.5 0 1 0 0 13 6.5 6.5 0 0 0 0-13Zm4.8 11.3L20 20M10.5 8v5M8 10.5h5",
    zoomOut: "M10.5 4a6.5 6.5 0 1 0 0 13 6.5 6.5 0 0 0 0-13Zm4.8 11.3L20 20M8 10.5h5",
    expand: "M15 4h5v5M9 20H4v-5M20 4l-6 6M4 20l6-6",
    shrink: "M14 4v6h6M10 20v-6H4M20 4l-6 6M4 20l6-6",
    tag: "M3.5 12.5V4.5a1 1 0 0 1 1-1h8l8 8-9 9Zm4.5-5h.01",
    notes: "M5 4h14v16H5Zm4 4h6m-6 4h6m-6 4h3",
    undo: "M9 14 4 9l5-5M4 9h10.5a5.5 5.5 0 0 1 0 11H11",
    branch: "M6 3v12m0 0a3 3 0 1 0 0 6 3 3 0 0 0 0-6Zm12-6a3 3 0 1 0 0-6 3 3 0 0 0 0 6Zm0 0c0 4-4 4-9 6",
    share: "M8.6 13.5l6.8 4M15.4 6.5l-6.8 4M18 3a3 3 0 1 0 0 6 3 3 0 0 0 0-6ZM6 9a3 3 0 1 0 0 6 3 3 0 0 0 0-6Zm12 6a3 3 0 1 0 0 6 3 3 0 0 0 0-6Z",
    warning: "M12 4 2.5 20h19Zm0 6v4.5m0 3v.01",
    alert: "M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18Zm0 5v5m0 3.5v.01",
    game: "M7 8h10a4 4 0 0 1 4 4v1a3 3 0 0 1-5.4 1.8L14.7 14H9.3l-.9.8A3 3 0 0 1 3 13v-1a4 4 0 0 1 4-4Zm0 3v3m-1.5-1.5h3m7.5-.5h.01m2 0h.01",
    crown: "M4 18h16M4 18 3 7l5 4 4-6 4 6 5-4-1 11",
    people:
      "M9 11a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7Zm-6 9a6 6 0 0 1 12 0m1.5-9a3 3 0 1 0-1-5.8M17 14a5 5 0 0 1 4 6",
    flame: "M12 3c1 3 5 5 5 10a5 5 0 0 1-10 0c0-2 1-3.5 2-4.5 0 2 1 3 2 3 0-3-1-5.5 1-8.5Z",
    pin: "M12 21s7-6.2 7-12a7 7 0 0 0-14 0c0 5.8 7 12 7 12Zm0-14.5a2.5 2.5 0 1 0 0 5 2.5 2.5 0 0 0 0-5Z",
    keyboard: "M3 6h18v12H3Zm4 4h.01m4 0h.01m4 0h.01m4 0h.01M7 14h10",
    sun: "M12 7.5a4.5 4.5 0 1 0 0 9 4.5 4.5 0 0 0 0-9ZM12 2v2m0 16v2M2 12h2m16 0h2M4.9 4.9l1.4 1.4m11.4 11.4 1.4 1.4m0-14.2-1.4 1.4M6.3 17.7l-1.4 1.4",
    moon: "M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5Z",
    monitor: "M3 4h18v12H3Zm6 16h6m-3-4v4",
    grid: "M4 4h7v7H4Zm9 0h7v7h-7ZM4 13h7v7H4Zm9 0h7v7h-7Z",
    list: "M8 6h12M8 12h12M8 18h12M4 6h.01M4 12h.01M4 18h.01",
    filter: "M4 5h16l-6 8v6l-4-2v-4Z",
    location: "M12 2v3m0 14v3M2 12h3m14 0h3M12 7a5 5 0 1 0 0 10 5 5 0 0 0 0-10Z",
    mountain: "m3 19 6.5-11 4 6.5L16 11l5 8Z",
    sliders: "M4 6h9m4 0h3M4 12h3m4 0h9M4 18h11m4 0h1M15 4v4M9 10v4m8 2v4",
    labels: "M4 7V5h16v2M12 5v14m-3 0h6",
    borders: "M4 4h16v16H4Zm0 8h7V4m5 16v-8h4",
    external: "M14 4h6v6m0-6-9 9M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5",
    heart: "M12 20s-8-4.6-8-10.3A4.5 4.5 0 0 1 12 7a4.5 4.5 0 0 1 8 2.7C20 15.4 12 20 12 20Z",
    camera: "M4 8h3l2-3h6l2 3h3v11H4Zm8 2.5a3.5 3.5 0 1 0 0 7 3.5 3.5 0 0 0 0-7Z",
    swipe: "M12 3v18M8 8l-4 4 4 4m8-8 4 4-4 4",
    hand: "M8 13V5.5a1.5 1.5 0 0 1 3 0V11m0-1V4.5a1.5 1.5 0 0 1 3 0V11m0-4.5a1.5 1.5 0 0 1 3 0V13a7 7 0 0 1-7 7h-.5a6 6 0 0 1-4.8-2.4L4 15a1.6 1.6 0 0 1 2.4-2.1L8 14.5",
  };

  export const ICONS = Object.keys(PATHS);
</script>

<script lang="ts">
  let {
    name,
    size = 18,
    stroke = 1.8,
    fill = false,
    label = "",
  }: { name: string; size?: number; stroke?: number; fill?: boolean; label?: string } = $props();
</script>

<svg
  width={size}
  height={size}
  viewBox="0 0 24 24"
  fill={fill ? "currentColor" : "none"}
  stroke="currentColor"
  stroke-width={stroke}
  stroke-linecap="round"
  stroke-linejoin="round"
  role={label ? "img" : undefined}
  aria-label={label || undefined}
  aria-hidden={label ? undefined : "true"}
>
  <path d={PATHS[name] ?? PATHS.info} />
</svg>
