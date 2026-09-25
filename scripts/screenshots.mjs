// Captures the README screenshots with headless Chrome over CDP (desktop, dark mode, real 390px mobile layout).
//   (cd backend && python -m uvicorn main:app --port 8830)
//   (cd frontend && npm run build && npx next start -p 3831)     # API_URL must point at the backend
//   node scripts/screenshots.mjs [baseUrl]
import { spawn } from "node:child_process";
import { existsSync, mkdirSync, mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const out = path.join(root, "docs", "screenshots");
mkdirSync(out, { recursive: true });
const base = process.argv[2] ?? "http://localhost:3831";
const chromePath = [
  process.env.CHROME_PATH,
  "C:/Program Files/Google/Chrome/Application/chrome.exe",
  "/usr/bin/google-chrome",
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
].find((p) => p && existsSync(p));
if (!chromePath) throw new Error("Chrome not found: set CHROME_PATH");

const port = 9334;
const chrome = spawn(chromePath, [
  "--headless=new", "--disable-gpu", "--hide-scrollbars", `--remote-debugging-port=${port}`,
  `--user-data-dir=${mkdtempSync(path.join(tmpdir(), "orderflow-shots-"))}`, "about:blank",
], { stdio: "ignore" });

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
async function connect() {
  for (let i = 0; i < 40; i++) {
    try {
      const list = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
      const page = list.find((t) => t.type === "page");
      if (page) return page.webSocketDebuggerUrl;
    } catch { /* not up yet */ }
    await sleep(250);
  }
  throw new Error("Chrome did not start");
}

const ws = new WebSocket(await connect());
await new Promise((r) => ws.addEventListener("open", r));
let id = 0;
const pending = new Map();
ws.addEventListener("message", (e) => {
  const m = JSON.parse(e.data);
  if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); }
});
const send = (method, params = {}) => new Promise((resolve, reject) => {
  const n = ++id;
  pending.set(n, (m) => (m.error ? reject(new Error(m.error.message)) : resolve(m.result)));
  ws.send(JSON.stringify({ id: n, method, params }));
});
const evaluate = async (expression) => (await send("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true })).result.value;

async function capture(name, route, { width = 1440, height = 900, mobile = false, dpr = 1, dark = false, ready, fullPage = true, clipHeight }) {
  await send("Emulation.setDeviceMetricsOverride", { width, height, deviceScaleFactor: dpr, mobile });
  await send("Emulation.setEmulatedMedia", { features: [{ name: "prefers-color-scheme", value: dark ? "dark" : "light" }] });
  await send("Page.navigate", { url: base + route });
  for (let i = 0; i < 80; i++) {
    if (await evaluate(ready).catch(() => false)) break;
    await sleep(400);
  }
  await sleep(1800);
  let h = height;
  if (fullPage) {
    // Grow the viewport to the full page so charts measure their real size.
    h = await evaluate("document.documentElement.scrollHeight");
    await send("Emulation.setDeviceMetricsOverride", { width, height: h, deviceScaleFactor: dpr, mobile });
    await sleep(1500);
  }
  const overflow = await evaluate("document.documentElement.scrollWidth - innerWidth");
  if (mobile) console.log(`${name}: horizontal overflow ${overflow}px`);
  const { data } = await send("Page.captureScreenshot", { format: "png", clip: { x: 0, y: 0, width, height: clipHeight ?? h, scale: 1 } });
  writeFileSync(path.join(out, `${name}.png`), Buffer.from(data, "base64"));
  console.log("captured", name);
}

const analysisReady = "!!document.querySelector('[data-testid=order-analysis]')";
const batchReady = "document.querySelectorAll('svg.recharts-surface').length >= 7 && !!document.querySelector('table')";
const insightsReady = "document.querySelectorAll('svg.recharts-surface').length >= 1 && document.body.innerText.includes('Confusion')";
const overviewReady = "document.body.innerText.includes('AVG DELAY PROBABILITY')";

try {
  await send("Page.enable");
  await capture("overview", "/", { ready: overviewReady, fullPage: false });
  await capture("analyse", "/analyse", { ready: analysisReady });
  await capture("batch", "/batch", { ready: batchReady });
  await capture("insights", "/insights", { ready: insightsReady });
  await capture("analyse-dark", "/analyse", { ready: analysisReady, dark: true, clipHeight: 1500 });
  await capture("mobile-overview", "/", { width: 390, height: 844, mobile: true, dpr: 2, ready: overviewReady, clipHeight: 1700 });
  await capture("mobile-analyse", "/analyse", { width: 390, height: 844, mobile: true, dpr: 2, ready: analysisReady, clipHeight: 2600 });
} finally {
  ws.close();
  chrome.kill();
}
