# External Ballistics Reference

## Contents
1. Constants and conversions
2. Drag models and BC
3. Atmosphere
4. Wind
5. Spin drift, aerodynamic jump, Coriolis
6. Stability
7. Inclined shots
8. Truing a solver
9. Common error sources

## 1. Constants and conversions

| Quantity | Value |
|---|---|
| 1 MRAD at 100 m | 10 cm |
| 1 MOA at 100 m | 2.908 cm |
| 1 MOA at 100 yd | 1.047 in |
| 1 MRAD | 3.4377 MOA |
| 1 grain | 0.06479891 g |
| 1 ft/s | 0.3048 m/s |
| 1 inHg | 33.8639 hPa |
| 1 bar | 14.5038 psi |
| g (standard) | 9.80665 m/s² |
| Earth rotation Ω | 7.2921·10⁻⁵ rad/s |
| ICAO standard atmosphere (sea level) | 15 °C, 1013.25 hPa, ρ = 1.225 kg/m³ |
| Army Standard Metro (old G1 BC reference) | 59 °F, 29.53 inHg, 78 % RH |

- Kinetic energy: E = ½·m·v²
- Speed of sound (dry air): c ≈ 331.3·√(1 + T/273.15) m/s; ≈ 340.3 m/s at 15 °C
- Transonic: roughly Mach 1.2 → 0.9. Drag changes quickly; BC and drag-model errors grow; some bullets destabilise. Plan the useful range to stay supersonic, or with margin.

## 2. Drag models and BC

- BC (lb/in²) = bullet mass / (form factor · diameter²), always relative to a standard projectile: **G1** (flat base, blunt) or **G7** (long boat-tail, secant ogive).
- Modern long-range bullets match G7 better: the G7 BC is nearly constant over the velocity range, while a G1 BC changes strongly and is often given as several velocity-banded values.
- G1 and G7 numbers are not comparable (G7 values are roughly half the G1 value for the same bullet; do not convert with a fixed ratio).
- **Custom drag models (CDM)** measured by Doppler radar (Applied Ballistics, Hornady 4DOF data) are more accurate than any standard-table BC, especially transonic.
- BC changes with stability (Sg < 1.5 loses BC), with tip deformation and with lot-to-lot bullet variation.

## 3. Atmosphere

- Drag is proportional to air density. Density depends on station pressure, temperature and, slightly, humidity (humid air is less dense).
- **Station pressure** = absolute pressure at the shooter. **Barometric/QNH** = corrected to sea level. A Kestrel shows station pressure as "Station Press" and barometric as "Baro"; confusing them at altitude causes large elevation errors.
- **Density altitude (DA)** summarises density as an equivalent altitude in the standard atmosphere; many solvers accept DA directly.
- Temperature also changes the speed of sound (Mach number, transonic point) and powder temperature (MV).

## 4. Wind

- Lag-time rule (point-mass, exact for constant crosswind and no lift): drift = W_cross · (TOF − R/V₀).
- Only the crosswind component matters for drift: W_cross = W·sin(angle). Clock system: 3 and 9 o'clock = full value; 1:30, 4:30, 7:30, 10:30 ≈ 70 %; 12 and 6 ≈ 0 (head/tailwind changes elevation slightly).
- Wind varies along the path and every part of it contributes to drift. Estimate an average crosswind for the whole path; the scripts assume one constant wind.
- Wind is usually the largest error source past ~500 m: present windage per 1 m/s (or 1 mph) so the user can scale.

## 5. Spin drift, aerodynamic jump, Coriolis

- **Spin drift** (yaw of repose): right-hand twist drifts right. Litz empirical fit: SD [in] = 1.25·(Sg + 1.2)·TOF^1.83. Many shooters zero out part of it at a medium range; state what the table includes.
- **Aerodynamic jump**: a crosswind causes a small vertical deflection that depends on twist direction (for right twist, wind from the right raises impact, from the left lowers it). Magnitude depends on bullet and stability; full 6-DOF or measured models compute it. `scripts/trajectory.py` does not model it; mention it when crosswind is strong.
- **Coriolis** (Earth rotation): horizontal deflection ≈ Ω·R·TOF·sin(latitude), to the right in the Northern Hemisphere, left in the Southern. **Eötvös** (vertical): shooting east impacts high, west low; proportional to cos(latitude)·sin(azimuth). Usually a few cm at 1000 m; relevant for ELR and precise first-round hits. The trajectory script computes both exactly in the integrator.

## 6. Stability

- Gyroscopic stability factor Sg (Miller formula, `scripts/stability.py`): Sg ≥ 1.5 recommended for full BC; 1.0–1.5 marginal; < 1.0 unstable.
- Sg increases with faster twist, higher velocity, warmer/thinner air; decreases with longer bullets for the same weight (monolithic copper bullets are longer).
- Check stability at the coldest, densest conditions expected (winter, sea level).
- Use the measured length of the user's bullet; plastic tips add length but little mass, so full length gives a conservative (lower) Sg.
- Dynamic stability (transonic) is a separate issue not captured by Sg.

## 7. Inclined shots

- Gravity acts perpendicular to the horizon; for an uphill or downhill shot the drop component perpendicular to the line of sight is smaller. Both up and downhill need less elevation than the same slant range on the flat.
- "Rifleman's rule" (multiply horizontal distance) is an approximation; the script solves it exactly by rotating gravity into the line-of-sight frame. Use slant range and look angle as inputs.

## 8. Truing a solver

1. Verify the basics first: zero at the stated distance, sight height (bore centre to scope centre), and **scope tracking** with a tall-target test (a 2–5 % click error looks like a BC problem).
2. Measure MV with a reliable chronograph at the ammo temperature of the day.
3. **True MV** using observed drop at a medium supersonic range (where the bullet is still well above Mach 1.2, typically 500–800 m for .308 and 6.5 CM), using group centres of several shots.
4. **True the drop scale / BC** in the transonic region only after MV is trued.
5. Never adjust MV and BC on the same data point: you will fit noise and make other ranges worse.
6. Record the conditions (station pressure, temperature, wind) for every truing data point.

## 9. Common error sources (largest first, typical)

1. Wind estimation
2. Wrong pressure type (station vs barometric)
3. Muzzle velocity error (temperature, small chrono sample)
4. Scope tracking / click value error
5. Wrong range (laser rangefinder beam divergence on small targets)
6. BC / drag model error, especially transonic
7. Sight height, zero offset, cant (a canted rifle moves impact sideways and lowers it)
