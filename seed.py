"""
Seed the Noesis corpus from the Helios CubeSat CDR.

Every entry below is a maths or physics concept that the CDR actually
depends on, written up as a concept note, tagged by region and syllabus,
and cross-linked the way a member would link them by hand.

Usage:

    python seed.py                 # upload notes to R2 + insert rows
    python seed.py --no-upload     # database only (no R2 traffic)
    python seed.py --wipe          # remove previously seeded entries first

Requires R2_ACCESS_KEY and R2_SECRET_KEY in the environment, same as app.py.
"""

import os
import sys
import uuid
import io

from werkzeug.security import generate_password_hash

from database import connect, create_tables


R2_BUCKET = "noesis-files"

SEED_MARKER = "[seed:cdr]"


# =========================
# CONTRIBUTOR
# =========================
# Everything is uploaded by one account.

CONTRIBUTOR = (
    "Vanshika Tummala",
    "vrtummala02@gmail.com"
)


# =========================
# CORPUS
# =========================
# key, region, subject, syllabus, title, formula, author, body, links

CONCEPTS = [

    # ---------- PURE MATHS ----------

    ("logs", "pure", "Maths", "TMUA",
     "Logarithms and decibel arithmetic",
     "L(dB) = 10 log10(P1 / P0)",
     "comms",
     "Every line of the link budget is a logarithm. Working in decibels turns the "
     "multiplication of gains and losses into addition, which is why the CDR link "
     "budget can be summed down a column: 33 dBm transmit, +5.11 dBi antenna gain, "
     "-1.5 dB cable loss, -160.30 dB free-space path loss. A 3 dB change is a factor "
     "of two in power; a 10 dB change is a factor of ten. Read the S-band margin of "
     "5.61 dB as 'roughly 3.6x more received power than the demodulator needs'.",
     ["fspl", "ebn0"]),

    ("smallangle", "pure", "Maths", "TMUA",
     "Small-angle approximation and arcseconds",
     "tan θ ≈ θ (radians) for θ << 1",
     "orbit",
     "Pointing and orbit-knowledge budgets are quoted in degrees, arcminutes and "
     "arcseconds, and converted between angular and linear error with the small-angle "
     "approximation. The CDR states 1 km of GNSS orbit knowledge error at 500 km is "
     "about 0.009° ≈ 32 arcseconds; that conversion is θ ≈ s / r with θ in radians. "
     "The same step turns the 0.15° residual pointing error into a ground offset at "
     "500 km altitude when checking the 16 m GSD requirement.",
     ["gsd", "pointing"]),

    ("calculus", "pure", "Maths", "TMUA",
     "Differentiation and integration as rate and accumulation",
     "F = dp/dt,  W = ∫ F · ds,  ΔQ = ∫ I dt",
     "systems",
     "One pair of operations underlies most of the spacecraft's physics. "
     "Differentiation gives rates: momentum change into force, flux change into emf, "
     "charge flow into current. Integration accumulates: force over distance into "
     "work, current over time into charge, power over time into the watt-hours in the "
     "energy budget. The 22.29 Wh consumed per 1.5-hour orbit is exactly the integral "
     "of the 14.86 W orbit-average power over one orbital period.",
     ["newton2", "energybudget", "induction"]),

    ("vectors", "pure", "Maths", "TMUA",
     "Vectors, dot product and coordinate frames",
     "a · b = |a||b| cos θ",
     "systems",
     "The spacecraft body frame is defined in the CDR with its origin at the geometric "
     "centre, +X along velocity and -Z nadir. Every attitude statement is a rotation "
     "between that frame and an inertial or Earth-fixed one. The dot product resolves "
     "a vector onto an axis, which is how sun-sensor readings become a sun direction "
     "in body coordinates and how a commanded torque is split across three axes.",
     ["quaternions", "moments", "sunsensor"]),

    ("quaternions", "pure", "Maths", "Neither",
     "Quaternions for attitude representation",
     "q = [q0, q1, q2, q3],  |q| = 1",
     "adcs",
     "The ADCS estimator outputs an attitude quaternion rather than Euler angles. "
     "Quaternions are four numbers on the unit hypersphere: they compose rotations by "
     "multiplication, avoid gimbal lock, and normalise cheaply on a flight processor. "
     "The MEKF in the CDR estimates a small error quaternion about a reference "
     "attitude, which keeps the filter linear even though rotations are not.",
     ["vectors", "kalman", "pointing"]),

    ("statistics", "pure", "Maths", "TMUA",
     "Standard deviation and the 3-sigma convention",
     "P(|X - μ| ≤ 3σ) ≈ 99.7%",
     "systems",
     "Requirements ADCS-1 and ORB-12 are written as 3σ figures, not typical values: "
     "pointing accuracy is the 3σ total attitude error over the control window. That "
     "means the requirement is met if 99.7% of samples fall inside the bound, which is "
     "a far stronger claim than an average. Margins throughout the CDR (15% on peak "
     "currents, 20% on mass) are deterministic allowances stacked on top of this "
     "statistical one.",
     ["margins", "pointing"]),

    ("margins", "pure", "Maths", "Neither",
     "Margin arithmetic and budget stacking",
     "Margin % = (Capability - Requirement) / Requirement × 100",
     "systems",
     "The CubeSat carries 8.472 kg before margin; a 20% system margin gives 10.166 kg "
     "against a 12 kg limit, leaving 1.83 kg or 15.28% remaining. Note the two "
     "different denominators in play — margin applied to a subsystem estimate versus "
     "margin remaining against a hard limit. Mixing them is the most common budgeting "
     "error, and the reason each budget in the CDR states which one it means.",
     ["statistics", "energybudget"]),

    # ---------- MECHANICS ----------

    ("newton2", "mech", "Physics", "ESAT",
     "Newton's second law in momentum form",
     "F = dp/dt = m dv/dt",
     "systems",
     "The momentum form is the one that survives variable mass and is the honest "
     "statement of the law. For the CubeSat it governs the response to every "
     "disturbance torque and to the ejection shock of up to 1,500 g quoted in STL-3. "
     "Note that a 'g' in that requirement is an acceleration expressed as a multiple "
     "of 9.81 m/s², so the load on a 10.17 kg spacecraft at 15 g quasi-static is "
     "roughly 1.5 kN along the axis.",
     ["calculus", "quasistatic", "conservation"]),

    ("moments", "mech", "Physics", "ESAT",
     "Torque, moment of inertia and angular acceleration",
     "τ = I α,  L = I ω",
     "adcs",
     "ADCS-4 requires an angular acceleration of 1.75 × 10⁻⁴ rad/s² and ADCS-5 a "
     "torque authority of 2.1 × 10⁻⁴ N·m. Those two numbers imply a moment of inertia "
     "of about 1.2 kg·m² about the controlled axis: I = τ / α. The same relation sets "
     "the slew time to reach the 3.0°/s peak rate, and it is why the payload mass "
     "properties are controlled and reported to ADCS.",
     ["reactionwheel", "vectors", "newton2"]),

    ("conservation", "mech", "Physics", "ESAT",
     "Conservation of angular momentum",
     "L_total = constant (no external torque)",
     "adcs",
     "A reaction wheel does not create angular momentum, it borrows it. Spinning the "
     "wheel one way rotates the body the other, and the total stays fixed. This is "
     "exactly why wheels saturate: absorbing a persistent disturbance torque drives "
     "wheel speed toward its limit, and ADCS-9 caps that at 80% of rated momentum. "
     "Only an external torque can remove momentum from the system — hence "
     "magnetorquers.",
     ["reactionwheel", "magnetorquer", "newton2"]),

    ("reactionwheel", "mech", "Physics", "Neither",
     "Reaction wheel sizing and desaturation",
     "τ_w = I_w dω_w/dt,  h_w = I_w ω_w",
     "adcs",
     "The CDR selects a reaction wheel plus magnetorquer architecture over "
     "magnetorquer-only (0.8° pointing, fails ADCS-1) and CMGs (2.5 kg, 20 W, over "
     "budget). Wheels give fine control at 0.55 kg and 5.1 W. Desaturation is required "
     "at least once per 1.6 hours per ADCS-13, offloading stored wheel momentum into "
     "Earth's magnetic field.",
     ["conservation", "magnetorquer", "moments"]),

    ("quasistatic", "mech", "Physics", "ESAT",
     "Quasi-static loads, factors of safety and vibration",
     "σ_allow = σ_yield / FoS",
     "structure",
     "STL-1 requires survival of ±15 g quasi-static along each axis, STL-2 an 8.0 g RMS "
     "random vibration environment from 20–2,000 Hz, with factors of safety of 1.5 on "
     "yield and 2.0 on ultimate. A factor of safety is a divisor on allowable stress, "
     "not a multiplier on load, so 7075-T6 aluminium at 505 MPa yield is worked to "
     "about 337 MPa.",
     ["stress", "resonance", "newton2"]),

    ("drag", "mech", "Physics", "Neither",
     "Atmospheric drag and passive deorbit",
     "F_D = ½ ρ v² C_D A",
     "mech",
     "Deorbit is passive: MECH-02 deploys ≥1.00 m² of drag area so that ORB-11 is met "
     "with reentry inside 5 years and no propulsion. Drag scales with area linearly "
     "and with velocity squared, and ρ at 500 km varies by an order of magnitude with "
     "solar activity — which is why the analysis is run for low, mean and high "
     "atmosphere cases rather than a single density.",
     ["orbitalvelocity", "gaslaw", "lift"]),

    # ---------- WAVES & OPTICS ----------

    ("fspl", "waves", "Physics", "Neither",
     "Free-space path loss and the inverse square law",
     "FSPL(dB) = 20 log10(d) + 20 log10(f) + 92.45",
     "comms",
     "Power spreads over a sphere, so received power falls as 1/d². In decibels that "
     "becomes a clean sum. The CDR worst case is a 1,123 km slant range at 25° "
     "elevation: 146.12 dB at UHF and 160.30 dB at S-band. The 14 dB penalty for "
     "S-band is purely the frequency term — same geometry, shorter wavelength.",
     ["logs", "ebn0", "antennagain"]),

    ("ebn0", "waves", "Physics", "Neither",
     "Eb/N0, bit error rate and link margin",
     "Margin = Eb/N0(received) - Eb/N0(required)",
     "comms",
     "Eb/N0 is energy per bit over noise power spectral density — the quantity that "
     "actually sets bit error rate, independent of data rate. COMMS-3 demands "
     "BER ≤ 10⁻⁶, which for the chosen modulation needs about 3–4 dB. The S-band "
     "downlink delivers 8.61 dB against a 3.0 dB requirement, hence the 5.61 dB margin "
     "that satisfies COMMS-2.",
     ["fspl", "noisetemp", "logs"]),

    ("noisetemp", "waves", "Physics", "Neither",
     "System noise temperature and thermal noise",
     "N0 = k T,  k = 1.38 × 10⁻²³ J/K",
     "comms",
     "Every receiver adds noise, quantified as an equivalent temperature. The CDR "
     "assumes 500 K for the UHF chain and 300 K for S-band, giving noise spectral "
     "densities of -201.61 and -203.83 dBW/Hz. Cooling the front end or lowering the "
     "noise figure buys margin exactly as if you had increased transmit power.",
     ["ebn0", "thermalradiation"]),

    ("antennagain", "waves", "Physics", "Neither",
     "Antenna gain, beamwidth and polarisation loss",
     "G = η (4π A) / λ²",
     "comms",
     "Gain is not amplification, it is directivity: concentrating radiated power into a "
     "narrower solid angle. The 26.63 dBi ground S-band dish beats the 5.11 dBi "
     "spacecraft patch because it is electrically far larger. Narrow beams demand "
     "accurate pointing, and mismatch between transmit and receive polarisation costs "
     "further dB, which COMMS-5 requires to be actively managed.",
     ["fspl", "pointing", "doppler"]),

    ("doppler", "waves", "Physics", "ESAT",
     "Doppler shift on a LEO pass",
     "Δf = f0 (v_r / c)",
     "comms",
     "At 7.6 km/s the radial velocity component swings from positive to negative "
     "through a pass, shifting the carrier by roughly ±11 kHz at 437 MHz and ±60 kHz "
     "at 2.4 GHz. COMMS-13 requires the link to close under worst-case Doppler shift "
     "and rate, which is why the ground station pre-compensates using the orbit "
     "prediction.",
     ["orbitalvelocity", "antennagain"]),

    ("gsd", "waves", "Physics", "Neither",
     "Ground sample distance and optical resolution",
     "GSD = (p × h) / f",
     "payload",
     "GSD is set by detector pitch p, altitude h and focal length f. PAY-2 requires "
     "≤16 m at 500 km with a 32 km swath, delivered by a 2,000-pixel pushbroom array. "
     "Swath is simply GSD times the number of across-track pixels: 16 m × 2,000 = "
     "32 km. The image is built line by line from orbital motion, so along-track "
     "sampling is set by integration time and ground speed.",
     ["smallangle", "pointing", "blackbody"]),

    ("blackbody", "waves", "Physics", "ESAT",
     "Blackbody radiation and Wien's law",
     "λ_max T = 2.898 × 10⁻³ m·K",
     "payload",
     "Urban surfaces near 300 K peak at about 9.7 µm, which is precisely why the "
     "thermal payload observes the 8–14 µm band. The VNIR channel at 0.4–1 µm instead "
     "sees reflected sunlight, peaking near 500 nm for a 5,800 K Sun. Two bands, two "
     "physical processes: emission versus reflection.",
     ["thermalradiation", "gsd", "gaslaw"]),

    # ---------- ELECTRICITY & MAGNETISM ----------

    ("ohm", "em", "Physics", "ESAT",
     "Ohm's law and bus current",
     "V = IR,  P = VI",
     "power",
     "The regulated bus sits at 14.8 V nominal. Every peak load in the CDR converts "
     "straight through P = VI: imaging at 33.15 W draws 2.24 A, and with the 15% "
     "margin 2.58 A. Those currents size the harness, the switch trip thresholds and "
     "the inrush limiting demanded by PWR-18.",
     ["energybudget", "kirchhoff", "resistiveheating"]),

    ("kirchhoff", "em", "Physics", "ESAT",
     "Kirchhoff's laws as conservation statements",
     "ΣI_in = ΣI_out,  ΣV_loop = 0",
     "power",
     "The junction rule is conservation of charge; the loop rule is conservation of "
     "energy. Together they are how the power distribution unit's branch currents are "
     "predicted and how a fault current is traced when over-current protection trips a "
     "channel under PWR-16.",
     ["ohm", "conservation", "energybudget"]),

    ("energybudget", "em", "Physics", "ESAT",
     "Energy, power and depth of discharge",
     "E = P t,  DoD = E_used / E_capacity",
     "power",
     "Orbit-average load is 14.86 W, so a 1.5-hour orbit consumes 22.29 Wh. Eclipse "
     "alone is 10.3 W for 28.4% of the orbit, about 4.4 Wh — around 1.25% of a 350 Wh "
     "pack. PWR-4 caps depth of discharge at 70%, and shallow cycling is the single "
     "biggest lever on battery life over 16,000 orbits.",
     ["calculus", "ohm", "solarcell", "margins"]),

    ("solarcell", "em", "Physics", "ESAT",
     "Photovoltaic generation and MPPT",
     "P = η G A cos θ",
     "power",
     "Generation scales with the cosine of the sun incidence angle, so attitude is a "
     "power variable, not just a pointing one. PWR-2 allocates 0.06 m² of body-mounted "
     "cells; deployables were traded away to remove a deployment failure mode. PWR-25 "
     "requires maximum power point tracking because a cell's optimum operating voltage "
     "moves with temperature and illumination.",
     ["energybudget", "thermalradiation", "pn"]),

    ("pn", "em", "Physics", "Neither",
     "P-N junctions, detectors and radiation damage",
     "I = I0 (exp(qV/kT) - 1)",
     "payload",
     "The same junction physics runs the solar cells and the imaging detectors. It "
     "also explains total ionising dose: accumulated charge in oxide layers shifts "
     "threshold voltages and raises dark current. The CDR estimates 5–10 krad over the "
     "mission and selects parts rated ≥15 krad, with memory scrubbed every 60 s "
     "against single-event upsets.",
     ["solarcell", "blackbody"]),

    ("magnetorquer", "em", "Physics", "ESAT",
     "Magnetic dipole moment and torque in a field",
     "τ = m × B",
     "adcs",
     "A magnetorquer is a coil: it generates a dipole moment m and Earth's field B "
     "does the rest. ADCS-10 bounds the dipole to ±0.5 A·m² per axis and no less than "
     "±0.2 A·m². Because the torque is a cross product, no torque can be produced "
     "about the field direction itself — which is why magnetorquers alone cannot meet "
     "the pointing requirement and are paired with wheels.",
     ["reactionwheel", "induction", "vectors"]),

    ("induction", "em", "Physics", "ESAT",
     "Electromagnetic induction and Lenz's law",
     "ε = -dΦ/dt",
     "power",
     "The minus sign is a conservation argument, not a sign convention. Induction "
     "drives the switching regulators in the EPS, and the resulting ripple and "
     "switching noise is exactly what PWR-12 and PWR-35 constrain so that MPPT "
     "switching does not degrade the radio or the payload.",
     ["magnetorquer", "kirchhoff", "calculus"]),

    # ---------- THERMO & MATERIALS ----------

    ("thermalradiation", "thermo", "Physics", "ESAT",
     "Stefan-Boltzmann law and radiative balance",
     "P = ε σ A T⁴,  σ = 5.67 × 10⁻⁸ W/m²K⁴",
     "thermal",
     "In vacuum there is no convection: radiation is the only way heat leaves the "
     "spacecraft. Equilibrium temperature comes from balancing absorbed solar, albedo "
     "and Earth infrared against emitted radiation, and the fourth-power dependence is "
     "why surface finish (the α/ε ratio) is such a powerful design lever. It sets the "
     "-21.2 °C to +103.5 °C solar panel extremes in the CDR.",
     ["blackbody", "thermalcycling", "solarcell"]),

    ("gaslaw", "thermo", "Physics", "ESAT",
     "Ideal gas law and outgassing",
     "pV = nRT",
     "structure",
     "In hard vacuum, volatiles trapped in adhesives and plastics escape and "
     "re-condense on cold optics. STM-7 therefore imposes TML < 1.0% and CVCM < 0.1%. "
     "The same state relation governs the residual atmosphere at 500 km whose density "
     "drives the drag sail deorbit analysis.",
     ["drag", "thermalradiation"]),

    ("thermalcycling", "thermo", "Physics", "Neither",
     "Thermal expansion and cycle fatigue",
     "ΔL = α L ΔT",
     "thermal",
     "STER-2 demands stability through more than 16,000 orbital thermal cycles between "
     "-40 °C and +85 °C survival limits. Dissimilar materials expand at different "
     "rates, so joints see strain every orbit; TCS-02 caps gradients at 10 °C partly "
     "to limit this. Fatigue is driven by cycle count and strain range, not peak "
     "temperature alone.",
     ["stress", "thermalradiation"]),

    ("stress", "thermo", "Physics", "Neither",
     "Stress, strain and Young's modulus",
     "σ = F/A,  ε = ΔL/L,  E = σ/ε",
     "structure",
     "The primary structure is 7075-T6 aluminium at 505 MPa yield, chosen for "
     "stiffness-to-weight; secondary panels are 6061-T6. STL-7 limits deflection at "
     "the payload interface to 0.55 mm under full load, which is a stiffness "
     "requirement (E and geometry) rather than a strength one — the structure could be "
     "strong enough and still fail it.",
     ["quasistatic", "resonance", "thermalcycling"]),

    ("resonance", "thermo", "Physics", "ESAT",
     "Natural frequency and resonance avoidance",
     "f = (1/2π) √(k/m)",
     "structure",
     "STL-4 requires a fundamental natural frequency ≥100 Hz so the spacecraft does "
     "not couple with the launch vehicle's low-frequency environment. Stiffness raises "
     "it, mass lowers it — the two levers pull against each other, and adding mass to "
     "'strengthen' a structure can make the frequency requirement harder to meet.",
     ["stress", "quasistatic"]),

    # ---------- APPLIED AERO ----------

    ("orbitalvelocity", "aero", "Physics", "Neither",
     "Orbital velocity and period",
     "v = √(GM/r),  T = 2π √(r³/GM)",
     "orbit",
     "At 500 km altitude r ≈ 6,878 km, giving about 7.6 km/s and a period near 94.6 "
     "minutes — the ~1.5-hour orbit every power and data budget in the CDR is built "
     "on. Roughly 16 orbits per day follow directly, and with them the pass counts and "
     "the 26 images per day.",
     ["drag", "sso", "doppler"]),

    ("sso", "aero", "Physics", "Neither",
     "Sun-synchronous orbits and J2 nodal precession",
     "dΩ/dt = +0.9856°/day",
     "orbit",
     "Earth's oblateness (the J2 term) precesses the orbital plane. Choose altitude "
     "and inclination so that precession matches Earth's mean motion about the Sun and "
     "the local solar time of each pass stays fixed. ORB-2 fixes inclination at "
     "97.4° ± 0.03° for a 500 km orbit and ORB-3 an LTAN of 13:30 — retrograde, which "
     "is what makes the sign work out.",
     ["orbitalvelocity", "beta"]),

    ("beta", "aero", "Physics", "Neither",
     "Beta angle and eclipse fraction",
     "β = angle between orbit plane and Sun vector",
     "orbit",
     "Beta angle sets how much of each orbit is in shadow: high |β| means little or no "
     "eclipse, low β the maximum. ORB-9 caps eclipse at 36 minutes per orbit (38%) and "
     "ORB-10 requires operation from -60° to +60°. Every power and thermal worst case "
     "in the CDR is quoted at a stated beta angle for this reason.",
     ["sso", "energybudget", "thermalradiation"]),

    ("lift", "aero", "Physics", "Neither",
     "Lift from circulation (Kutta-Joukowski)",
     "L' = ρ V Γ",
     "mech",
     "Not used in orbit, but the reason the corpus exists: it is the first equation of "
     "any Helios airframe study, and it rests on the same vector calculus and momentum "
     "flux arguments as the orbital work. Circulation Γ is a line integral of velocity "
     "around the aerofoil — accumulation again, in a different coordinate system.",
     ["vectors", "drag", "calculus"]),

    ("pointing", "aero", "Physics", "Neither",
     "Pointing error budget and geolocation",
     "ground error ≈ h × tan(θ_err)",
     "adcs",
     "Raw ADCS pointing of ±0.4° maps to roughly 3.5 km of ground error at 500 km — "
     "far beyond one 16 m pixel. The CDR closes the gap not by tightening the ADCS but "
     "by combining boresight calibration, attitude knowledge of ±0.13° and ground "
     "georeferencing, bringing residual geolocation error under one pixel. A good "
     "example of a requirement met at system level rather than component level.",
     ["smallangle", "gsd", "quaternions", "kalman"]),

    ("kalman", "aero", "Maths", "Neither",
     "Kalman filtering and sensor fusion",
     "x̂ = x̂⁻ + K (z - H x̂⁻)",
     "adcs",
     "No single sensor is good enough. Gyros are precise but drift; sun sensors and "
     "magnetometers are noisy but absolute. The MEKF weights each by its uncertainty, "
     "producing an estimate better than any input — which is how ADCS-7 reaches "
     "±0.13° attitude knowledge and why ORB-14 can claim ≤500 m orbit knowledge from "
     "GNSS.",
     ["quaternions", "statistics", "sunsensor", "pointing"]),

    ("sunsensor", "aero", "Physics", "Neither",
     "Sun sensors and attitude determination geometry",
     "cos θ = (s · n)",
     "adcs",
     "A coarse sun sensor is a photodiode whose current follows the cosine of the "
     "incidence angle; several on different faces give a sun vector in body "
     "coordinates. One vector fixes only two of three degrees of freedom, so a second "
     "reference — the magnetic field — is required, which is the basis of TRIAD and of "
     "the safe-mode sun-pointing behaviour in ADCS-17.",
     ["vectors", "kalman", "solarcell"]),

    ("resistiveheating", "em", "Physics", "ESAT",
     "Resistive heating and survival heaters",
     "P = I²R",
     "thermal",
     "Heaters are just resistors, and the same relation explains harness losses. The "
     "battery must stay at or above 0 °C or it becomes inert and the mission is lost, "
     "so heater power is budgeted per mode under TCS-E3. Note that heater energy is "
     "not wasted in the thermal sense — all of it ends up as heat inside the "
     "spacecraft, which is exactly the point.",
     ["ohm", "thermalradiation", "energybudget"])
]


# =========================
# SEEDING
# =========================

def note_markdown(c):

    key, region, subject, syllabus, title, formula, author, body, links = c

    name = CONTRIBUTOR[0]

    return (
        "# " + title + "\n\n"
        "**Region:** " + region + "  \n"
        "**Syllabus:** " + syllabus + "  \n"
        "**Contributed by:** " + name + "\n\n"
        "## Canonical form\n\n"
        "    " + formula + "\n\n"
        "## Statement\n\n"
        + body + "\n\n"
        "---\n"
        "Source: Helios CubeSat Critical Design Review, issue 1/0. " + SEED_MARKER + "\n"
    )


def get_or_create_user(conn):

    name, email = CONTRIBUTOR

    row = conn.execute(
        "SELECT id FROM users WHERE email=?",
        (email,)
    ).fetchone()

    if row:
        return row["id"]

    cur = conn.execute(
        """
        INSERT INTO users (username, email, password)
        VALUES (?,?,?)
        """,
        (
            name,
            email,
            generate_password_hash(uuid.uuid4().hex)
        )
    )

    return cur.lastrowid


def main():

    upload = "--no-upload" not in sys.argv

    r2 = None

    if upload:

        import boto3

        r2 = boto3.client(
            "s3",
            endpoint_url=
            "https://b84acb151b5757fff0502ce1f1d72f05.r2.cloudflarestorage.com",
            aws_access_key_id=os.environ["R2_ACCESS_KEY"],
            aws_secret_access_key=os.environ["R2_SECRET_KEY"],
            region_name="auto"
        )


    create_tables()

    conn = connect()


    if "--wipe" in sys.argv:

        conn.execute(
            "DELETE FROM resources WHERE description LIKE ?",
            ("%" + SEED_MARKER + "%",)
        )

        conn.commit()

        print("Removed previously seeded entries.")


    ids = {}

    for c in CONCEPTS:

        key, region, subject, syllabus, title, formula, author, body, links = c


        existing = conn.execute(
            "SELECT id FROM resources WHERE title=?",
            (title,)
        ).fetchone()

        if existing:
            ids[key] = existing["id"]
            print("skip  " + title)
            continue


        filename = str(uuid.uuid4()) + "_" + key + "_note.md"

        markdown = note_markdown(c)


        if upload:

            r2.upload_fileobj(
                io.BytesIO(markdown.encode("utf-8")),
                R2_BUCKET,
                filename
            )


        user_id = get_or_create_user(conn)


        cur = conn.execute(
            """
            INSERT INTO resources
            (title, description, subject, syllabus, region, formula,
             filename, uploaded_by)
            VALUES (?,?,?,?,?,?,?,?)
            """,
            (
                title,
                body + "  " + SEED_MARKER,
                subject,
                syllabus,
                region,
                formula,
                filename,
                user_id
            )
        )

        ids[key] = cur.lastrowid

        print("added " + title)


    conn.commit()


    # Bidirectional links, matching the two-row insert used by /link

    made = 0

    for c in CONCEPTS:

        key = c[0]
        links = c[8]

        a = ids.get(key)

        if not a:
            continue

        for other in links:

            b = ids.get(other)

            if not b or a == b:
                continue

            dup = conn.execute(
                """
                SELECT 1 FROM relationships
                WHERE resource_one=? AND resource_two=?
                """,
                (a, b)
            ).fetchone()

            if dup:
                continue

            conn.execute(
                """
                INSERT INTO relationships (resource_one, resource_two)
                VALUES (?,?), (?,?)
                """,
                (a, b, b, a)
            )

            made += 1


    conn.commit()

    conn.close()


    print("")
    print("Seeded " + str(len(ids)) + " concepts and " + str(made) + " links.")
    print("Regions: pure, mech, waves, em, thermo, aero.")


if __name__ == "__main__":
    main()
