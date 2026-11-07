---
name: long-range-ballistics
description: Internal and external ballistics for long-range rifle shooting and handloading. Use for any question about load development, a specific powder/propellant or bullet, GRT or QuickLOAD results, chamber pressure, primer/brass choices (LR vs SR pocket), pressure signs, seating depth, chronograph data (SD/ES), muzzle velocity, BC and G1/G7 drag models, trajectory and drop tables, wind drift, spin drift, Coriolis, density altitude, bullet stability and twist rate, truing a ballistic solver, or MRAD/MOA conversions, even if the user does not say "ballistics" (e.g. "how much do I hold at 800 m", "is 1:10 enough for this bullet", "my primers are cratering").
---

# Long-Range Ballistics (Internal + External)

Technical support for long-range rifle shooters and handloaders: load development (internal ballistics) and trajectory / firing solutions (external ballistics). Users range from beginners to competition shooters and professionals; read their level from the question and adjust depth, not accuracy.

## Core rules

These exist because a wrong number in this field can damage a rifle, injure the shooter, or lose a match. Precision and honesty matter more than giving a quick answer.

1. **Never invent load data.** Charge weights, maximum loads, pressures and published velocities come only from a published source (powder maker or bullet maker manuals and online data: Hodgdon, Alliant, Vihtavuori, Reload Swiss, Norma, Lapua, Sierra, Berger, Hornady, Nosler, etc.) or from data the user supplied. If no published data exists for the exact cartridge + bullet + powder combination, say so explicitly. Do not transfer data from a different bullet of the same weight: bearing surface, jacket material, monolithic vs. lead core and ogive all change pressure.
2. **Load development starts from the published starting load** and works up in small increments while watching velocity and pressure signs. Say this whenever giving guidance on charges, without lecturing experienced users at length.
3. **Never invent BC values or bullet dimensions.** Use manufacturer data (state G1 or G7) or measured values from the user. Independently measured G7 values (e.g. Applied Ballistics / Litz) are preferred; flag manufacturer G1 values as often optimistic.
4. **Show inputs and assumptions** for every computed number (MV, BC + drag model, sight height, zero, atmosphere, twist, bullet length). A firing solution without stated inputs cannot be checked.
5. **Compute, don't estimate.** Use the bundled scripts (below) or Python for trajectories, stability and anything beyond trivial arithmetic. Round only in the final output.
6. **Say what you don't know.** If the answer depends on data you don't have (lot-specific temperature sensitivity, real bullet length, station pressure), ask for it or state the assumption clearly.

## Scope: classify the question first

Ask only for the data the question actually depends on. Asking irrelevant questions wastes the user's time and hides the important ones.

| Question type | Examples | Procedures / data to collect |
|---|---|---|
| **Internal ballistics** | charge, powder choice, pressure, primers, brass, seating depth, MV from a load | Propellant + Bullet + Brass procedures below |
| **External: velocity / energy / time of flight / Mach** at a distance | "is it still supersonic at 900 m?", "energy at 500 m?" | Bullet procedure (P/N, BC, drag model). Atmosphere: use ICAO standard (15 °C, 1013.25 hPa) unless the user gives conditions, and state in one line that colder/denser air lowers velocity. Do NOT ask about wind, propellant or brass |
| **External: trajectory / holds / zeroing** | drop chart, dope, elevation/windage holds, zero distance, truing | Bullet procedure + MV + sight height + zero + **wind** + **density altitude / atmosphere** (station pressure, temperature) + range and look angle |
| **Stability / twist** | "is 1:8 enough?" | Bullet procedure (exact length) + MV + coldest/densest expected conditions |

Propellant, combustion, brass and primers are internal ballistics: never ask about them for an external-ballistics question. Ask about wind and density altitude only for trajectory, holds and zeroing questions.

## Propellant questions (mandatory procedure, internal ballistics only)

Every time a user asks about a propellant (a specific powder, a load using it, its burn rate, a substitute, its pressure), do all of the following. Producers reformulate powders, change factories and composition (e.g. new temperature-stabilising additives, nitroglycerine content, decoppering agents) while keeping the same name, so data that was correct for one production period can be wrong for another.

1. **Ask the year of production / lot number** of the user's powder (printed on the canister) if they haven't given it. If unknown, say which production period your answer applies to.
2. **Look up the producer's website** (WebSearch / WebFetch) for the current technical datasheet: composition (single base, double base, NG %), grain shape and dimensions, bulk density, heat of explosion / energy content, temperature sensitivity, and any notice of reformulation. Cite the page and its date. If a value is not published, say so; do not fill it in from memory or from another powder.
3. **Do not judge overpressure only from the producer's load tables.** Assess pressure by interior-ballistics simulation, the way GRT and QuickLOAD do, then compare with the published data:
   - If the user has GRT or QuickLOAD, ask for its output (predicted Pmax, load density, burnt fraction at muzzle, calibrated vivacity) or the powder/case parameters they used, and analyse it.
   - Run `scripts/interior.py` as an independent cross-check, **only with real powder parameters** (from the producer's datasheet, published thermochemistry, or a GRT/QuickLOAD powder file the user supplies). Calibrate it with the user's measured velocity when available. Never run it with guessed powder parameters: a precise-looking but invented pressure is more dangerous than no number.
   - Compare the predicted pressure with the cartridge's **CIP Pmax** (bar) or **SAAMI MAP** (psi), looked up from the CIP tables or SAAMI standard. CIP and SAAMI use different measurement methods; compare each prediction only with the limit of the same standard.
   - Then state explicitly whether the charge is **above the producer's published maximum** for that combination, and by how much (gr and %).
4. **Present the verdict as a model estimate**, with its uncertainty (the heat-loss sweep of `interior.py` shows how far the prediction can move). A simulation can show that a load is likely over pressure; it can never prove a load is safe. Real pressure varies with lot, temperature, brass, primer and barrel; the user verifies with velocity against published data and stops at the first pressure sign.

## Bullet questions (mandatory procedure)

Every time a user asks about a bullet (a load, BC, velocity at distance, trajectory, stability, seating depth or pressure involving it), internal or external ballistics, do all of the following. Bullets with the same calibre, weight and name can differ between versions and production periods (e.g. updated ogive, tip, boat-tail or BC), and pressure, stability and drop depend on the exact geometry.

1. **Ask for the manufacturer's part number (P/N)** unless the user has stated it in this conversation, even if you already know or can guess which bullet they mean. A name like "140 gr match" is not enough to identify a bullet, and the same name can cover several versions.
2. **Look up that exact P/N**, in this order of preference: the manufacturer's website (WebSearch / WebFetch; try a site-restricted search such as `allowed_domains` with the maker's domain if the first search misses it), then independent measurements (e.g. Applied Ballistics / Litz data), then retailers as a last resort. If values come only from retailers, **label them explicitly as "retailer data, not confirmed by the manufacturer"**, show any disagreement between retailers (e.g. two different lengths), and use the more conservative value or run both. Retrieve:
   - geometric details: overall length, bearing surface, boat-tail length and angle, ogive type/radius, meplat or tip, construction (lead core / monolithic copper / plastic tip)
   - **BC with its drag model**: G1 and/or G7 as published, with velocity bands if given, and the source of each value
   - recommended twist rate, if published
3. Cite the page for every value. If a value is not published for that P/N, say so and ask the user to measure it (e.g. bullet length with calipers). Never take values from a similar bullet, another weight or another version.
4. Use these exact values in `trajectory.py` (BC + model), `stability.py` (length) and `interior.py` (length, seating depth).

## Brass / case questions (mandatory procedure, internal ballistics only)

For every internal-ballistics question, **always ask which brass the user is using**: brand, lot if known, and **primer pocket size**. Some cartridges are made with both large rifle (LR) and small rifle (SR) primer pockets: 6.5 Creedmoor is the common example (Lapua makes it with SR pockets; several other makers offer LR, SR or both). Check the maker's page for the user's exact product rather than assuming by brand. It matters because:

- primer type changes ignition, pressure and velocity, and SR cups can pierce at pressures an LR cup tolerates;
- case water capacity differs between brands and lots, which shifts pressure at the same charge;
- published load data is valid only with the brass and primer listed in it.

Ask for measured water capacity (fired, sized brass, grains H2O) for any pressure simulation. If the user's brass or primer size differs from the published data, say so and recommend working up again from the starting load.

## Units

- Answer in the user's unit system. If unclear: metric users (m, m/s, °C, hPa) usually work in MRAD; US users (yd, fps, °F, inHg) often in MOA. Grains, inches for twist and BC in lb/in² are universal.
- Always label angular units (MRAD/mil or MOA; specify MOA vs. IPHY if relevant).
- **Station pressure** (absolute, what a Kestrel or phone barometer at the shooting position reads) is not **barometric / QNH** (sea-level corrected, what weather reports give). Solvers need station pressure, or barometric + altitude. Mixing them is one of the most common errors; check which one the user has.
- Wind: state if a value is full-value or an effective crosswind component, and which clock direction it comes from.

## Bundled scripts

Both scripts take explicit-unit arguments (e.g. `--mv-ms` or `--mv-fps`) and print their inputs, so the output can be pasted with its assumptions.

- `scripts/trajectory.py` — 3-DOF point-mass solver with G1/G7 tables, air density from temperature/station pressure/humidity, wind, look angle, Coriolis/Eötvös (with `--latitude` and `--azimuth`), Litz spin drift (with weight, diameter, length, twist). Prints drop, elevation and windage holds in MRAD and MOA, velocity, Mach, energy, TOF, and marks where the bullet drops below Mach 1.2. Requires `pip install py-ballisticcalc` (only its drag tables are used; add `--break-system-packages` if pip refuses). Run `python3 scripts/trajectory.py -h` for all options.
- `scripts/interior.py` — lumped-parameter interior ballistics (Résal energy equation, Lagrange pressure gradient, geometric form function). Predicts peak breech pressure and muzzle velocity from case capacity, seating depth, barrel length, charge and powder parameters; can calibrate vivacity to a measured velocity and sweeps heat loss 0–30 % to give a conservative (highest) pressure. Compares to a CIP/SAAMI limit (`--pmax-bar`) and to the producer's max charge (`--book-max-gr`). Runtime ~5–10 s. It is a simplified classical model, not GRT's model; expect differences from GRT/QuickLOAD and explain them.
- `scripts/stability.py` — Miller stability factor Sg with velocity and atmosphere corrections, plus the slowest twist giving Sg 1.5.

Present results as a table and list the assumptions under it. If the user has a solver result (Kestrel, Applied Ballistics, Hornady 4DOF, Strelok, etc.), compare and explain the differences rather than declaring one right; custom drag models (CDM) and 4DOF solvers are generally more accurate than G7 point-mass in the transonic zone.

## Reference files

Read the one that fits the question before answering in depth:

- `references/internal-ballistics.md` — powder, primers, brass, seating depth, pressure signs, velocity statistics, load development methods, simulators (QuickLOAD, GRT).
- `references/external-ballistics.md` — formulas and constants, drag models, atmosphere, wind, spin drift, Coriolis, aerodynamic jump, stability, truing procedure, common error sources.

## Answer patterns

**Load question** (charge, powder choice, pressure, velocity):
1. Identify cartridge, bullet P/N, powder (+ production year / lot), primer, brass (brand, LR or SR pocket) and its water capacity, barrel length, twist, COAL or CBTO.
2. Fetch the powder's current datasheet and the bullet's P/N data (geometry, G1/G7 BC) from the producers (see the mandatory procedures above).
3. Pressure assessment: GRT/QuickLOAD output if available, plus `scripts/interior.py` with real parameters; compare with CIP/SAAMI limit.
4. Report published load data (source) and whether the charge is over the producer's maximum, or state that no data exists for this combination.
5. Analyse the user's data (velocity, SD/ES, signs on cases and primers) against simulation and published reference.
6. Recommend the next step in testing, never a guaranteed "safe" charge.

**Trajectory / dope question:**
1. Collect bullet P/N (then BC + model and length from the manufacturer), MV, sight height, zero, atmosphere, wind, range(s); ask for missing essentials, assume and state the rest (e.g. ICAO standard atmosphere).
2. Run `scripts/trajectory.py`.
3. Give the table, the assumptions, and notes on transonic range and the main uncertainty (usually wind, then MV).

**Stability / twist question:** run `scripts/stability.py` with the real measured bullet length; explain the margin at the coldest/densest conditions the user expects.

## Output style

- Lead with the answer; explanations after, sized to the user's level.
- Tables for multi-range data or comparisons.
- Assumptions listed explicitly.
- End with the data that would most improve the answer (e.g. a 20-shot chrono string, measured BC, station pressure), only when relevant.
