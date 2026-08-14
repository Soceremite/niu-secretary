#!/usr/bin/env node

import process from "node:process";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const { chromium } = require("../web/node_modules/playwright");

async function readInput() {
  const chunks = [];
  for await (const chunk of process.stdin) chunks.push(chunk);
  return JSON.parse(Buffer.concat(chunks).toString("utf8") || "{}");
}

function output(payload) {
  process.stdout.write(`${JSON.stringify(payload)}\n`);
}

let browser;
try {
  const input = await readInput();
  const formulas = Array.isArray(input.formulas)
    ? input.formulas.map((value) => String(value ?? ""))
    : [String(input.latex ?? "")];
  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  await page.addInitScript(() => {
    window.MathJax = {
      loader: { load: ["[tex]/ams"] },
      tex: {
        packages: { "[+]": ["ams"] },
        macros: { textsc: ["\\\\mathrm{#1}", 1] },
      },
      startup: { typeset: false },
    };
  });
  await page.goto("about:blank");
  await page.addScriptTag({ url: "https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-chtml.js" });
  await page.waitForFunction(() => window.MathJax?.startup?.promise, null, { timeout: 25000 });
  await page.evaluate(() => window.MathJax.startup.promise);
  const results = await page.evaluate(async (values) => {
    const compiled = [];
    for (const latex of values) {
      try {
        const node = await window.MathJax.tex2chtmlPromise(latex, { display: true });
        const errorNode = node.querySelector("mjx-merror");
        compiled.push({
          valid: !errorNode,
          error: errorNode?.getAttribute("title") || errorNode?.textContent?.trim() || "",
        });
      } catch (error) {
        compiled.push({ valid: false, error: String(error?.message || error) });
      }
    }
    return compiled;
  }, formulas);
  output({ status: "ok", results });
} catch (error) {
  output({ status: "unavailable", error: String(error?.message || error).slice(0, 1000) });
  process.exitCode = 2;
} finally {
  await browser?.close();
}
