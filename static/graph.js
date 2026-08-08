// =========================
// NOESIS — CONNECTION MAP
// =========================

const GRAPH = JSON.parse(
    document.getElementById("graph-data").textContent
);


const SVG_NS = "http://www.w3.org/2000/svg";

const PAD_X = 120;
const PAD_Y = 24;

const panel = document.getElementById("graph-panel");
const edgeGroup = document.getElementById("graph-edges");
const nodeGroup = document.getElementById("graph-nodes");


// Lay concepts out in one wedge per region, two radii deep.

const pos = {};

GRAPH.regions.forEach(function (r, ri) {

    const list = GRAPH.nodes.filter(function (n) { return n.region === r.id; });

    const base = (ri / GRAPH.regions.length) * Math.PI * 2 - Math.PI / 2;

    list.forEach(function (n, i) {

        const spread = (i - (list.length - 1) / 2) * (list.length > 3 ? 0.3 : 0.5);

        const angle = base + spread;

        const radius = 150 + (i % 2) * 72;

        pos[n.id] = {
            x: 500 + Math.cos(angle) * radius * 1.5,
            y: 280 + Math.sin(angle) * radius
        };

    });

});


GRAPH.edges.forEach(function (e) {

    const a = pos[e.from];
    const b = pos[e.to];

    if (!a || !b) return;

    const line = document.createElementNS(SVG_NS, "line");

    line.setAttribute("x1", a.x);
    line.setAttribute("y1", a.y);
    line.setAttribute("x2", b.x);
    line.setAttribute("y2", b.y);

    line.setAttribute("stroke", e.cross ? e.colour : "#232C37");
    line.setAttribute("opacity", e.cross ? 0.38 : 0.55);

    edgeGroup.appendChild(line);

});


GRAPH.nodes.forEach(function (n) {

    const p = pos[n.id];

    if (!p) return;

    const c = document.createElementNS(SVG_NS, "circle");

    c.setAttribute("cx", p.x);
    c.setAttribute("cy", p.y);
    c.setAttribute("r", 7);
    c.setAttribute("fill", n.colour);
    c.style.cursor = "pointer";

    c.addEventListener("click", function () {
        window.location.href = "/resource/" + n.id;
    });

    nodeGroup.appendChild(c);


    // Labels are HTML, positioned over the SVG so they stay crisp
    // and never inherit the non-uniform viewBox scaling.

    const right = p.x >= 500;

    const label = document.createElement("div");

    label.className = "glabel";
    label.textContent = n.title;

    label.style.left =
        "calc(" + PAD_X + "px + " + (p.x / 1000 * 100) + "% - " + (2 * PAD_X * p.x / 1000) + "px)";

    label.style.top =
        "calc(" + PAD_Y + "px + " + (p.y / 560 * 100) + "% - " + (2 * PAD_Y * p.y / 560) + "px)";

    label.style.transform =
        "translate(" + (right ? "13px" : "calc(-100% - 13px)") + ",-50%) " +
        "translateY(" + (n.id % 2 ? "-9px" : "9px") + ")";

    panel.appendChild(label);

});
