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
      { label: "TextRank", ready: data.textrank?.ready, info: "extractive baseline" },
      {
        label: "Seq2Seq",
        ready: data.seq2seq?.ready,
        info: data.seq2seq?.ready ? data.seq2seq.device : "checkpoint belum ada",
      },
      {
        label: "Gemini API",
        ready: data.gemini?.ready,
        info: data.gemini?.has_api_key ? data.gemini.model_name : "API key belum di-set",
      },
    ];

    for (const it of items) {
      const li = document.createElement("li");
      const badge = document.createElement("span");
      badge.className = "badge " + (it.ready ? "badge-ready" : "badge-off");
      badge.textContent = it.ready ? "ready" : "off";
      li.appendChild(badge);
      const text = document.createElement("span");
      text.innerHTML = `<strong>${it.label}</strong><br><span style="color:var(--text-muted);font-size:11px">${it.info ?? ""}</span>`;
      li.appendChild(text);
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

function renderResult(data) {
  $("result").innerHTML = `<div>${escapeHtml(data.summary || "(kosong)")}</div>`;
  $("resultModel").textContent = `Model: ${data.model}`;

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

$("btnClear").addEventListener("click", () => {
  $("inputText").value = "";
  $("referenceText").value = "";
  showError(null);
  $("result").innerHTML = '<div class="placeholder">Ringkasan akan muncul di sini.</div>';
  $("stats").classList.add("hidden");
  $("rouge").classList.add("hidden");
  $("resultModel").textContent = "—";
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
