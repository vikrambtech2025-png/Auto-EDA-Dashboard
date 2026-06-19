const state = {
  current: null,
  history: [],
};

const $ = (id) => document.getElementById(id);
const fmt = new Intl.NumberFormat();

function showToast(message) {
  const toast = $("toast");
  toast.textContent = message;
  toast.classList.remove("hidden");
  clearTimeout(showToast.timer);
  showToast.timer = setTimeout(() => toast.classList.add("hidden"), 3600);
}

function setBusy(isBusy) {
  document.querySelectorAll("button").forEach((button) => {
    button.disabled = isBusy;
  });
  $("uploadForm").classList.toggle("is-busy", isBusy);
}

async function api(path, options = {}) {
  const response = await fetch(path, options);
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.detail || "Request failed");
  }
  return payload;
}

function resizeCanvas(canvas) {
  const ratio = window.devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();
  canvas.width = Math.max(320, Math.floor(rect.width * ratio));
  canvas.height = Math.floor(Number(canvas.getAttribute("height")) * ratio);
  const ctx = canvas.getContext("2d");
  ctx.scale(ratio, ratio);
  return { ctx, width: rect.width, height: Number(canvas.getAttribute("height")) };
}

function drawBarChart(canvasId, data, options = {}) {
  const canvas = $(canvasId);
  const { ctx, width, height } = resizeCanvas(canvas);
  ctx.clearRect(0, 0, width, height);
  const padding = { top: 18, right: 16, bottom: 46, left: 38 };
  const plotW = width - padding.left - padding.right;
  const plotH = height - padding.top - padding.bottom;
  const maxValue = Math.max(...data.map((item) => item.value ?? item.count), 1);

  ctx.strokeStyle = "#dde6e3";
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(padding.left, padding.top);
  ctx.lineTo(padding.left, padding.top + plotH);
  ctx.lineTo(padding.left + plotW, padding.top + plotH);
  ctx.stroke();

  if (!data.length) {
    ctx.fillStyle = "#647270";
    ctx.font = "13px system-ui";
    ctx.fillText("No chartable values", padding.left, padding.top + 28);
    return;
  }

  const barGap = 8;
  const barW = Math.max(12, (plotW - barGap * (data.length - 1)) / data.length);
  data.forEach((item, index) => {
    const rawValue = item.value ?? item.count;
    const barH = (rawValue / maxValue) * plotH;
    const x = padding.left + index * (barW + barGap);
    const y = padding.top + plotH - barH;
    ctx.fillStyle = options.color || "#0d8f7b";
    ctx.fillRect(x, y, barW, barH);
    ctx.fillStyle = "#647270";
    ctx.font = "11px system-ui";
    ctx.save();
    ctx.translate(x + 2, height - 12);
    ctx.rotate(-0.58);
    const label = String(item.label || item.column || "").slice(0, 18);
    ctx.fillText(label, 0, 0);
    ctx.restore();
  });
}

function drawDistribution() {
  const selected = $("distributionSelect").value;
  const charts = state.current?.report?.charts?.distributions || [];
  const chart = charts.find((item) => item.column === selected) || charts[0];
  drawBarChart(
    "distributionChart",
    chart ? chart.bins.map((bin) => ({ label: bin.label, count: bin.count })) : [],
    { color: "#283f3b" },
  );
}

function drawCategory() {
  const selected = $("categorySelect").value;
  const charts = state.current?.report?.charts?.categories || [];
  const chart = charts.find((item) => item.column === selected) || charts[0];
  drawBarChart(
    "categoryChart",
    chart ? chart.values.map((item) => ({ label: item.label, count: item.count })) : [],
    { color: "#d98b18" },
  );
}

function metric(id, value) {
  $(id).textContent = value;
}

function renderHistory() {
  const list = $("historyList");
  list.innerHTML = "";
  if (!state.history.length) {
    list.innerHTML = '<div class="alert-item"><strong>No saved runs</strong><p>Upload a dataset to create the first report.</p></div>';
    return;
  }
  state.history.forEach((item) => {
    const button = document.createElement("button");
    button.className = `history-item ${state.current?.id === item.id ? "active" : ""}`;
    button.type = "button";
    button.innerHTML = `
      <p>${item.name}</p>
      <span>${fmt.format(item.rows)} rows · ${item.columns} cols · score ${item.quality_score}</span>
    `;
    button.addEventListener("click", () => loadReport(item.id));
    list.appendChild(button);
  });
}

function renderReport(payload) {
  state.current = payload;
  const report = payload.report;
  const overview = report.overview;
  $("emptyState").classList.add("hidden");
  $("dashboard").classList.remove("hidden");
  $("datasetTitle").textContent = payload.name || report.filename;
  $("downloadLink").href = `/api/datasets/${payload.id}/download`;
  $("downloadLink").classList.remove("disabled");
  $("downloadLink").removeAttribute("aria-disabled");

  metric("rowsMetric", fmt.format(overview.rows));
  metric("columnsMetric", fmt.format(overview.columns));
  metric("missingMetric", `${overview.missing_pct}%`);
  metric("missingDetail", `${fmt.format(overview.missing_cells)} cells`);
  metric("qualityMetric", overview.quality_score);
  metric("typeMetric", `${report.schema.numeric} numeric · ${report.schema.categorical} other`);
  metric("sampleNote", overview.sample_note);
  metric("schemaSummary", `${report.schema.columns.length} profiled columns`);

  drawBarChart(
    "missingChart",
    report.charts.missing.map((item) => ({ label: item.label, value: item.value })),
    { color: "#0d8f7b" },
  );

  const distributionSelect = $("distributionSelect");
  distributionSelect.innerHTML = "";
  report.charts.distributions.forEach((chart) => {
    const option = document.createElement("option");
    option.value = chart.column;
    option.textContent = chart.column;
    distributionSelect.appendChild(option);
  });
  drawDistribution();

  const categorySelect = $("categorySelect");
  categorySelect.innerHTML = "";
  report.charts.categories.forEach((chart) => {
    const option = document.createElement("option");
    option.value = chart.column;
    option.textContent = chart.column;
    categorySelect.appendChild(option);
  });
  drawCategory();

  const alerts = $("alertsList");
  $("alertCount").textContent = `${report.alerts.length} alerts`;
  alerts.innerHTML = report.alerts.length
    ? report.alerts.map((alert) => `<div class="alert-item ${alert.level}"><strong>${alert.title}</strong><p>${alert.detail}</p></div>`).join("")
    : '<div class="alert-item"><strong>No major issues found</strong><p>The automatic checks did not flag severe quality problems.</p></div>';

  const correlations = $("correlationList");
  correlations.innerHTML = report.correlations.length
    ? report.correlations.map((item) => `<div class="correlation-item"><strong>${item.left} ↔ ${item.right}</strong><p>r = ${item.value}</p></div>`).join("")
    : '<div class="correlation-item"><strong>Not enough numeric fields</strong><p>Upload at least two numeric columns to calculate correlations.</p></div>';

  $("schemaTable").innerHTML = report.schema.columns.map((column) => `
    <tr>
      <td><strong>${column.name}</strong></td>
      <td><span class="badge">${column.semantic_type}</span></td>
      <td>${column.missing_pct}%</td>
      <td>${fmt.format(column.unique)}</td>
      <td>${column.mean ?? "—"}</td>
      <td>${column.outlier_pct ?? "—"}${column.outlier_pct === undefined ? "" : "%"}</td>
    </tr>
  `).join("");

  renderPreview(report.preview);
  renderHistory();
}

function renderPreview(rows) {
  const target = $("previewTable");
  if (!rows.length) {
    target.innerHTML = "<p>No preview rows available.</p>";
    return;
  }
  const headers = Object.keys(rows[0]);
  target.innerHTML = `
    <table>
      <thead><tr>${headers.map((header) => `<th>${header}</th>`).join("")}</tr></thead>
      <tbody>
        ${rows.map((row) => `<tr>${headers.map((header) => `<td>${row[header] ?? ""}</td>`).join("")}</tr>`).join("")}
      </tbody>
    </table>
  `;
}

async function refreshHistory() {
  const payload = await api("/api/datasets");
  state.history = payload.datasets;
  renderHistory();
}

async function loadReport(id) {
  try {
    const payload = await api(`/api/datasets/${id}`);
    renderReport(payload);
  } catch (error) {
    showToast(error.message);
  }
}

async function uploadCurrentFile(event) {
  event.preventDefault();
  const file = $("fileInput").files[0];
  if (!file) {
    showToast("Choose a CSV, XLS, or XLSX file first.");
    return;
  }
  const form = new FormData();
  form.append("file", file);
  setBusy(true);
  try {
    const payload = await api("/api/upload", { method: "POST", body: form });
    await refreshHistory();
    renderReport(payload);
    showToast("EDA report generated.");
  } catch (error) {
    showToast(error.message);
  } finally {
    setBusy(false);
  }
}

async function loadDemo() {
  setBusy(true);
  try {
    const payload = await api("/api/demo", { method: "POST" });
    await refreshHistory();
    renderReport(payload);
    showToast("Demo report generated.");
  } catch (error) {
    showToast(error.message);
  } finally {
    setBusy(false);
  }
}

function initDropZone() {
  const dropZone = $("dropZone");
  const fileInput = $("fileInput");
  fileInput.addEventListener("change", () => {
    const file = fileInput.files[0];
    if (file) {
      dropZone.querySelector("strong").textContent = file.name;
      dropZone.querySelector("small").textContent = `${(file.size / 1024 / 1024).toFixed(2)} MB selected`;
    }
  });

  ["dragenter", "dragover"].forEach((name) => {
    dropZone.addEventListener(name, (event) => {
      event.preventDefault();
      dropZone.classList.add("dragging");
    });
  });
  ["dragleave", "drop"].forEach((name) => {
    dropZone.addEventListener(name, (event) => {
      event.preventDefault();
      dropZone.classList.remove("dragging");
    });
  });
  dropZone.addEventListener("drop", (event) => {
    fileInput.files = event.dataTransfer.files;
    fileInput.dispatchEvent(new Event("change"));
  });
}

window.addEventListener("resize", () => {
  if (!state.current) return;
  drawBarChart("missingChart", state.current.report.charts.missing.map((item) => ({ label: item.label, value: item.value })));
  drawDistribution();
  drawCategory();
});

$("uploadForm").addEventListener("submit", uploadCurrentFile);
$("demoButton").addEventListener("click", loadDemo);
$("refreshButton").addEventListener("click", refreshHistory);
$("distributionSelect").addEventListener("change", drawDistribution);
$("categorySelect").addEventListener("change", drawCategory);
initDropZone();
refreshHistory().catch((error) => showToast(error.message));
