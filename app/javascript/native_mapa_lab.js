// Replays measured N1/N2/N3 cutoff metrics. Does NOT synthesize epoch telemetry.
const initNativeLab = () => {
  document.querySelectorAll("[data-native-timeline]").forEach(root => {
    if (root.dataset.ready) return;
    root.dataset.ready = "1";
    let blocks;
    try { blocks = JSON.parse(root.querySelector("[data-native-data]").textContent); }
    catch (_) { return; }
    const range = root.querySelector("[data-cut-range]");
    const label = root.querySelector("[data-cut-label]");
    const plot = root.querySelector("[data-native-plot]");
    let timer = null;
    const render = () => {
      const cutoff = Number(range.value);
      label.textContent = "N" + cutoff;
      const selected = blocks.find(item => item.cutoff === cutoff);
      if (!selected) return;
      plot.replaceChildren();
      const header = document.createElement("h4");
      header.textContent = "Macro-F1 e recall de reprovação — N" + cutoff;
      plot.appendChild(header);
      selected.results.forEach(result => {
        const row = document.createElement("div");
        row.className = "native-bar-row";
        const name = document.createElement("span");
        name.textContent = result.model;
        row.appendChild(name);
        for (const [metric, text] of [["f1","F1"],["recall_failed","Recall"]]) {
          const bar = document.createElement("div");
          bar.className = "native-track";
          const fill = document.createElement("span");
          fill.className = metric === "f1" ? "native-fill" : "native-fill native-recall";
          const value = Number(result[metric] || 0);
          fill.style.width = Math.max(0, Math.min(100, value * 100)) + "%";
          fill.title = text + ": " + (value * 100).toFixed(1) + "%";
          bar.appendChild(fill);
          row.appendChild(bar);
        }
        plot.appendChild(row);
      });
    };
    range.addEventListener("input", render);
    root.querySelector("[data-cut-play]").addEventListener("click", () => {
      if (timer) clearInterval(timer);
      range.value = "1"; render();
      timer = setInterval(() => {
        if (Number(range.value) >= 3) { clearInterval(timer); timer = null; return; }
        range.value = String(Number(range.value) + 1); render();
      }, 950);
    });
    render();
  });
};
document.addEventListener("turbo:load", initNativeLab);
document.addEventListener("DOMContentLoaded", initNativeLab);
