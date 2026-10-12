// Render frames of a Lottie JSON with lottie-web (SVG renderer) in headless Chromium.
//   node tools/lottie/render.js anim.json outDir [--frames 0,10,20 | --every N] [--bg #rrggbb|transparent]
// Writes outDir/f<frame>.png at the animation's native size and prints a JSON summary.
const fs = require("fs");
const path = require("path");
const { chromium } = require("playwright-core");

const [file, outDir, ...rest] = process.argv.slice(2);
const opt = (k, d) => { const i = rest.indexOf(k); return i >= 0 ? rest[i + 1] : d; };
const anim = JSON.parse(fs.readFileSync(file, "utf8"));
const total = Math.round(anim.op - anim.ip);
let frames;
if (opt("--frames")) frames = opt("--frames").split(",").map(Number);
else { const n = Number(opt("--every", 1)); frames = []; for (let f = 0; f < total; f += n) frames.push(f); }
const bg = opt("--bg", "transparent");
const lottieSrc = fs.readFileSync(path.join(__dirname, "node_modules/lottie-web/build/player/lottie_svg.min.js"), "utf8");

(async () => {
  fs.mkdirSync(outDir, { recursive: true });
  const browser = await chromium.launch({ executablePath: "/opt/pw-browsers/chromium-1194/chrome-linux/chrome" });
  const page = await browser.newPage({ viewport: { width: anim.w, height: anim.h } });
  await page.setContent(`<html><body style="margin:0;background:${bg}"><div id="a" style="width:${anim.w}px;height:${anim.h}px"></div></body></html>`);
  await page.addScriptTag({ content: lottieSrc });
  const errors = [];
  page.on("pageerror", e => errors.push(String(e)));
  await page.evaluate(data => {
    window.anim = lottie.loadAnimation({ container: document.getElementById("a"), renderer: "svg", loop: false, autoplay: false, animationData: data });
  }, anim);
  for (const f of frames) {
    await page.evaluate(f => window.anim.goToAndStop(f, true), f);
    await page.screenshot({ path: path.join(outDir, `f${String(f).padStart(3, "0")}.png`), omitBackground: bg === "transparent" });
  }
  await browser.close();
  console.log(JSON.stringify({ file, w: anim.w, h: anim.h, fr: anim.fr, frames: total, rendered: frames.length, errors }));
})();
