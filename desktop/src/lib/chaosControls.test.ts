// @vitest-environment happy-dom
import { afterEach, expect, it, vi } from "vitest";
import { flushSync, mount, unmount } from "svelte";
import NewWorldPanel from "../components/NewWorldPanel.svelte";
import { app } from "./app.svelte";
import type { NewState, State, Static } from "./types";

let panel: ReturnType<typeof mount> | undefined;

afterEach(async () => {
  if (panel) await unmount(panel);
  panel = undefined;
  app.now = null;
  app.info = null;
  vi.restoreAllMocks();
});

it("offers a separate settings draw only for Total Chaos and respects preparation locks", () => {
  const call = vi.spyOn(app, "call").mockResolvedValue(undefined);
  app.newTab = "world";
  app.info = { strings: { randomize_settings: "Randomize settings again" } } as unknown as Static;
  const settings = { mode: "chaos", choice: "chaos", preset: "islands", queue: [], values: {}, quick: {}, algorithm: 63, algorithms: [] } as unknown as NewState;
  app.now = { busy: false, preferences: { show_new_world: false }, new: settings } as State;
  panel = mount(NewWorldPanel, { target: document.body });
  flushSync();
  const findButton = () => Array.from(document.querySelectorAll("button")).find(
    (button) => button.textContent === "Randomize settings again",
  );
  const button = findButton();
  expect(button).toBeDefined();
  button!.click();
  expect(call).toHaveBeenCalledWith("randomize_settings");
  app.now = { ...app.now!, busy: true, task: "template", new: { ...settings, preparable: false } };
  flushSync();
  expect(findButton()?.disabled).toBe(true);
  app.now = { ...app.now!, task: "generate", new: { ...settings, preparable: true } };
  flushSync();
  expect(findButton()?.disabled).toBe(false);
  app.now = { ...app.now!, new: { ...settings, mode: null, choice: "islands" } };
  flushSync();
  expect(findButton()).toBeUndefined();
});
