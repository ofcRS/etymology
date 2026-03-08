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

const NODE_COLORS = {
  input: "#8b6530",
  ancestor: "#c8a830",
  intermediate: "#5a4428",
};

const NODE_RADIUS = {
  input: 10,
  ancestor: 14,
  intermediate: 7,
};

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

  // Links
  const link = g
    .append("g")
    .selectAll("line")
    .data(data.links)
    .join("line")
    .attr("class", "link")
    .attr("stroke", "#3d2e1a")
    .attr("stroke-width", 1.5)
    .attr("stroke-dasharray", (d) => ["same_root", "cognate_of"].includes(d.reltype) ? "5,3" : "none")
    .attr("marker-end", (d) => ["same_root", "cognate_of"].includes(d.reltype) ? "none" : "url(#arrowhead)");

  // Link labels
  const linkLabel = g
    .append("g")
    .selectAll("text")
    .data(data.links)
    .join("text")
    .attr("class", "link-label")
    .text((d) => d.reltype.replace(/_/g, " "));

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

  // Type-specific node rendering
  // Ancestor nodes: gold circle + glow + dashed outer ring + sun rays
  const ancestors = node.filter((d) => d.type === "ancestor");

  // Sun-ray lines (8 rays)
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

  // Main circle with glow
  ancestors
    .append("circle")
    .attr("r", NODE_RADIUS.ancestor)
    .attr("fill", NODE_COLORS.ancestor)
    .attr("filter", "url(#glow-gold)");

  // Input nodes: bronze circle + amber glow
  const inputs = node.filter((d) => d.type === "input");
  inputs
    .append("circle")
    .attr("r", NODE_RADIUS.input)
    .attr("fill", NODE_COLORS.input)
    .attr("filter", "url(#glow-amber)");

  // Intermediate nodes: muted wood circle, no glow
  const intermediates = node.filter((d) => d.type === "intermediate");
  intermediates
    .append("circle")
    .attr("r", NODE_RADIUS.intermediate)
    .attr("fill", NODE_COLORS.intermediate);

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
