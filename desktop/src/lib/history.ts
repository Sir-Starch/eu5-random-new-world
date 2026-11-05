// How the society panel draws what the generator recorded: a glyph and a tone for each kind of
// event, a tone for each remembered feeling and standing, and the numbers' written forms. Kinds
// are the template families of `history_text` (the generator names them, this only dresses them).

export type Tone = "origin" | "tie" | "split" | "clash" | "turn";

/** Events are drawn by what happened, not by whom it helped: a breakaway is a split for both. */
export const EVENTS: Record<string, { glyph: string; tone: Tone }> = {
  foundation: { glyph: "flag", tone: "origin" },
  union: { glyph: "merge", tone: "tie" },
  contact: { glyph: "link", tone: "tie" },
  exchange: { glyph: "swap", tone: "tie" },
  pact: { glyph: "link", tone: "tie" },
  protection: { glyph: "shield", tone: "tie" },
  access: { glyph: "star", tone: "tie" },
  separation: { glyph: "split", tone: "split" },
  secession: { glyph: "split", tone: "split" },
  independence: { glyph: "up", tone: "split" },
  conflict: { glyph: "bolt", tone: "clash" },
  pressure: { glyph: "bolt", tone: "clash" },
  repelled: { glyph: "shield", tone: "clash" },
  dependency: { glyph: "down", tone: "turn" },
  reform: { glyph: "lines", tone: "turn" },
  resisted: { glyph: "x", tone: "turn" },
  migration: { glyph: "forward", tone: "turn" },
};

export function eventStyle(kind: string): { glyph: string; tone: Tone } {
  return EVENTS[kind] ?? { glyph: "circle", tone: "turn" };
}

export type Mood = "good" | "bad" | "flat";

/** The feeling a remembered cause left, by its factor. */
export const FACTORS: Record<string, Mood> = {
  trust: "good",
  affinity: "good",
  grievance: "bad",
  fear: "bad",
  competition: "bad",
  dependence: "flat",
};

/** A partner's standing: rank (overlord, subject), friendly, hostile, or an ordinary agreement. */
export const STANDINGS: Record<string, "rank" | Mood> = {
  lord: "rank",
  subject: "rank",
  alliance: "good",
  rival: "bad",
  guarantor: "flat",
  protected: "flat",
  trade: "flat",
};

export function mood(factor: string): Mood {
  return FACTORS[factor] ?? "flat";
}

export function standing(kind: string): "rank" | Mood {
  return STANDINGS[kind] ?? "flat";
}

/** A 0-1000 trait on the 0-100 scale the meter draws. */
export function percent(value: number): number {
  return Math.round(Math.min(Math.max(value, 0), 1000) / 10);
}

/** An opinion change with a real minus sign, and a plus where it is positive. */
export function signed(value: number): string {
  return value > 0 ? `+${value}` : value < 0 ? `−${-value}` : "0";
}

/** Which pole a societal value leans to, and how far (0-100), as the game words its sliders. */
export function leaning(value: { position: number; left: string; right: string }): {
  name: string;
  strength: number;
} {
  const strength = Math.abs(value.position);
  return { name: value.position < 0 ? value.left : value.position > 0 ? value.right : "", strength };
}

/** The filled part of a two-pole bar, in percent of its width: from the middle toward a pole. */
export function spread(position: number): { left: number; width: number } {
  const clamped = Math.min(Math.max(position, -100), 100);
  return { left: clamped < 0 ? 50 + clamped / 2 : 50, width: Math.abs(clamped) / 2 };
}
