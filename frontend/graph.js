const LANG_NAMES = {
  en: "English",
  ru: "Russian",
  "ine-pro": "Proto-Indo-European",
  "gem-pro": "Proto-Germanic",
  "sla-pro": "Proto-Slavic",
  "ine-bsl-pro": "Proto-Balto-Slavic",
  "iir-pro": "Proto-Indo-Iranian",
  ang: "Old English",
  enm: "Middle English",
  la: "Latin",
  grc: "Ancient Greek",
  cu: "Old Church Slavonic",
  orv: "Old East Slavic",
  non: "Old Norse",
  fro: "Old French",
  frm: "Middle French",
  sa: "Sanskrit",
  goh: "Old High German",
};

const NODE_COLORS = {
  input: "#6c8cff",
  ancestor: "#f0c040",
  intermediate: "#666680",
};

const NODE_RADIUS = {
  input: 8,
  ancestor: 12,
  intermediate: 6,
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
    .attr("fill", "#2a2a3a");

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
    .attr("stroke", "#2a2a3a")
    .attr("stroke-width", 1.5)
    .attr("marker-end", "url(#arrowhead)");

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

  // Node circles
  node
    .append("circle")
    .attr("r", (d) => NODE_RADIUS[d.type] || 6)
    .attr("fill", (d) => NODE_COLORS[d.type] || "#666")
    .attr("stroke", (d) => (d.type === "ancestor" ? "#f0c040" : "none"))
    .attr("stroke-width", (d) => (d.type === "ancestor" ? 3 : 0))
    .attr("stroke-opacity", 0.3);

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
    .attr("dy", (d) => (NODE_RADIUS[d.type] || 6) + 14)
    .text((d) => LANG_NAMES[d.lang] || d.lang);

  // Translation labels for ancestor/intermediate nodes
  node
    .filter((d) => d.translations && Object.keys(d.translations).length > 0)
    .append("text")
    .attr("class", "translation-label")
    .attr("dy", (d) => (NODE_RADIUS[d.type] || 6) + 26)
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
  // Merge both graphs into a single dataset and let D3 force simulation
  // naturally separate the disconnected components
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
