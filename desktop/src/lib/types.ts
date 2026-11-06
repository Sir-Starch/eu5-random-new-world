// The data the bridge sends (rnw/gui/view.py); the names are the bridge's.

export interface ControlInfo {
  toggle?: boolean;
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
  /** The new world can be changed and queued now, also while a world is being made. */
  preparable: boolean;
  /** Why the world chosen now cannot be queued, or null. */
  queue_problem: string | null;
  /** The worlds in the queue; `error` says why a world could not be made, "" when it did not fail. */
  queue: { code: string; seed: string; type: string; running: boolean; error: string }[];
  queue_done: number;
  /** How many worlds of the queue could not be made; they stay listed with their errors. */
  queue_failed: number;
  /** A world was added during a run: the queue goes on by itself when it is done. */
  queue_follows: boolean;
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
  playset: string[];
  parent: string;
  parent_name: string;
  picture: string;
  add_problem: string | null;
  remove_problem: string | null;
  can_change: boolean;
  /** Why no version of this world can be made (another algorithm epoch), or null. */
  version_problem: string | null;
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
  preferences: { show_new_world: boolean; language: string; window: string };
  resources: string;
  selection: string;
  library: LibraryEntry[];
  batch: string;
  new: NewState;
  world: WorldState | null;
  stray: StrayState | null;
  candidates: { seed: string; land: number; queued: boolean }[];
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

/** One recorded event as a timeline row; `place` is a cell index, -1 when none is named. */
export interface HistoryEntry {
  year: number;
  kind: string;
  label: string;
  text: string;
  place: number;
}

/** A society's trait: a 0-1000 scale (`number`), or a named value (`number` is -1). */
export interface HistoryAxis {
  key: string;
  label: string;
  number: number;
  word: string;
  kind: string;
  cause: string;
  year: number;
  place: number;
}

export interface HistoryReason {
  factor: string;
  label: string;
  cause: string;
  year: number;
  place: number;
  effect: number;
}

export interface HistoryPartner {
  name: string;
  place: number;
  tag: string;
  standing: {kind: string; label: string}[];
  reasons: HistoryReason[];
}

/** A societal value as EU5 shows it: a position from -100 (left pole) to 100 (right pole). */
export interface HistoryValue {
  key: string;
  label: string;
  left: string;
  right: string;
  position: number;
  kind: string;
  cause: string;
  year: number;
  place: number;
}

/** A country's society, chronicle and relationships (`history_presenter.Dossier`). */
export interface HistoryDossier {
  government: string;
  rank: string;
  technology: string;
  origin: HistoryEntry;
  values: HistoryValue[];
  axes: HistoryAxis[];
  chronicle: HistoryEntry[];
  partners: HistoryPartner[];
  more: number;
}

/** A region's ownership changes, shared inheritances and aims (`history_presenter.RegionHistory`). */
export interface HistoryRegion {
  changes: {year: number; count: number; place: number}[];
  heritage: {labels: string[]; members: {name: string; place: number}[]}[];
  ambitions: {kind: string; label: string; name: string; place: number; realized: boolean}[];
}

export interface AtlasBundle {
  history?: {countries: Record<string, HistoryDossier>; regions: Record<string, HistoryRegion>} | null;
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
