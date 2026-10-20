// Data-driven figures for the story page. Reads results/index.json (copied by scripts/build_site.py).
const $ = (s) => document.querySelector(s);
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}[c]));
const mean = (a) => a.reduce((s, x) => s + x, 0) / a.length;
const f3 = (x) => x.toFixed(3);

const PATTERN_ORDER = ["plain_typos", "casual_voice", "glossary_names", "pasted_verbatim", "shifted_hands", "unknown_names"];

function tooltip(container) {
  const tip = document.createElement("div");
  tip.className = "tip";
  container.appendChild(tip);
  container.querySelectorAll("[data-tip]").forEach((el) => {
    el.addEventListener("mousemove", (e) => {
      const box = container.getBoundingClientRect();
      tip.style.display = "block";
      tip.textContent = el.dataset.tip;
      tip.style.left = Math.min(e.clientX - box.left + 12, box.width - 220) + "px";
      tip.style.top = e.clientY - box.top - 30 + "px";
    });
    el.addEventListener("mouseleave", () => (tip.style.display = "none"));
  });
}

function curve(el, runs, versions, labels) {
  const W = Math.max(300, el.clientWidth - 40), H = 300, P = {l: 46, r: 56, t: 18, b: 52};
  const step = 0.02, ymax = Math.ceil(Math.max(...runs.map((r) => r.summary.cer)) / step) * step;
  const xs = (i) => P.l + i * (W - P.l - P.r) / (versions.length - 1);
  const ys = (v) => P.t + (1 - v / ymax) * (H - P.t - P.b);
  let g = "";
  for (let v = 0; v <= ymax + 1e-9; v += step) {
    g += `<line x1="${P.l}" x2="${W - P.r}" y1="${ys(v)}" y2="${ys(v)}" stroke="var(--rule)"/>`;
    g += `<text x="${P.l - 8}" y="${ys(v) + 4}" text-anchor="end">${v.toFixed(2)}</text>`;
  }
  g += `<text x="${P.l}" y="${P.t - 6}" font-size="11">CER, lower is better</text>`;
  const pts = versions.map((v, i) => [xs(i), ys(mean(runs.filter((r) => r.version === v).map((r) => r.summary.cer)))]);
  g += `<polyline points="${pts.map((p) => p.join(",")).join(" ")}" fill="none" stroke="var(--green)" stroke-width="2"/>`;
  versions.forEach((v, i) => {
    const rs = runs.filter((r) => r.version === v);
    const m = mean(rs.map((r) => r.summary.cer));
    g += `<text x="${xs(i)}" y="${H - 30}" text-anchor="middle" font-size="13" style="fill:var(--ink)">${v}</text>`;
    g += `<text x="${xs(i)}" y="${H - 14}" text-anchor="middle" font-size="11">${esc(labels[v] || "")}</text>`;
    rs.forEach((r, k) => {
      const dx = (k - (rs.length - 1) / 2) * 8;
      g += `<circle cx="${xs(i) + dx}" cy="${ys(r.summary.cer)}" r="4.5" fill="var(--card)" stroke="var(--ink)" stroke-width="1.5" data-tip="${v} run ${k + 1}: CER ${f3(r.summary.cer)}"/>`;
    });
    g += `<circle cx="${pts[i][0]}" cy="${pts[i][1]}" r="12" fill="transparent" data-tip="${v} mean of ${rs.length} run(s): CER ${f3(m)}"/>`;
    g += `<text x="${pts[i][0] + 10}" y="${pts[i][1] - 10}" font-size="12" style="fill:var(--ink-2)">${f3(m)}</text>`;
  });
  el.innerHTML = `<svg width="${W}" height="${H}" role="img" aria-label="Mean CER by version, with every run as a dot">${g}</svg>`;
  tooltip(el);
}

function heat(el, runs, versions) {
  const pats = PATTERN_ORDER.filter((p) => runs.some((r) => r.summary.patterns[p]));
  const n = (p) => runs.find((r) => r.summary.patterns[p]).summary.patterns[p].n;
  let h = `<table><thead><tr><th>Pattern</th><th class="num">Items</th>${versions.map((v) => `<th class="num">${v}</th>`).join("")}</tr></thead><tbody>`;
  pats.forEach((p) => {
    h += `<tr><td>${p.replace(/_/g, " ")}</td><td class="num">${n(p)}</td>`;
    versions.forEach((v) => {
      const vals = runs.filter((r) => r.version === v).map((r) => r.summary.patterns[p].cer);
      const m = mean(vals);
      const a = Math.min(1, m / 0.2);
      h += `<td class="num" style="background: color-mix(in srgb, var(--second) ${Math.round(a * 40)}%, transparent)" title="${p} ${v}: ${vals.map(f3).join(", ")}">${f3(m)}</td>`;
    });
    h += "</tr>";
  });
  h += `<tr><td><b>total</b></td><td class="num">${runs[0].summary.n}</td>${versions.map((v) => `<td class="num"><b>${f3(mean(runs.filter((r) => r.version === v).map((r) => r.summary.cer)))}</b></td>`).join("")}</tr>`;
  el.innerHTML = h + "</tbody></table>";
}

function noise(el, runs, versions) {
  let h = `<table><thead><tr><th>Version</th><th class="num">Run 1</th><th class="num">Run 2</th><th class="num">Run 3</th><th class="num">Range</th></tr></thead><tbody>`;
  versions.forEach((v) => {
    const c = runs.filter((r) => r.version === v).map((r) => r.summary.cer);
    if (c.length < 2) return;
    h += `<tr><td>${v}</td>${[0, 1, 2].map((k) => `<td class="num">${c[k] !== undefined ? f3(c[k]) : "–"}</td>`).join("")}<td class="num"><b>${f3(Math.max(...c) - Math.min(...c))}</b></td></tr>`;
  });
  el.innerHTML = h + "</tbody></table>";
}

async function main() {
  const index = await (await fetch("results/index.json")).json();
  const full = Math.max(...index.runs.map((r) => r.summary.n));
  const runs = index.runs.filter((r) => r.summary.n === full);
  const versions = [...new Set(runs.map((r) => r.version))];
  const labels = Object.fromEntries(versions.map((v) => [v, runs.find((r) => r.version === v).title.replace(/^v\d+:\s*/, "")]));
  const short = {v0: "echo", v1: "naive", v2: "voice", v3: "glossary", v4: "pasted text", v5: "drifted hands"};
  const draw = () => curve($("#curve"), runs, versions, short);
  draw();
  window.addEventListener("resize", draw);
  heat($("#heat"), runs, versions);
  noise($("#noise"), runs, versions);
  document.querySelectorAll("[data-version-title]").forEach((el) => (el.textContent = labels[el.dataset.versionTitle] || ""));
}
main().catch((e) => {
  document.querySelectorAll(".needs-data").forEach((el) => (el.innerHTML = `<p class="small bad">Could not load results/index.json (${esc(e.message)}). Run scripts/build_site.py, then serve docs/ over http.</p>`));
});
