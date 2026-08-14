#!/usr/bin/env node

import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const { chromium } = require("../web/node_modules/playwright");

const baseUrl = (process.argv[2] || "").replace(/\/$/, "");
const outputDir = process.argv[3] || "/tmp/airesearch-deep-reading-verification";
if (!baseUrl) throw new Error("usage: verify_deep_reading_display.mjs BASE_URL [OUTPUT_DIR]");
fs.mkdirSync(outputDir, { recursive: true });

const papers = [
  "world-model-self-distillation",
  "latent-diffusion-policy",
  "world2vlm",
  "what-if-world",
  "world-action-models",
];
const viewports = [
  { name: "desktop", width: 1440, height: 1000 },
  { name: "mobile", width: 390, height: 844 },
];

const browser = await chromium.launch({ headless: true });
const report = [];
try {
  for (const viewport of viewports) {
    for (const paper of papers) {
      const context = await browser.newContext({ viewport });
      const page = await context.newPage();
      const consoleErrors = [];
      page.on("console", (message) => {
        if (message.type() === "error") consoleErrors.push(message.text());
      });
      await page.goto(`${baseUrl}/papers/${paper}.html#deep-reading`, { waitUntil: "networkidle" });
      await page.waitForFunction(() => document.querySelector(".paper-blog-prose"));
      await page.waitForFunction(() => !window.MathJax?.startup?.promise || document.querySelector("mjx-container"), null, {
        timeout: 30000,
      });
      await page.waitForTimeout(300);
      const metrics = await page.evaluate(() => {
        const dimensions = (selector) => {
          const node = document.querySelector(selector);
          return node
            ? {
                clientWidth: node.clientWidth,
                scrollWidth: node.scrollWidth,
                left: Math.round(node.getBoundingClientRect().left),
                right: Math.round(node.getBoundingClientRect().right),
              }
            : null;
        };
        const images = [...document.querySelectorAll(".paper-blog-image img")].map((image) => ({
          alt: image.alt,
          width: image.clientWidth,
          naturalWidth: image.naturalWidth,
          naturalHeight: image.naturalHeight,
          src: image.getAttribute("src"),
        }));
        const locallyScrollable = [...document.querySelectorAll(".paper-blog-equation, .paper-blog-prose pre, .paper-blog-prose table")]
          .filter((node) => node.scrollWidth > node.clientWidth + 1)
          .map((node) => ({ tag: node.tagName, className: node.className, clientWidth: node.clientWidth, scrollWidth: node.scrollWidth }));
        return {
          viewportWidth: document.documentElement.clientWidth,
          documentScrollWidth: document.documentElement.scrollWidth,
          bodyScrollWidth: document.body.scrollWidth,
          deepReading: dimensions(".paper-mode-deep-reading"),
          blogSection: dimensions(".paper-blog-section"),
          prose: dimensions(".paper-blog-prose"),
          mathErrors: [...document.querySelectorAll("mjx-merror")].map((node) => node.getAttribute("title") || node.textContent),
          images,
          locallyScrollable,
        };
      });
      const screenshot = path.join(outputDir, `${paper}-${viewport.name}.png`);
      let screenshotError = "";
      try {
        await page.screenshot({ path: screenshot, fullPage: false, timeout: 15000 });
      } catch (error) {
        screenshotError = String(error?.message || error).slice(0, 500);
      }
      report.push({ paper, viewport: viewport.name, screenshot, screenshotError, consoleErrors, ...metrics });
      fs.writeFileSync(path.join(outputDir, "report.partial.json"), `${JSON.stringify(report, null, 2)}\n`);
      await page.close();
      await context.close();
    }
  }
} finally {
  await browser.close();
}

fs.writeFileSync(path.join(outputDir, "report.json"), `${JSON.stringify(report, null, 2)}\n`);
process.stdout.write(`${JSON.stringify(report, null, 2)}\n`);
const failed = report.some(
  (item) =>
    item.documentScrollWidth > item.viewportWidth + 1 ||
    item.bodyScrollWidth > item.viewportWidth + 1 ||
    item.mathErrors.length > 0 ||
    item.consoleErrors.some((error) => /MathJax|TypeError|ReferenceError/i.test(error)),
);
process.exitCode = failed ? 1 : 0;
