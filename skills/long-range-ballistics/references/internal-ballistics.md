# Internal Ballistics Reference

## Contents
1. Propellant
2. Pressure: limits, measurement, simulation
3. Pressure signs
4. Primers
5. Brass
6. Seating depth
7. Velocity statistics
8. Load development methods
9. Temperature sensitivity
10. Input checklist for `scripts/interior.py`

## 1. Propellant

- **Burn rate charts** are relative orderings only, often from closed-bomb tests in different conditions; neighbouring powders in a chart are NOT interchangeable charge-for-charge. Never transfer a charge between powders.
- **Single base** (nitrocellulose) vs **double base** (NC + nitroglycerine): double base usually has higher energy per unit mass, so a lower charge for the same velocity, and potentially more barrel throat heat.
- **Grain shape**: extruded tube (stick, usually ~neutral burning), ball/spherical (degressive unless deterred-coated), flake. Ball powders are usually denser and meter better; extruded powders often fill the case more.
- **Temperature-stabilised** lines exist from several producers; "low sensitivity" claims must be checked against the producer's own published figures for the current production.
- **Lot-to-lot variation** is normal; producers adjust lots to stay within a velocity/pressure tolerance in their reference cartridge, not in yours. A new lot means restarting from below the working charge.
- **Reformulations under the same name** happen: check the producer's website and notices for the user's production year (see SKILL.md).

## 2. Pressure: limits, measurement, simulation

- **CIP** (Europe and members): Pmax in bar, measured with a piezo transducer per CIP procedure. **SAAMI** (USA): MAP in psi, transducer method per SAAMI standard. Older SAAMI values in "CUP" (copper crusher) are a different unit, not convertible 1:1 to psi. Always look up the limit for the exact cartridge from CIP tables or the SAAMI standard; do not quote from memory.
- **Producer load data** is measured in a test barrel with specific components. Your rifle/brass/primer/lot differs, so treat a max load as a max for their test conditions.
- **Simulators** (GRT, QuickLOAD, `scripts/interior.py`) solve a lumped-parameter model: burning law + energy balance + bullet motion. Their output depends heavily on:
  - case capacity (measure water capacity of fired, sized brass; a 1 gr H2O error can shift pressure a lot)
  - seating depth / volume under the bullet
  - powder parameters (energy, burn rate/vivacity, progressivity); these are the largest uncertainty
  - shot-start pressure and heat loss
- **Calibration to velocity**: fitting the burn rate so predicted MV matches the chronograph improves the pressure prediction, but only if barrel length, capacity and charge are correct. A velocity higher than predicted for a given charge is a pressure warning.
- **Load density** (powder solid volume / free case volume): well below ~85 % with some powders raises ignition and consistency questions; above 100 % solid volume is physically impossible (check inputs). "Compressed load" in manuals refers to bulk volume, not solid volume.
- A model can flag a probable over-pressure; it cannot certify a load as safe.

## 3. Pressure signs (late and unreliable indicators)

Ejector marks/swipes, cratered or pierced primers, flattened primers, sticky or heavy bolt lift, case head expansion, loose primer pockets after few firings, blown primers, velocity well above published data for the barrel length. Absence of signs does not prove safe pressure: modern actions and brass can hide signs above Pmax. Primer appearance also depends on cup hardness and firing pin hole clearance. Stop at the first sign and drop back.

## 4. Primers

- Cup thickness/hardness matters: magnum and "BR"/military-style primers resist piercing better than soft standard cups.
- Small rifle primer brass in cartridges traditionally using large rifle primers (e.g. some 6.5 Creedmoor and .308 brass) gives different pressure and ignition behaviour; work up again when switching.
- A primer change (brand or type) requires re-working the load from below.

## 5. Brass

- Water capacity varies between brands and lots (often 1–3 gr H2O); lower capacity = higher pressure at the same charge. Measure it for the simulator.
- Sizing: shoulder bump typically 0.05–0.08 mm (0.002–0.003 in) for bolt guns; semi-autos often need more. Measure with a headspace comparator on fired and sized cases.
- Neck tension: from bushing size or mandrel; consistent tension helps SD. Annealing keeps tension consistent over firings.
- Trim to length: an over-length case can pinch the bullet in the chamber leade and raise pressure.

## 6. Seating depth

- Measure **CBTO** (base to ogive, with a comparator) for consistency; COAL (tip) varies with tip irregularity.
- Distance to lands: measure with an OAL gauge and modified case, or by seating long and chambering. Repeat 3–5 times; report method and average.
- Jam increases pressure; jump changes pressure less, but deep seating reduces case volume (raises pressure).
- Magazine length is a hard limit for repeaters.
- Throat erosion moves the lands forward over barrel life; re-measure periodically.

## 7. Velocity statistics

- SD from 5 shots has a very wide confidence interval; 10–20+ shots are needed to compare loads meaningfully.
- ES grows with sample size; SD is the more useful statistic.
- Typical goal for long range: single-digit SD in m/s (low double-digit fps), but vertical dispersion at distance is what matters: compute it with the trajectory script.
- Chronograph: confirm consistent setup (Doppler like Garmin Xero / LabRadar vs optical); Doppler devices may need angle/placement checks.

## 8. Load development methods

- **Charge ladder**: one shot per charge step, look for velocity behaviour and pressure. Statistical value of a single shot per step is low.
- **OCW (Optimal Charge Weight)**: groups at incremental charges, looking for consistent point of impact across charges.
- **Satterlee 10-shot**: looks for velocity "flat spots"; widely disputed because the flat spots are usually within chronograph and sample noise.
- **Seating depth test**: after choosing a charge, test CBTO steps (e.g. 0.25–0.5 mm).
- Whatever method: start from the published starting load, increase in small steps (≈1–2 % of charge), check for pressure signs at every step.

## 9. Temperature sensitivity

- Express as m/s per °C (or fps per °F) from the user's own chrono data at different powder temperatures; producer figures apply to their test cartridge.
- A load at max in winter may be over pressure in summer. Develop at the highest expected ammo temperature, or leave margin.
- Ammunition left in a hot chamber or in the sun heats faster than the air; record powder temperature, not air temperature.

## 10. Input checklist for `scripts/interior.py`

| Input | Where it comes from |
|---|---|
| Bore and groove diameter | Cartridge drawing (CIP/SAAMI) or slugged barrel |
| Case water capacity | Weigh fired, sized brass full of water to the mouth (grains H2O) |
| Case length, COAL, bullet length | User measurement |
| Bullet weight | Box / weigh |
| Barrel length | Bolt face to muzzle |
| Charge | User |
| Force F or Qex, γ, covolume, density | Producer datasheet (Qex/energy if published), published thermochemistry, or GRT/QuickLOAD powder file the user supplies |
| Grain geometry | Datasheet / measured (ball → `sphere`, single-perforated tube → `tube`, otherwise `custom` χ, λ, μ) |
| Vivacity | GRT/QuickLOAD powder data, or calibrate with `--measured-mv-ms` |
| Pmax | CIP table (bar) or SAAMI MAP (psi → bar: ÷ 14.504) |
| Producer max charge | Current producer load data for the exact combination |

If any powder parameter is missing, do not run the simulation: tell the user which value is missing and where to find it.
