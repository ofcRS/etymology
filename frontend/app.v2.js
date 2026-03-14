const API = window.location.pathname.endsWith("/")
  ? window.location.pathname
  : window.location.pathname + "/";

const form = document.getElementById("cognate-form");
const wordA = document.getElementById("word-a");
const wordB = document.getElementById("word-b");
const langA = document.getElementById("lang-a");
const langB = document.getElementById("lang-b");
const resultDiv = document.getElementById("result");
const checkBtn = document.getElementById("check-btn");
const graphContainer = document.getElementById("graph-container");
const graphLegend = document.getElementById("graph-legend");
const howToRead = document.getElementById("how-to-read");

// State for tree view toggle
let lastPathGraphData = null;
let lastAncestorTerm = null;
let lastAncestorLangCode = null;
let isTreeView = false;

// Example pairs
const EXAMPLE_PAIRS = [
  { a: "мать", langA: "ru", b: "mother", langB: "en" },
  { a: "вода", langA: "ru", b: "water", langB: "en" },
  { a: "молоко", langA: "ru", b: "milk", langB: "en" },
  { a: "ночь", langA: "ru", b: "night", langB: "en" },
  { a: "три", langA: "ru", b: "three", langB: "en" },
  { a: "сердце", langA: "ru", b: "heart", langB: "en" },
  { a: "нос", langA: "ru", b: "nose", langB: "en" },
  { a: "кот", langA: "ru", b: "cat", langB: "en" },
  { a: "два", langA: "ru", b: "two", langB: "en" },
  { a: "новый", langA: "ru", b: "new", langB: "en" },
  { a: "берёза", langA: "ru", b: "birch", langB: "en" },
  { a: "волк", langA: "ru", b: "wolf", langB: "en" },
];

// Fun facts
const FUN_FACTS = [
  "English \"mother\", Russian \"\u043C\u0430\u0442\u044C\", Latin \"m\u0101ter\", and Sanskrit \"m\u0101t\u00E1r\" all come from the same Proto-Indo-European root *m\u00E9h\u2082t\u0113r.",
  "The word \"czar\" (Russian \"\u0446\u0430\u0440\u044C\") comes from Latin \"Caesar\" \u2014 the same root as German \"Kaiser.\"",
  "English \"cow\" and Russian \"\u0433\u043E\u0432\u044F\u0434\u0438\u043D\u0430\" (beef) both trace back to Proto-Indo-European *g\u02B7\u1E53ws.",
  "\"Sugar\" traveled from Sanskrit \u0936\u0930\u094D\u0915\u0930\u093E (\u015B\u00E1rkar\u0101) through Persian, Arabic, and Latin before reaching English.",
  "The PIE root *h\u2082\u00E9k\u02B7eh\u2082 (water) gave Latin \"aqua\", but also \u2014 through Germanic \u2014 English \"island\" (via Old English \u00EDeg).",
  "Russian \"\u0433\u043E\u0440\u043E\u0434\" (city) and English \"garden\" are distant cousins \u2014 both from PIE *g\u02B0\u00F3rd\u02B0os (enclosure).",
  "Proto-Indo-European was spoken around 4500 BCE \u2014 over 6,000 years ago \u2014 yet its echoes are in nearly every word you speak today.",
  "\"Daughter\" in English, \"\u0434\u043E\u0447\u044C\" in Russian, \"\u03B8\u03C5\u03B3\u03AC\u03C4\u03B7\u03C1\" in Ancient Greek, and \"duhit\u00E1r\" in Sanskrit all share the PIE root *d\u02B0ug\u02B0\u2082t\u1E17r.",
];

// Render example chips
function renderExampleChips() {
  const container = document.getElementById("example-chips");
  const display = EXAMPLE_PAIRS.slice(0, 6);
  display.forEach((pair) => {
    const chip = document.createElement("button");
    chip.type = "button";
    chip.className = "example-chip";
    chip.textContent = `${pair.a} \u2194 ${pair.b}`;
    chip.addEventListener("click", () => submitPair(pair));
    container.appendChild(chip);
  });
}

function submitPair(pair) {
  wordA.value = pair.a;
  wordB.value = pair.b;
  langA.value = pair.langA;
  langB.value = pair.langB;
  form.dispatchEvent(new Event("submit", { cancelable: true }));
}

// Random button
document.getElementById("random-btn").addEventListener("click", () => {
  const pair = EXAMPLE_PAIRS[Math.floor(Math.random() * EXAMPLE_PAIRS.length)];
  submitPair(pair);
});

renderExampleChips();

// Fun fact rotation
let currentFactIndex = Math.floor(Math.random() * FUN_FACTS.length);
const funFactEl = document.getElementById("fun-fact");

function showFunFact() {
  funFactEl.textContent = FUN_FACTS[currentFactIndex];
  currentFactIndex = (currentFactIndex + 1) % FUN_FACTS.length;
}

showFunFact();
setInterval(showFunFact, 15000);
funFactEl.addEventListener("click", showFunFact);
funFactEl.style.cursor = "pointer";

// Language auto-detection
function detectLang(text) {
  if (/[а-яёА-ЯЁ]/.test(text)) return "ru";
  if (/[\u0530-\u058F]/.test(text)) return "hy";
  if (/[\u0370-\u03FF]/.test(text)) return "el";
  if (/[\u0600-\u06FF]/.test(text)) return "ar";
  return "en";
}

function setupLangDetection(input, langSelect) {
  input.addEventListener("input", () => {
    const text = input.value.trim();
    if (text.length > 0) {
      langSelect.value = detectLang(text);
    }
  });
}

setupLangDetection(wordA, langA);
setupLangDetection(wordB, langB);

// Autocomplete
let debounceTimer = null;

function setupAutocomplete(input, langSelect, suggestionsEl) {
  input.addEventListener("input", () => {
    clearTimeout(debounceTimer);
    const q = input.value.trim();
    if (q.length < 2) {
      suggestionsEl.classList.remove("active");
      return;
    }
    debounceTimer = setTimeout(async () => {
      const lang = langSelect.value;
      const res = await fetch(
        `${API}api/search?q=${encodeURIComponent(q)}&lang=${encodeURIComponent(lang)}`
      );
      const data = await res.json();
      suggestionsEl.innerHTML = "";
      if (data.length === 0) {
        suggestionsEl.classList.remove("active");
        return;
      }
      data.forEach((item) => {
        const li = document.createElement("li");
        li.textContent = item.term;
        li.addEventListener("click", () => {
          input.value = item.term;
          suggestionsEl.classList.remove("active");
        });
        suggestionsEl.appendChild(li);
      });
      suggestionsEl.classList.add("active");
    }, 200);
  });

  input.addEventListener("blur", () => {
    setTimeout(() => suggestionsEl.classList.remove("active"), 150);
  });
}

setupAutocomplete(wordA, langA, document.getElementById("suggestions-a"));
setupAutocomplete(wordB, langB, document.getElementById("suggestions-b"));

// Confidence badge HTML
function confidenceBadge(level) {
  if (!level) return "";
  const dots = { high: "\u25CF\u25CF\u25CF", medium: "\u25CF\u25CF\u25CB", low: "\u25CF\u25CB\u25CB" };
  return `<span class="confidence-badge confidence-${level}" title="${level} confidence">${dots[level] || ""}</span>`;
}

// Show/hide legend and how-to-read
function showLegend() {
  graphLegend.classList.remove("hidden");
  howToRead.classList.remove("hidden");
}

function hideLegend() {
  graphLegend.classList.add("hidden");
  howToRead.classList.add("hidden");
}

// Get a suggestion pair that shares a language with the current search
function getSuggestion(currentLangA, currentLangB) {
  const matches = EXAMPLE_PAIRS.filter(
    (p) =>
      p.langA === currentLangA ||
      p.langA === currentLangB ||
      p.langB === currentLangA ||
      p.langB === currentLangB
  );
  if (matches.length === 0) return EXAMPLE_PAIRS[0];
  return matches[Math.floor(Math.random() * matches.length)];
}

// Form submit
form.addEventListener("submit", async (e) => {
  e.preventDefault();

  const a = wordA.value.trim();
  const b = wordB.value.trim();
  if (!a || !b) return;

  checkBtn.disabled = true;
  isTreeView = false;
  graphContainer.classList.remove("tree-view");
  resultDiv.className = "result";
  resultDiv.innerHTML = '<span class="loading"></span> Searching for connections...';
  resultDiv.classList.remove("hidden");
  graphContainer.classList.remove("active");
  hideLegend();

  try {
    const res = await fetch(`${API}api/cognates`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        word_a: { term: a, lang: langA.value },
        word_b: { term: b, lang: langB.value },
      }),
    });

    const data = await res.json();

    if (data.is_cognate) {
      resultDiv.className = "result cognate";
      const badge = confidenceBadge(data.confidence);
      const summary = data.summary || data.message;
      const treeBtn = data.ancestor_lang_code
        ? `<button type="button" class="show-tree-btn" id="show-tree-btn">Show full descendant tree</button>`
        : "";
      resultDiv.innerHTML = `
        <div class="summary-banner">${badge} ${summary}</div>
        <div class="ancestor-detail">
          Common ancestor: <strong>${data.common_ancestor}</strong> (${data.ancestor_lang})
          ${treeBtn}
        </div>
      `;
      if (data.graph) {
        lastPathGraphData = data.graph;
        lastAncestorTerm = data.common_ancestor;
        lastAncestorLangCode = data.ancestor_lang_code;
        graphContainer.classList.add("active");
        renderGraph(data.graph);
        showLegend();
      }
      if (data.ancestor_lang_code) {
        document.getElementById("show-tree-btn").addEventListener("click", loadFullTree);
      }
    } else {
      resultDiv.className = "result not-cognate";
      const summary = data.summary || data.message;
      const suggestion = getSuggestion(langA.value, langB.value);
      const hasGraph = data.graph_a || data.graph_b;
      resultDiv.innerHTML = `
        <div class="summary-banner">${summary}</div>
        ${hasGraph ? '<div class="not-cognate-explanation">Their individual ancestry is shown below.</div>' : ""}
        <div class="try-instead">
          Try instead:
          <button type="button" class="example-chip" id="suggestion-chip">${suggestion.a} \u2194 ${suggestion.b}</button>
        </div>
      `;
      document
        .getElementById("suggestion-chip")
        .addEventListener("click", () => submitPair(suggestion));
      if (hasGraph) {
        graphContainer.classList.add("active");
        renderSplitGraphs(data.graph_a, data.graph_b);
        showLegend();
      }
    }
  } catch (err) {
    resultDiv.className = "result not-cognate";
    resultDiv.textContent = "Error: " + err.message;
  } finally {
    checkBtn.disabled = false;
  }
});

// Full tree expansion
async function loadFullTree() {
  if (!lastAncestorTerm || !lastAncestorLangCode) return;

  const btn = document.getElementById("show-tree-btn");
  btn.disabled = true;
  btn.textContent = "Loading tree...";

  try {
    const url = `${API}api/tree?term=${encodeURIComponent(lastAncestorTerm)}&lang=${encodeURIComponent(lastAncestorLangCode)}`;
    const res = await fetch(url);
    const treeData = await res.json();

    isTreeView = true;
    graphContainer.classList.add("tree-view");

    // Highlight the two input words
    const highlightIds = new Set([
      `${wordA.value.trim()}|${langA.value}`,
      `${wordB.value.trim()}|${langB.value}`,
    ]);

    renderTreeGraph(treeData, highlightIds);
    btn.textContent = "Back to path view";
    btn.disabled = false;
    btn.removeEventListener("click", loadFullTree);
    btn.addEventListener("click", backToPathView);
  } catch (err) {
    btn.textContent = "Error loading tree";
    btn.disabled = false;
  }
}

function backToPathView() {
  if (!lastPathGraphData) return;

  isTreeView = false;
  graphContainer.classList.remove("tree-view");
  renderGraph(lastPathGraphData);

  const btn = document.getElementById("show-tree-btn");
  btn.textContent = "Show full descendant tree";
  btn.removeEventListener("click", backToPathView);
  btn.addEventListener("click", loadFullTree);
}
