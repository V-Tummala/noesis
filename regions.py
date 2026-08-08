# =========================
# REGION TAXONOMY
# =========================
# Six regions of the brain landing page. Each maps to a lobe path in
# templates/index.html and a colour token in static/style.css.

REGIONS = [
    {
        "id": "pure",
        "name": "Pure Maths",
        "label": "PURE MATHS",
        "colour": "#4CC9F0",
        "subject": "Maths",
        "blurb": "Algebra, sequences, calculus and proof \u2014 the substrate everything else is written in."
    },
    {
        "id": "mech",
        "name": "Mechanics",
        "label": "MECHANICS",
        "colour": "#F7A44B",
        "subject": "Physics",
        "blurb": "Kinematics, forces, momentum and rotation. The densest region of the corpus."
    },
    {
        "id": "waves",
        "name": "Waves & Optics",
        "label": "WAVES & OPTICS",
        "colour": "#B69CFF",
        "subject": "Physics",
        "blurb": "Oscillation, superposition, refraction. Shares more structure with electromagnetism than most members expect."
    },
    {
        "id": "em",
        "name": "Electricity & Magnetism",
        "label": "ELECTRICITY & MAGNETISM",
        "colour": "#58D9A3",
        "subject": "Physics",
        "blurb": "Circuits, fields and induction \u2014 the region with the most links leaving it."
    },
    {
        "id": "thermo",
        "name": "Thermo & Materials",
        "label": "THERMO & MATERIALS",
        "colour": "#FF7A7A",
        "subject": "Physics",
        "blurb": "Energy transfer, gas laws, stress and strain. Where ESAT physics meets real airframe decisions."
    },
    {
        "id": "aero",
        "name": "Applied Aero",
        "label": "APPLIED AERO",
        "colour": "#E8E3D6",
        "subject": "Other",
        "blurb": "Helios-specific: lift, drag, nozzle flow, stability. Off-syllabus, but the reason the tool exists."
    }
]


REGION_BY_ID = {
    r["id"]: r
    for r in REGIONS
}


def region_name(region_id):

    r = REGION_BY_ID.get(region_id)

    return r["name"] if r else "Unassigned"


def region_colour(region_id):

    r = REGION_BY_ID.get(region_id)

    return r["colour"] if r else "#6B7684"
