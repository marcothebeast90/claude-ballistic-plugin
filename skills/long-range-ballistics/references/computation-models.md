# Computation Models

The equations and procedures to implement when a question needs a number. Write the code in Python in the sandbox for each task, run it, and show inputs and assumptions with the result. Use SI units internally; convert only for input and output.

## Contents
1. Conversions and constants
2. Atmosphere
3. Point-mass trajectory (3-DOF)
4. Miller stability
5. Lumped-parameter interior ballistics (pressure cross-check)
6. Validation before you trust a result

## 1. Conversions and constants

| Quantity | Value |
|---|---|
| grain | 0.06479891 g |
| inch | 25.4 mm |
| foot | 0.3048 m |
| yard | 0.9144 m |
| mph | 0.44704 m/s |
| inHg | 33.8638866667 hPa |
| bar | 14.5037738 psi |
| BC lb/in² → kg/m² | × 703.0696 |
| grain of water → cm³ | × 0.06479891 |
| g | 9.80665 m/s² |
| Ω (Earth rotation) | 7.2921159·10⁻⁵ rad/s |
| 1 MRAD | 3.4377468 MOA |

## 2. Atmosphere

Inputs: temperature T [°C], **station** pressure p [hPa], relative humidity RH [%].

- Saturation vapour pressure (Tetens): p_sat = 610.78 · 10^(7.5·T / (T + 237.3)) Pa
- Vapour partial pressure: p_v = RH/100 · p_sat; dry air: p_d = p·100 − p_v
- Density: ρ = p_d / (287.058 · T_K) + p_v / (461.495 · T_K), T_K = T + 273.15
- Speed of sound: c = √(1.4 · 287.058 · T_K)
- Default when the user gives nothing: ICAO 15 °C, 1013.25 hPa, 0 % RH (ρ = 1.225 kg/m³). State it.

## 3. Point-mass trajectory (3-DOF)

**Drag tables.** Use the standard G1 and G7 tables (Mach, Cd) from the open-source `py-ballisticcalc` package (`pip install py-ballisticcalc`, add `--break-system-packages` if needed; import `TableG1`, `TableG7`: lists of `{"Mach": m, "CD": cd}`). Interpolate Cd linearly in Mach. Never type drag-table values from memory.

**Frame.** x downrange along the line of sight, y up (perpendicular to the line of sight), z right. The bullet starts at (0, −sight_height, 0).

**Equations of motion.** With wind vector w and velocity v, relative velocity v_r = v − w, speed |v_r|:

- drag deceleration a_d = −ρ · |v_r| · Cd(|v_r|/c) · π / (8 · BC_SI) · v_r, with BC_SI = BC[lb/in²] · 703.0696
- gravity rotated for look angle θ (uphill +): g_vec = (−g·sin θ, −g·cos θ, 0)
- Coriolis (optional, latitude φ, azimuth of fire α clockwise from true north): Ω_vec = Ω·(cos φ · cos α, sin φ, −cos φ · sin α); a_c = −2 · Ω_vec × v
- a = a_d + g_vec + a_c

Integrate with RK4 at a fixed step of about 0.5 ms; interpolate state linearly at each requested range.

**Wind vector** for a wind of speed W coming FROM clock position h (12 = from the target, 3 = from the right): angle ψ = h · 30°, w = (−W·cos ψ, 0, −W·sin ψ).

**Zero.** Find the launch elevation by bisection so that y = 0 at the zero range, with no wind, no Coriolis and look angle 0, in the day's atmosphere (or the zeroing atmosphere if the user gives it).

**Spin drift (optional).** Add Litz's fit to z: SD[in] = 1.25 · (Sg + 1.2) · TOF^1.83, to the right for right-hand twist.

**Outputs per range.** Drop y; elevation hold = −atan(y/x) in MRAD (×3.4377 for MOA); windage hold = −atan(z/x); velocity; Mach = v/c; energy ½·m·v²; time of flight. Positive hold = dial up / right. Flag the first range where Mach < 1.2.

**Not modelled:** aerodynamic jump, custom drag curves (CDM), 6-DOF effects. Say so when they could matter.

## 4. Miller stability

Sg = 30·m / (t²·d³·l·(1 + l²)) · (V/2800)^(1/3) · ((T_F + 460)/519) · (29.92/P_inHg)

- m bullet weight [gr]; d diameter [in]; l length [calibers] = length_in / d; t twist [calibers/turn] = twist_in / d; V muzzle velocity [fps]; T_F temperature [°F]; P_inHg **station** pressure.
- Sg ≥ 1.5 full BC; 1.0–1.5 marginal; < 1.0 unstable.
- Slowest twist for Sg = 1.5 at the same conditions: twist_in · √(Sg / 1.5) (Sg scales with 1/t²).

## 5. Lumped-parameter interior ballistics (pressure cross-check)

A classical Résal/Lagrange model, not GRT's or QuickLOAD's proprietary model. Only run it with real powder parameters (producer datasheet, published thermochemistry, or a GRT/QuickLOAD powder file the user supplies). If a parameter is missing, do not run it: say which value is missing.

**Geometry.**
- Bore area A from the mean of bore and groove diameter.
- Case volume to the mouth V_case = water capacity [gr H₂O] × 0.06479891 cm³.
- Bullet base position from the bolt face: b = COAL − bullet length. Seated length inside the case: s = max(case length − b, 0).
- Initial volume V₀ = V_case − (π/4)·d_groove²·s (boat-tail volume ignored: slightly conservative).
- Bullet travel L = barrel length (bolt face to muzzle) − b.

**Powder.** Force F [J/kg] (or F = (γ − 1)·Q_ex from the heat of explosion), γ, covolume η [m³/kg], solid density ρ_p [kg/m³], burn law exponent α (default 1), vivacity A [1/s at 1 MPa], form function ψ(z) = χ·z·(1 + λz + μz²) for burnt web fraction z ∈ [0, 1], ψ = 1 for z ≥ 1. Ball powder: χ = 3, λ = −1, μ = 1/3. Long single-perforated tube (≈ neutral): χ = 1, λ = 0, μ = 0.

**Equations** (charge mass C, bullet mass m, heat-loss fraction h):
- Free volume: V_f = V₀ − C·(1 − ψ)/ρ_p − η·C·ψ + A·x
- Space-mean pressure (Résal): p = [F·(1 − h)·C·ψ − (γ − 1)·½·φ·m·v²] / V_f, with φ = 1 + C/(3m)
- Base pressure: p_base = p / (1 + C/(3m)); breech pressure: p_breech = p_base · (1 + C/(2m))
- Burn rate: dz/dt = A · (p / 1 MPa)^α
- Bullet starts when p_base ≥ shot-start pressure (common simulator default ≈ 25 MPa); then m · dv/dt = A_bore · p_base, dx/dt = v
- Ignition: start with ψ₀ such that the igniter pressure (≈ 5 MPa) fills V₀ − C/ρ_p.

Integrate (midpoint/RK2) with a time step of the order of 10⁻⁸ s while the bullet is at rest, growing slowly once it moves, until x = L. Record peak breech pressure, muzzle velocity, burnt fraction at the muzzle. Check convergence by halving the step: the peak pressure must not change appreciably.

**Calibration to measured velocity.** If A is unknown and the user has a chrono velocity for the same load, find A by bisection on a log scale so that predicted MV equals measured MV.

**Heat-loss sweep.** Heat loss is uncertain. Run h = 0, 10, 20, 30 % and calibrate A for each: a higher assumed loss needs a faster burn to reach the measured velocity, which raises predicted pressure. Report the **highest** pressure as the conservative estimate, and the spread as the model uncertainty.

**Reporting.** Load density (C/ρ_p ÷ V₀, flag > 100 % as impossible); predicted peak breech pressure in bar and psi; comparison with the cartridge's CIP Pmax (bar) or SAAMI MAP (psi), each with its own standard; whether the charge is above the producer's published maximum and by how much. Always add that this is a model estimate: it can flag probable over-pressure, never prove a load is safe.

## 6. Validation before you trust a result

- **Trajectory:** for one case, compare bullet height, velocity and time of flight with `py-ballisticcalc`'s own `Calculator` (same BC, drag table, MV, sight height, zero, atmosphere). They should agree within a few millimetres and 1 m/s at 1000 m. Note that the library's `drop_angle` uses a different angular convention from the hold defined above, so compare heights.
- **Signs:** wind from 3 o'clock drifts the bullet left (z < 0), so the windage hold is to the right (positive); right-hand twist spin drift goes right; Coriolis deflects right in the Northern Hemisphere; shooting east impacts high (Eötvös).
- **Interior model:** step-size convergence as above; sanity of magnitudes (pressure of the right order for the cartridge's Pmax near a published max charge, velocity close to published data).
- If a check fails, fix the code before giving any number.
