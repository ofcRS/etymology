const form = document.getElementById("cognate-form");
const wordA = document.getElementById("word-a");
const wordB = document.getElementById("word-b");
const langA = document.getElementById("lang-a");
const langB = document.getElementById("lang-b");
const resultDiv = document.getElementById("result");
const checkBtn = document.getElementById("check-btn");
const graphContainer = document.getElementById("graph-container");

// Language auto-detection
function detectLang(text) {
  if (/[а-яёА-ЯЁ]/.test(text)) return "Russian";
  if (/[\u0530-\u058F]/.test(text)) return "Armenian";
  if (/[\u0370-\u03FF]/.test(text)) return "Greek";
  if (/[\u0600-\u06FF]/.test(text)) return "Arabic";
  return "English";
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
        `/api/search?q=${encodeURIComponent(q)}&lang=${encodeURIComponent(lang)}`
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

// Form submit
form.addEventListener("submit", async (e) => {
  e.preventDefault();

  const a = wordA.value.trim();
  const b = wordB.value.trim();
  if (!a || !b) return;

  checkBtn.disabled = true;
  resultDiv.className = "result";
  resultDiv.innerHTML = '<span class="loading"></span> Searching...';
  resultDiv.classList.remove("hidden");
  graphContainer.classList.remove("active");

  try {
    const res = await fetch("/api/cognates", {
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
      resultDiv.innerHTML = `
        <div>${data.message}</div>
        <div class="ancestor-detail">
          Common ancestor: <strong>${data.common_ancestor}</strong> (${data.ancestor_lang})
        </div>
      `;
      if (data.graph) {
        graphContainer.classList.add("active");
        renderGraph(data.graph);
      }
    } else {
      resultDiv.className = "result not-cognate";
      resultDiv.textContent = data.message;
      if (data.graph_a || data.graph_b) {
        graphContainer.classList.add("active");
        renderSplitGraphs(data.graph_a, data.graph_b);
      }
    }
  } catch (err) {
    resultDiv.className = "result not-cognate";
    resultDiv.textContent = "Error: " + err.message;
  } finally {
    checkBtn.disabled = false;
  }
});
