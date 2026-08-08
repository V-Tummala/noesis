// =========================
// NOESIS — BRAIN LANDING
// =========================

const DATA = JSON.parse(
    document.getElementById("brain-data").textContent
);


// Node clusters per lobe, in the 1000x660 viewBox of index.html

const NODES = {
    pure:   [[190,240],[248,300],[152,296],[276,206],[214,342]],
    mech:   [[420,192],[494,238],[386,286],[470,330],[544,190]],
    waves:  [[678,224],[724,296],[652,336],[712,368]],
    em:     [[268,430],[350,458],[440,452],[300,478]],
    thermo: [[604,452],[672,468],[700,506],[608,510]],
    aero:   [[540,530],[520,572]]
};


const SVG_NS = "http://www.w3.org/2000/svg";

const lobes = document.querySelectorAll(".lobe");

const nodeGroup = document.getElementById("brain-nodes");


function drawNodes(active) {

    nodeGroup.innerHTML = "";

    DATA.regions.forEach(function (r) {

        (NODES[r.id] || []).forEach(function (p, i) {

            const on = r.id === active;

            const c = document.createElementNS(SVG_NS, "circle");

            c.setAttribute("cx", p[0]);
            c.setAttribute("cy", p[1]);
            c.setAttribute("r", on ? 4.5 : 3);
            c.setAttribute("fill", on ? "#FFFFFF" : r.colour);
            c.setAttribute("class", "node");

            c.style.opacity = on ? 1 : 0.5;
            c.style.animationDelay = (i * 0.45) + "s";

            nodeGroup.appendChild(c);

        });

    });

}


function select(id) {

    const r = DATA.regions.find(function (x) { return x.id === id; });

    if (!r) return;

    const stats = DATA.stats[id] || { count: 0, links: 0, exam: 0, concepts: [] };


    lobes.forEach(function (l) {
        l.classList.toggle("active", l.dataset.region === id);
    });

    document.querySelectorAll(".rlabel").forEach(function (l) {
        l.style.color = l.dataset.label === id ? l.dataset.colour : "";
    });


    document.getElementById("region-dot").style.background = r.colour;
    document.getElementById("region-dot").style.boxShadow = "0 0 8px " + r.colour;

    document.getElementById("region-index").textContent =
        "0" + (DATA.regions.indexOf(r) + 1);

    document.getElementById("region-name").textContent = r.name;
    document.getElementById("region-blurb").textContent = r.blurb;

    document.getElementById("region-count").textContent = stats.count;
    document.getElementById("region-links").textContent = stats.links;
    document.getElementById("region-exam").textContent = stats.exam;

    document.getElementById("region-enter").href = "/library?region=" + r.id;


    const list = document.getElementById("region-concepts");

    list.innerHTML = "";

    if (!stats.concepts.length) {

        list.innerHTML =
            '<p class="empty" style="font-size:13px">Nothing in this region yet. ' +
            '<a href="/upload">Add the first concept.</a></p>';

        return;

    }

    stats.concepts.forEach(function (c) {

        const a = document.createElement("a");

        a.className = "mini";
        a.href = "/resource/" + c.id;

        a.innerHTML =
            '<div class="row"><span>' + c.title + '</span>' +
            '<span class="tag ' + c.syllabus + '">' + c.syllabus + '</span></div>' +
            '<div class="meta">' + c.links + ' LINKS &middot; ' + c.created + '</div>';

        list.appendChild(a);

    });

    drawNodes(id);

}


lobes.forEach(function (l) {

    l.addEventListener("click", function () {
        select(l.dataset.region);
    });

});


select(DATA.default_region);
