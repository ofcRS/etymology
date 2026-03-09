const LANG_NAMES = {
  en: "English",
  ru: "Russian",
  de: "German",
  fr: "French",
  es: "Spanish",
  it: "Italian",
  pt: "Portuguese",
  nl: "Dutch",
  pl: "Polish",
  cs: "Czech",
  el: "Greek",
  hy: "Armenian",
  fa: "Persian",
  ar: "Arabic",
  "ine-pro": "Proto-Indo-European",
  "gem-pro": "Proto-Germanic",
  "sla-pro": "Proto-Slavic",
  "ine-bsl-pro": "Proto-Balto-Slavic",
  "iir-pro": "Proto-Indo-Iranian",
  "gmw-pro": "Proto-West Germanic",
  "itc-pro": "Proto-Italic",
  "grk-pro": "Proto-Hellenic",
  ang: "Old English",
  enm: "Middle English",
  la: "Latin",
  lla: "Late Latin",
  grc: "Ancient Greek",
  cu: "Old Church Slavonic",
  orv: "Old East Slavic",
  non: "Old Norse",
  fro: "Old French",
  xno: "Old Northern French",
  frm: "Middle French",
  sa: "Sanskrit",
  goh: "Old High German",
  gmh: "Middle High German",
  gml: "Middle Low German",
  dum: "Middle Dutch",
  odt: "Old Dutch",
  osx: "Old Saxon",
  peo: "Old Persian",
  xcl: "Old Armenian",
  "la-med": "Medieval Latin",
  "la-new": "New Latin",
  "la-lat": "Late Latin",
};

// Human-readable edge labels
const HUMAN_LABELS = {
  inherited_from: "evolved from",
  derived_from: "derived from",
  borrowed_from: "borrowed from",
  has_root: "from root",
  learned_borrowing_from: "scholarly borrowing",
  semi_learned_borrowing_from: "semi-learned borrowing",
  unadapted_borrowing_from: "direct borrowing",
  orthographic_borrowing_from: "spelling borrowing",
  cognate_of: "same root as",
  doublet_with: "doublet of",
  etymologically_related_to: "related to",
  same_root: "same root as",
};

// Edge style categories
const EVOLUTION_EDGES = new Set(["inherited_from", "derived_from", "has_root"]);
const BORROWING_EDGES = new Set([
  "borrowed_from",
  "learned_borrowing_from",
  "semi_learned_borrowing_from",
  "unadapted_borrowing_from",
  "orthographic_borrowing_from",
]);
const COGNATE_EDGES = new Set([
  "cognate_of",
  "same_root",
  "doublet_with",
  "etymologically_related_to",
]);

function getEdgeStyle(reltype) {
  if (EVOLUTION_EDGES.has(reltype)) return { dasharray: "none", width: 2 };
  if (BORROWING_EDGES.has(reltype)) return { dasharray: "8,4", width: 2 };
  if (COGNATE_EDGES.has(reltype)) return { dasharray: "3,3", width: 2 };
  return { dasharray: "none", width: 1.5 };
}

// Era-based color coding
const ERA_COLORS = {
  proto: "#c8a830",
  ancient: "#a07840",
  medieval: "#7a6850",
  modern: "#5a8a6a",
};

const ANCIENT_LANGS = new Set([
  "ang",
  "la",
  "lla",
  "grc",
  "sa",
  "cu",
  "non",
  "fro",
  "xno",
  "goh",
  "osx",
  "odt",
  "peo",
  "xcl",
  "la-lat",
]);

const MEDIEVAL_LANGS = new Set([
  "enm",
  "frm",
  "gmh",
  "gml",
  "dum",
  "orv",
  "la-med",
  "la-new",
]);

function getEraColor(lang) {
  if (lang.endsWith("-pro")) return ERA_COLORS.proto;
  if (ANCIENT_LANGS.has(lang)) return ERA_COLORS.ancient;
  if (MEDIEVAL_LANGS.has(lang)) return ERA_COLORS.medieval;
  return ERA_COLORS.modern;
}

const NODE_RADIUS = {
  input: 10,
  ancestor: 14,
  intermediate: 7,
};

// Tooltip
let tooltip = document.getElementById("graph-tooltip");
if (!tooltip) {
  tooltip = document.createElement("div");
  tooltip.id = "graph-tooltip";
  tooltip.className = "graph-tooltip";
  document.body.appendChild(tooltip);
}

function getNodeDescription(d) {
  const langName = LANG_NAMES[d.lang] || d.lang;
  if (d.type === "ancestor")
    return "Proto-root \u2014 the oldest known ancestor of these words";
  if (d.type === "input")
    return `Modern ${langName} word you searched for`;
  return `Historical ${langName} form \u2014 an intermediate step in the word's evolution`;
}

function showTooltip(event, d) {
  const langName = LANG_NAMES[d.lang] || d.lang;
  let html = `<strong>${d.term}</strong> <span class="tooltip-lang">(${langName})</span>`;
  html += `<div class="tooltip-desc">${getNodeDescription(d)}</div>`;
  if (d.translations && Object.keys(d.translations).length > 0) {
    const trans = Object.entries(d.translations)
      .slice(0, 4)
      .map(
        ([lang, term]) =>
          `${term} <span class="tooltip-lang">(${LANG_NAMES[lang] || lang})</span>`
      )
      .join(", ");
    html += `<div class="tooltip-trans">Modern reflexes: ${trans}</div>`;
  }
  tooltip.innerHTML = html;
  tooltip.style.display = "block";
  positionTooltip(event);
}

function positionTooltip(event) {
  const pad = 12;
  let x = event.pageX + pad;
  let y = event.pageY + pad;
  const rect = tooltip.getBoundingClientRect();
  if (x + rect.width > window.innerWidth) x = event.pageX - rect.width - pad;
  if (y + rect.height > window.innerHeight)
    y = event.pageY - rect.height - pad;
  tooltip.style.left = x + "px";
  tooltip.style.top = y + "px";
}

function hideTooltip() {
  tooltip.style.display = "none";
}

function renderGraph(data) {
  const svg = d3.select("#graph");
  svg.selectAll("*").remove();

  const container = document.getElementById("graph-container");
  const width = container.clientWidth;
  const height = 500;

  svg.attr("viewBox", `0 0 ${width} ${height}`);

  // Arrow marker
  svg
    .append("defs")
    .append("marker")
    .attr("id", "arrowhead")
    .attr("viewBox", "0 -5 10 10")
    .attr("refX", 20)
    .attr("refY", 0)
    .attr("markerWidth", 6)
    .attr("markerHeight", 6)
    .attr("orient", "auto")
    .append("path")
    .attr("d", "M0,-5L10,0L0,5")
    .attr("fill", "#5a4428");

  const g = svg.append("g");

  // Zoom
  const zoom = d3
    .zoom()
    .scaleExtent([0.3, 4])
    .on("zoom", (event) => g.attr("transform", event.transform));
  svg.call(zoom);

  // Simulation
  const simulation = d3
    .forceSimulation(data.nodes)
    .force(
      "link",
      d3
        .forceLink(data.links)
        .id((d) => d.id)
        .distance(120)
    )
    .force("charge", d3.forceManyBody().strength(-400))
    .force("center", d3.forceCenter(width / 2, height / 2))
    .force("collision", d3.forceCollide().radius(30));

  // Links with edge style categories
  const link = g
    .append("g")
    .selectAll("line")
    .data(data.links)
    .join("line")
    .attr("class", "link")
    .attr("stroke", "#3d2e1a")
    .attr("stroke-width", (d) => getEdgeStyle(d.reltype).width)
    .attr("stroke-dasharray", (d) => getEdgeStyle(d.reltype).dasharray)
    .attr("marker-end", (d) =>
      COGNATE_EDGES.has(d.reltype) ? "none" : "url(#arrowhead)"
    );

  // Link labels with human-readable names
  const linkLabel = g
    .append("g")
    .selectAll("text")
    .data(data.links)
    .join("text")
    .attr("class", "link-label")
    .text((d) => HUMAN_LABELS[d.reltype] || d.reltype.replace(/_/g, " "));

  // Node groups
  const node = g
    .append("g")
    .selectAll("g")
    .data(data.nodes)
    .join("g")
    .call(
      d3
        .drag()
        .on("start", (event, d) => {
          if (!event.active) simulation.alphaTarget(0.3).restart();
          d.fx = d.x;
          d.fy = d.y;
        })
        .on("drag", (event, d) => {
          d.fx = event.x;
          d.fy = event.y;
        })
        .on("end", (event, d) => {
          if (!event.active) simulation.alphaTarget(0);
          d.fx = null;
          d.fy = null;
        })
    );

  // Tooltip events
  node
    .on("mouseenter", (event, d) => showTooltip(event, d))
    .on("mousemove", (event) => positionTooltip(event))
    .on("mouseleave", () => hideTooltip());

  // Type-specific node rendering with era colors
  const ancestors = node.filter((d) => d.type === "ancestor");

  // Sun-ray lines (8 rays) — always gold for visual distinction
  for (let i = 0; i < 8; i++) {
    const angle = (i * Math.PI * 2) / 8;
    const x1 = Math.cos(angle) * 18;
    const y1 = Math.sin(angle) * 18;
    const x2 = Math.cos(angle) * 28;
    const y2 = Math.sin(angle) * 28;
    ancestors
      .append("line")
      .attr("x1", x1)
      .attr("y1", y1)
      .attr("x2", x2)
      .attr("y2", y2)
      .attr("stroke", "#c8a830")
      .attr("stroke-width", 1.2)
      .attr("opacity", 0.35);
  }

  // Dashed outer ring
  ancestors
    .append("circle")
    .attr("r", 20)
    .attr("fill", "none")
    .attr("stroke", "#c8a830")
    .attr("stroke-width", 1)
    .attr("stroke-dasharray", "3,3")
    .attr("opacity", 0.4);

  // Main circle with glow — era-colored
  ancestors
    .append("circle")
    .attr("r", NODE_RADIUS.ancestor)
    .attr("fill", (d) => getEraColor(d.lang))
    .attr("filter", "url(#glow-gold)");

  // Input nodes: era-colored circle + amber glow
  const inputs = node.filter((d) => d.type === "input");
  inputs
    .append("circle")
    .attr("r", NODE_RADIUS.input)
    .attr("fill", (d) => getEraColor(d.lang))
    .attr("filter", "url(#glow-amber)");

  // Intermediate nodes: era-colored circle, no glow
  const intermediates = node.filter((d) => d.type === "intermediate");
  intermediates
    .append("circle")
    .attr("r", NODE_RADIUS.intermediate)
    .attr("fill", (d) => getEraColor(d.lang));

  // Term labels
  node
    .append("text")
    .attr("class", "node-label")
    .attr("dy", -16)
    .text((d) => d.term);

  // Language labels
  node
    .append("text")
    .attr("class", "lang-label")
    .attr("dy", (d) => (NODE_RADIUS[d.type] || 7) + 14)
    .text((d) => LANG_NAMES[d.lang] || d.lang);

  // Translation labels for ancestor/intermediate nodes
  node
    .filter((d) => d.translations && Object.keys(d.translations).length > 0)
    .append("text")
    .attr("class", "translation-label")
    .attr("dy", (d) => (NODE_RADIUS[d.type] || 7) + 26)
    .text((d) => {
      const entries = Object.entries(d.translations).slice(0, 3);
      return entries.map(([, term]) => term).join(", ");
    });

  // Tick
  simulation.on("tick", () => {
    link
      .attr("x1", (d) => d.source.x)
      .attr("y1", (d) => d.source.y)
      .attr("x2", (d) => d.target.x)
      .attr("y2", (d) => d.target.y);

    linkLabel
      .attr("x", (d) => (d.source.x + d.target.x) / 2)
      .attr("y", (d) => (d.source.y + d.target.y) / 2);

    node.attr("transform", (d) => `translate(${d.x},${d.y})`);
  });

  // Initial zoom to fit
  setTimeout(() => {
    svg.call(zoom.transform, d3.zoomIdentity);
  }, 100);
}

function renderSplitGraphs(graphA, graphB) {
  const nodes = [];
  const links = [];
  const seenIds = new Set();

  [graphA, graphB].forEach((g) => {
    if (!g) return;
    g.nodes.forEach((n) => {
      if (!seenIds.has(n.id)) {
        seenIds.add(n.id);
        nodes.push(n);
      }
    });
    links.push(...g.links);
  });

  if (nodes.length === 0) return;
  renderGraph({ nodes, links });
}
