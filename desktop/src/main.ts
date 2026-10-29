import { mount } from "svelte";
import "./app.css";
import App from "./App.svelte";
import { applyTheme } from "./lib/theme.svelte";

applyTheme();
const target = document.getElementById("app");
if (!target) throw new Error("No #app element");
export default mount(App, { target });
