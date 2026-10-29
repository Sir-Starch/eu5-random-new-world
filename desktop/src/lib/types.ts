// The data the bridge sends (rnw/gui/view.py); the names are the bridge's.

export interface ControlInfo {
  key: string;
  group: string;
  low: number;
  high: number;
  decimals: number;
  unit: string;
  steps: number;
  logarithmic: boolean;
  advanced: boolean;
  default: number;
}

export interface Static {
  title: string;
  version: string;
  language: string;
  languages: { key: string; name: string }[];
  grouping: string;
  strings: Record<string, string>;
  choices: string[];
  modes: string[];
  world_types: string[];
  groups: string[];
  controls: ControlInfo[];
  quick: { name: string; levels: string[] }[];
  budget: number;
  layers: string[];
  ramps: string[];
  bordered: string[];
  parts: string[];
  destinations: string[];
  name_limit: number;
}

export interface ValueState {
  shown: number;
  position: number;
  default: number;
  default_position: number;
  changed: boolean;
}

export interface NewState {
  choice: string;
  preset: string;
  mode: string | null;
  seed: string;
  code: string;
  notice: string;
  values: Record<string, ValueState>;
  quick: Record<string, string | null>;
  changed: number;
  estimate: number | null;
  estimate_text: string;
  over_budget: boolean;
  problem: string | null;
  hint: string;
  install: boolean;
  destination: string;
  target: string;
  land_mask: string;
  land_mask_text: string;
  candidates_enabled: boolean;
  template_enabled: boolean;
  queue: { seed: string; type: string }[];
  queue_done: number;
  retry: boolean;
  retry_enabled: boolean;
}

export interface LibraryEntry {
  kind: "world" | "stray";
  id: string;
  title: string;
  preset?: string;
  type?: string;
  created?: number;
  placement: "in_game" | "kept" | "code_only";
  place?: string;
  part?: string;
  depth?: number;
  starred?: boolean;
  tag?: string;
  shown?: boolean;
  picture?: string;
  folder?: string;
}

export interface WorldTask {
  running: boolean;
  line: string;
  bar: boolean;
  fraction: number;
  failed?: boolean;
}

export interface Totals {
  countries: number;
  states: number;
  tribes: number;
  cultures: number;
  religions: number;
  locations: number;
  land: number;
}

export interface WorldState {
  id: string;
  name: string;
  default_name: string;
  tag: string;
  code: string;
  preset: string;
  type: string;
  seed: string;
  custom: string;
  created: number;
  build: string;
  generator: string;
  reproduce: string;
  place: string;
  placement: "in_game" | "kept" | "code_only";
  shown: boolean;
  revealed: boolean;
  atlas: boolean;
  summary: string;
  totals: Totals | null;
  notes: string;
  user_tag: string;
  starred: boolean;
  part: string;
  note: string;
  advice: string;
  parent: string;
  parent_name: string;
  picture: string;
  add_problem: string | null;
  remove_problem: string | null;
  can_change: boolean;
  task: WorldTask | null;
  told: string;
  compare: boolean;
}

export interface StrayState {
  folder: string;
  path: string;
  about: string;
  remove_problem: string | null;
}

export interface GameState {
  found: boolean;
  directory: string;
  build: string;
  status: string;
  profile: string;
  problem: string;
}

export type Phase = "idle" | "running" | "cancelling" | "finished" | "failed" | "cancelled";

export interface State {
  phase: Phase;
  task: string | null;
  target: string;
  busy: boolean;
  runs: number;
  fraction: number;
  generating: boolean;
  running: string;
  stages: { label: string; state: "done" | "running" | "waiting" }[];
  eta: number | null;
  status: string;
  message: string;
  result: { world: string; seconds: number } | null;
  game: GameState;
  games: string[];
  profiles: string[];
  preferences: { show_new_world: boolean; language: string };
  resources: string;
  selection: string;
  library: LibraryEntry[];
  batch: string;
  new: NewState;
  world: WorldState | null;
  stray: StrayState | null;
  candidates: { seed: string; land: number }[];
}

export interface LayerBundle {
  colours: string;
  classes: string;
  values: string;
  legend: [string, string, number][];
  ramp: string[];
}

export interface CountryInfo {
  tag: string;
  name: string;
  kind: string;
  color: string;
  capital: number;
  culture: number;
  religion: number;
  locations: number;
}

export interface AtlasBundle {
  id: string;
  name: string;
  size: [number, number];
  scale: number;
  cells: number;
  labels: string;
  kinds: string[];
  keys: string[];
  names: string[];
  kind: number[];
  area: string[];
  region: string[];
  owner: number[];
  culture: number[];
  religion: number[];
  material: number[];
  climate: number[];
  vegetation: number[];
  topography: number[];
  settlement: number[];
  population: number[];
  complexity: number[];
  centre: number[];
  vocabulary: Record<string, string[]>;
  raw: Record<string, string[]>;
  precious: string[];
  countries: CountryInfo[];
  totals: Totals;
  layers: Record<string, LayerBundle>;
}
