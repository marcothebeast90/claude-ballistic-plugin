#!/usr/bin/env python3
"""Miller gyroscopic stability factor (Sg) with velocity and atmosphere corrections.

Sg = 30*m / (t^2 * d^3 * l * (1 + l^2)) * (V/2800)^(1/3) * ((T_F + 460)/519) * (29.92/P_inHg)
  m  bullet weight [grains]
  d  bullet diameter [in]
  l  bullet length [calibers] = length_in / d
  t  twist [calibers per turn] = twist_in / d
  V  muzzle velocity [fps]

Interpretation (Miller / Litz): Sg >= 1.5 full BC; 1.0-1.5 marginal (BC loss); < 1.0 unstable.
The formula is calibrated for jacketed lead-core bullets; for monolithic copper bullets
(longer for the same weight) it remains valid as long as the real measured length is used.
Plastic-tipped bullets: Miller suggests length correction (tip has negligible mass);
this script uses the full length entered, which is conservative (lower Sg).

Usage examples:
  python3 stability.py --weight-gr 140 --diam-in 0.264 --length-mm 35.0 --twist-in 8 --mv-ms 850
  python3 stability.py --weight-gr 175 --diam-in 0.308 --length-in 1.24 --twist-in 10 --mv-fps 2600 \
      --temp-c 5 --pressure-hpa 900
"""
import argparse

MM_PER_IN = 25.4
FPS_PER_MS = 3.280839895
INHG_PER_HPA = 0.0295299830714


def miller_sg(weight_gr, diam_in, length_in, twist_in, mv_fps=2800.0,
              temp_f=59.0, pressure_inhg=29.92):
    l = length_in / diam_in
    t = twist_in / diam_in
    sg = 30.0 * weight_gr / (t ** 2 * diam_in ** 3 * l * (1.0 + l ** 2))
    sg *= (mv_fps / 2800.0) ** (1.0 / 3.0)
    sg *= (temp_f + 460.0) / 519.0
    sg *= 29.92 / pressure_inhg
    return sg


def verdict(sg):
    if sg < 1.0:
        return "UNSTABLE (Sg < 1.0)"
    if sg < 1.5:
        return "MARGINAL (1.0-1.5): stable but expect reduced BC, more sensitive to cold/dense air"
    return "STABLE (Sg >= 1.5): full BC expected"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--weight-gr", type=float, required=True)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--diam-in", type=float)
    g.add_argument("--diam-mm", type=float)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--length-in", type=float)
    g.add_argument("--length-mm", type=float)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--twist-in", type=float, help="inches per turn, e.g. 8 for 1:8")
    g.add_argument("--twist-mm", type=float, help="mm per turn, e.g. 203 for 1:8in")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--mv-fps", type=float)
    g.add_argument("--mv-ms", type=float)
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--temp-f", type=float)
    g.add_argument("--temp-c", type=float)
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--pressure-inhg", type=float, help="STATION (absolute) pressure")
    g.add_argument("--pressure-hpa", type=float, help="STATION (absolute) pressure")
    a = ap.parse_args()

    d = a.diam_in if a.diam_in else a.diam_mm / MM_PER_IN
    L = a.length_in if a.length_in else a.length_mm / MM_PER_IN
    tw = a.twist_in if a.twist_in else a.twist_mm / MM_PER_IN
    v = a.mv_fps if a.mv_fps else (a.mv_ms * FPS_PER_MS if a.mv_ms else 2800.0)
    tf = a.temp_f if a.temp_f is not None else (a.temp_c * 9 / 5 + 32 if a.temp_c is not None else 59.0)
    p = a.pressure_inhg if a.pressure_inhg else (a.pressure_hpa * INHG_PER_HPA if a.pressure_hpa else 29.92)

    sg = miller_sg(a.weight_gr, d, L, tw, v, tf, p)
    print(f"Inputs: {a.weight_gr} gr, d={d:.4f} in, L={L:.3f} in ({L/d:.2f} cal), "
          f"twist 1:{tw:.2f} in ({tw/d:.1f} cal), V={v:.0f} fps, T={tf:.1f} F, P={p:.2f} inHg")
    print(f"Sg = {sg:.2f} -> {verdict(sg)}")
    # minimum twist for Sg = 1.5 at these conditions (Sg scales with 1/t^2)
    t_needed = tw * (sg / 1.5) ** 0.5
    print(f"Slowest twist for Sg 1.5 at these conditions: 1:{t_needed:.1f} in")


if __name__ == "__main__":
    main()
