// =============================================================
// IndoSum Summarizer - Frontend logic
// =============================================================

const API = {
  status: "/api/status",
  summarize: "/api/summarize",
  sample: "/api/sample",
};

const $ = (id) => document.getElementById(id);

// ---------- Tab navigation ----------
document.querySelectorAll(".nav-item").forEach((el) => {
  el.addEventListener("click", () => {
    document.querySelectorAll(".nav-item").forEach((n) => n.classList.remove("active"));
    el.classList.add("active");
    const tab = el.dataset.tab;
    document.querySelectorAll(".tab").forEach((t) => t.classList.add("hidden"));
    $("tab-" + tab).classList.remove("hidden");
  });
});

// ---------- Status ----------
async function refreshStatus() {
  try {
    const res = await fetch(API.status);
    const data = await res.json();
    const list = $("statusList");
    list.innerHTML = "";

    const items = [
      { label: "TextRank", ready: data.textrank?.ready },
      { label: "Seq2Seq",  ready: data.seq2seq?.ready },
      { label: "Gemini API", ready: data.gemini?.ready },
    ];

    for (const it of items) {
      const li = document.createElement("li");
      li.className = it.ready ? "is-ready" : "is-off";
      li.innerHTML = `
        <span class="status-dot"></span>
        <span class="status-name">${it.label}</span>
        <span class="status-state">${it.ready ? "ready" : "off"}</span>
      `;
      list.appendChild(li);
    }
  } catch (err) {
    console.error("status failed", err);
  }
}

// ---------- Summarize ----------
function showError(msg) {
  const el = $("error");
  if (!msg) {
    el.classList.add("hidden");
    el.textContent = "";
    return;
  }
  el.textContent = msg;
  el.classList.remove("hidden");
}

function setLoading(on) {
  $("loadingBar").classList.toggle("hidden", !on);
  $("btnSummarize").disabled = on;
}

let lastSummary = "";

function renderResult(data) {
  lastSummary = data.summary || "";
  $("result").innerHTML = `<div>${escapeHtml(data.summary || "(kosong)")}</div>`;
  $("resultModel").textContent = `Model: ${data.model}`;
  $("btnCopy").classList.toggle("hidden", !lastSummary);

  $("statInput").textContent = `${data.stats.input_words} kata`;
  $("statSummary").textContent = `${data.stats.summary_words} kata`;
  $("statCompression").textContent = `${(data.stats.compression * 100).toFixed(1)}%`;
  $("stats").classList.remove("hidden");

  if (data.rouge) {
    $("r1").textContent = data.rouge.rouge1.toFixed(4);
    $("r2").textContent = data.rouge.rouge2.toFixed(4);
    $("rL").textContent = data.rouge.rougeL.toFixed(4);
    $("rouge").classList.remove("hidden");
  } else {
    $("rouge").classList.add("hidden");
  }
}

function escapeHtml(str) {
  return String(str).replace(/[&<>"']/g, (c) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  }[c]));
}

$("useReference").addEventListener("change", (e) => {
  $("referenceWrap").classList.toggle("hidden", !e.target.checked);
});

// ---------- Char counter ----------
function updateCharCounter() {
  const v = $("inputText").value;
  const chars = v.length;
  const words = v.trim() ? v.trim().split(/\s+/).length : 0;
  $("charCounter").textContent = `${chars.toLocaleString("id-ID")} karakter · ${words.toLocaleString("id-ID")} kata`;
}
$("inputText").addEventListener("input", updateCharCounter);
updateCharCounter();

// ---------- Copy button ----------
$("btnCopy").addEventListener("click", async () => {
  if (!lastSummary) return;
  try {
    await navigator.clipboard.writeText(lastSummary);
  } catch {
    // Fallback for browsers without clipboard API
    const ta = document.createElement("textarea");
    ta.value = lastSummary;
    document.body.appendChild(ta);
    ta.select();
    try { document.execCommand("copy"); } catch {}
    document.body.removeChild(ta);
  }
  const btn = $("btnCopy");
  btn.classList.add("copied");
  btn.querySelector(".copy-label").textContent = "Tersalin";
  setTimeout(() => {
    btn.classList.remove("copied");
    btn.querySelector(".copy-label").textContent = "Salin";
  }, 1400);
});

// ---------- File upload ----------
$("fileInput").addEventListener("change", (e) => {
  const file = e.target.files && e.target.files[0];
  const info = $("fileInfo");
  if (!file) {
    info.textContent = "Belum ada file dipilih";
    info.classList.remove("has-file");
    return;
  }
  if (file.size > 2 * 1024 * 1024) {
    showError("Ukuran file maksimal 2 MB.");
    e.target.value = "";
    return;
  }
  const reader = new FileReader();
  reader.onload = (ev) => {
    $("inputText").value = String(ev.target.result || "");
    info.textContent = `${file.name} · ${(file.size / 1024).toFixed(1)} KB`;
    info.classList.add("has-file");
    showError(null);
  };
  reader.onerror = () => {
    showError("Gagal membaca file.");
  };
  reader.readAsText(file, "utf-8");
});

$("btnClear").addEventListener("click", () => {
  $("inputText").value = "";
  $("referenceText").value = "";
  showError(null);
  $("result").innerHTML = '<div class="placeholder">Ringkasan akan muncul di sini.</div>';
  $("stats").classList.add("hidden");
  $("rouge").classList.add("hidden");
  $("resultModel").textContent = "—";
  $("btnCopy").classList.add("hidden");
  lastSummary = "";
  updateCharCounter();
});

$("btnSummarize").addEventListener("click", async () => {
  showError(null);
  const text = $("inputText").value.trim();
  if (!text) {
    showError("Teks input masih kosong.");
    return;
  }
  const payload = {
    text,
    model: $("modelSelect").value,
    num_sentences: parseInt($("numSentences").value || "3", 10),
  };
  if ($("useReference").checked) {
    const ref = $("referenceText").value.trim();
    if (ref) payload.reference = ref;
  }

  setLoading(true);
  try {
    const res = await fetch(API.summarize, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (!res.ok) {
      showError(data.error || `Server error (${res.status})`);
      return;
    }
    renderResult(data);
  } catch (err) {
    showError("Tidak bisa menghubungi server: " + err.message);
  } finally {
    setLoading(false);
  }
});

// ---------- Sample dataset ----------
let lastSample = null;

async function fetchSample() {
  showError(null);
  const split = $("sampleSplit").value;
  const index = parseInt($("sampleIndex").value || "0", 10);
  $("btnFetchSample").disabled = true;
  try {
    const res = await fetch(`${API.sample}?split=${split}&index=${index}`);
    const data = await res.json();
    if (!res.ok) {
      $("sampleArticle").innerHTML = `<div class="placeholder">${escapeHtml(data.error || "Gagal memuat")}</div>`;
      $("sampleGold").innerHTML = `<div class="placeholder">—</div>`;
      $("sampleMeta").classList.add("hidden");
      $("btnSendToInput").disabled = true;
      return;
    }
    lastSample = data;
    $("sampleMeta").classList.remove("hidden");
    $("sampleMeta").innerHTML = `id=${escapeHtml(data.id || "?")} · category=${escapeHtml(data.category || "?")} · source=${escapeHtml(data.source || "?")}`;
    $("sampleArticle").textContent = data.article;
    $("sampleGold").textContent = data.gold_summary;
    $("btnSendToInput").disabled = false;
  } catch (err) {
    showError("Tidak bisa menghubungi server: " + err.message);
  } finally {
    $("btnFetchSample").disabled = false;
  }
}

$("btnFetchSample").addEventListener("click", fetchSample);
$("btnLoadSample").addEventListener("click", async () => {
  // Quick action: load random sample langsung ke tab Ringkas.
  $("sampleSplit").value = "test";
  const idx = Math.floor(Math.random() * 200);
  $("sampleIndex").value = idx;
  await fetchSample();
  if (lastSample) {
    $("inputText").value = lastSample.article;
    $("referenceText").value = lastSample.gold_summary;
    $("useReference").checked = true;
    $("referenceWrap").classList.remove("hidden");
  }
});

$("btnSendToInput").addEventListener("click", () => {
  if (!lastSample) return;
  $("inputText").value = lastSample.article;
  $("referenceText").value = lastSample.gold_summary;
  $("useReference").checked = true;
  $("referenceWrap").classList.remove("hidden");
  // pindah ke tab Ringkas
  document.querySelector('.nav-item[data-tab="summarize"]').click();
});

// ---------- Init ----------
refreshStatus();
