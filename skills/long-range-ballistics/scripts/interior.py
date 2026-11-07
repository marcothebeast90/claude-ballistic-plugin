#!/usr/bin/env python3
"""Lumped-parameter interior ballistics simulator (classical Resal / Lagrange model).

PURPOSE: an independent CROSS-CHECK of chamber pressure, next to published load data and
GRT/QuickLOAD. It is NOT a substitute for either, and it is NOT GRT's model: GRT and QuickLOAD
use their own proprietary/calibrated burn models and powder databases. Results here are only as
good as the powder parameters supplied. Never run it with guessed powder parameters.

MODEL
  Burn law (geometric form function, Vieille-type rate):
      dz/dt = A * (p/1 MPa)^alpha              z = burnt web fraction (0..1)
      psi   = chi*z*(1 + lam*z + mu*z^2)        psi = burnt mass fraction
  Energy (Resal), with heat loss as a fraction of the propellant force:
      p_mean * V_free = F*(1-h)*C*psi - (gamma-1) * 0.5*phi*m*v^2
      V_free = V0 - C*(1-psi)/rho_p - eta*C*psi + A_bore*x
      phi    = 1 + C/(3m)                        (Lagrange gas-mass correction)
  Pressure gradient (Lagrange): p_base = p_mean/(1 + C/(3m)), p_breech = p_base*(1 + C/(2m))
  Motion: bullet starts when p_base >= shot-start pressure, then m*dv/dt = A_bore*p_base.
  Reported pressure = peak BREECH pressure (closest to what CIP/SAAMI chamber gauges measure).

POWDER PARAMETERS (must come from a real source: lab data, published thermochemistry, a
GRT/QuickLOAD powder file the user owns, or the producer's datasheet):
  --force-jkg    propellant force F [J/kg]  (or --qex-jkg heat of explosion; F = (gamma-1)*Qex)
  --gamma        ratio of specific heats of the gases
  --covolume     eta [cm3/g]
  --density      solid propellant density [g/cm3]
  --grain        sphere | tube | custom (with --chi --lam --mu)
  --vivacity     A [1/s at 1 MPa], or omit and give --measured-mv to CALIBRATE A from a chrono
                 velocity (the same idea as GRT/QuickLOAD "calibrate to measured velocity").
  --alpha        burn-rate pressure exponent (default 1.0)

UNCERTAINTY: heat loss is not well known for a given rifle. In calibration mode the script runs
heat-loss fractions 0..30 %: a higher assumed loss requires a faster burn to reach the measured
velocity, which gives a HIGHER predicted pressure. The conservative (highest) value is reported.

Example (calibration from measured velocity):
  python3 interior.py --cal 6.5 --bore-in 0.256 --groove-in 0.264 --capacity-gr-h2o 52.5 \
     --case-len-mm 48.8 --coal-mm 72.3 --bullet-len-mm 35.0 --bullet-gr 140 --barrel-mm 610 \
     --charge-gr 42.0 --force-jkg 1000000 --gamma 1.24 --covolume 1.0 --density 1.6 --grain tube \
     --measured-mv-ms 830 --pmax-bar 4350 --pmax-std CIP --book-max-gr 43.0
"""
import argparse
import math
import sys

GR_KG = 0.06479891e-3
GRH2O_CM3 = 0.06479891          # 1 grain of water ~ 0.0648 cm3
BAR_PSI = 14.5037738

PRESETS = {
    "sphere": (3.0, -1.0, 1.0 / 3.0),   # ideal ball powder: strongly degressive
    "tube": (1.0, 0.0, 0.0),            # long single-perforated tube: ~neutral burning
}


def run(prm, A, h, want_trace=False):
    C, m, Ab = prm["C"], prm["m"], prm["Ab"]
    F = prm["F"] * (1.0 - h)
    g, eta, rho, V0 = prm["gamma"], prm["eta"], prm["rho"], prm["V0"]
    chi, lam, mu, alpha = prm["chi"], prm["lam"], prm["mu"], prm["alpha"]
    phi = 1.0 + C / (3.0 * m)
    kb = 1.0 / (1.0 + C / (3.0 * m))
    kbr = 1.0 + C / (2.0 * m)
    psi_of = lambda z: 1.0 if z >= 1.0 else chi * z * (1.0 + lam * z + mu * z * z)
    # initial state: igniter pressure fills the free volume
    p_ign = prm["p_ign"]
    psi0 = p_ign * (V0 - C / rho) / (F * C)
    # solve z0 from psi0 (small) by bisection
    lo, hi = 0.0, 1.0
    for _ in range(60):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if psi_of(mid) < psi0 else (lo, mid)
    z, x, v, t = lo, 0.0, 0.0, 0.0
    dt = 2e-8
    pk, pk_t, moving = 0.0, 0.0, False

    def pressure(z, x, v):
        psi = psi_of(z)
        vf = V0 - C * (1 - psi) / rho - eta * C * psi + Ab * x
        return max((F * C * psi - (g - 1) * 0.5 * phi * m * v * v) / vf, 0.0), psi

    while x < prm["travel"]:
        p, psi = pressure(z, x, v)
        pb = p * kb
        if not moving and pb >= prm["p_start"]:
            moving = True
        # RK2 midpoint
        dz1 = A * (p / 1e6) ** alpha if z < 1 else 0.0
        dv1 = Ab * pb / m if moving else 0.0
        zm, vm, xm = z + 0.5 * dt * dz1, v + 0.5 * dt * dv1, x + 0.5 * dt * v
        p2, _ = pressure(zm, xm, vm)
        dz2 = A * (p2 / 1e6) ** alpha if zm < 1 else 0.0
        dv2 = Ab * p2 * kb / m if moving else 0.0
        z = min(z + dt * dz2, 1.0)
        x += dt * vm
        v += dt * dv2
        t += dt
        br = p * kbr
        if br > pk:
            pk, pk_t = br, t
        if t > 0.02:
            return None
        if moving and dt < 2e-7:
            dt *= 1.0005  # bullet in motion: let step grow a little
    p_muz, psi_m = pressure(z, x, v)
    return dict(v=v, pmax=pk, t_pmax=pk_t, t_muzzle=t, psi_muzzle=psi_m, p_muzzle=p_muz * kb)


def calibrate(prm, v_target, h):
    lo, hi = 1e-2, 1e4   # vivacity search range, log bisection
    for _ in range(70):
        mid = math.sqrt(lo * hi)
        r = run(prm, mid, h)
        if r is None or r["v"] < v_target:
            lo = mid
        else:
            hi = mid
    A = math.sqrt(lo * hi)
    return A, run(prm, A, h)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cal", default="", help="label only")
    ap.add_argument("--bore-in", type=float, required=True, help="bore (land) diameter")
    ap.add_argument("--groove-in", type=float, required=True, help="groove diameter")
    ap.add_argument("--capacity-gr-h2o", type=float, required=True,
                    help="case water capacity to the mouth, fired+sized brass, grains H2O")
    ap.add_argument("--case-len-mm", type=float, required=True)
    ap.add_argument("--coal-mm", type=float, required=True)
    ap.add_argument("--bullet-len-mm", type=float, required=True)
    ap.add_argument("--bullet-gr", type=float, required=True)
    ap.add_argument("--barrel-mm", type=float, required=True, help="bolt face to muzzle")
    ap.add_argument("--charge-gr", type=float, required=True)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--force-jkg", type=float)
    g.add_argument("--qex-jkg", type=float)
    ap.add_argument("--gamma", type=float, required=True)
    ap.add_argument("--covolume", type=float, required=True, help="cm3/g")
    ap.add_argument("--density", type=float, required=True, help="g/cm3, solid propellant")
    ap.add_argument("--grain", choices=["sphere", "tube", "custom"], required=True)
    ap.add_argument("--chi", type=float); ap.add_argument("--lam", type=float); ap.add_argument("--mu", type=float)
    ap.add_argument("--alpha", type=float, default=1.0)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--vivacity", type=float, help="A [1/s at 1 MPa]")
    g.add_argument("--measured-mv-ms", type=float, help="calibrate vivacity to this chrono velocity")
    g.add_argument("--measured-mv-fps", type=float)
    ap.add_argument("--heat-loss", type=float, default=None,
                    help="fraction 0..1; default: sweep 0-30%% in calibration mode, 0.15 otherwise")
    ap.add_argument("--shot-start-mpa", type=float, default=25.0,
                    help="engraving / shot-start pressure (common simulator default ~25 MPa)")
    ap.add_argument("--ignition-mpa", type=float, default=5.0, help="primer/igniter pressure")
    ap.add_argument("--pmax-bar", type=float, help="max pressure limit (CIP Pmax in bar or SAAMI MAP converted)")
    ap.add_argument("--pmax-std", default="", help="CIP or SAAMI, label only")
    ap.add_argument("--book-max-gr", type=float, help="producer's published max charge for this combination")
    a = ap.parse_args()

    if a.grain == "custom":
        if None in (a.chi, a.lam, a.mu):
            sys.exit("custom grain needs --chi --lam --mu")
        chi, lam, mu = a.chi, a.lam, a.mu
    else:
        chi, lam, mu = PRESETS[a.grain]
    F = a.force_jkg if a.force_jkg else (a.gamma - 1.0) * a.qex_jkg

    d_eff = (a.bore_in + a.groove_in) / 2 * 0.0254   # simple mean bore area approximation
    Ab = math.pi / 4 * d_eff ** 2
    cap = a.capacity_gr_h2o * GRH2O_CM3 * 1e-6
    base = a.coal_mm - a.bullet_len_mm              # bullet base position from bolt face
    intr = max(a.case_len_mm - base, 0.0) / 1000.0  # seated depth inside the case
    d_g = a.groove_in * 0.0254
    V0 = cap - math.pi / 4 * d_g ** 2 * intr        # boat-tail volume ignored (slightly conservative)
    travel = (a.barrel_mm - base) / 1000.0
    C, m = a.charge_gr * GR_KG, a.bullet_gr * GR_KG
    rho, eta = a.density * 1000.0, a.covolume * 1e-3
    load_density = C / (V0 * rho)

    prm = dict(C=C, m=m, Ab=Ab, F=F, gamma=a.gamma, eta=eta, rho=rho, V0=V0, chi=chi, lam=lam, mu=mu,
               alpha=a.alpha, travel=travel, p_start=a.shot_start_mpa * 1e6, p_ign=a.ignition_mpa * 1e6)

    print(f"{a.cal} | charge {a.charge_gr} gr | bullet {a.bullet_gr} gr | COAL {a.coal_mm} mm | barrel {a.barrel_mm} mm")
    print(f"Case volume under bullet {V0*1e6:.2f} cm3 ({V0*1e6/GRH2O_CM3:.1f} gr H2O), bullet travel {travel*1000:.0f} mm")
    print(f"Load density (solid volume / free case volume) {load_density*100:.0f}%"
          + ("  <- COMPRESSED beyond solid volume: impossible, check inputs" if load_density > 1 else ""))
    print(f"Powder: F {F/1e3:.0f} kJ/kg, gamma {a.gamma}, eta {a.covolume} cm3/g, rho {a.density} g/cm3, "
          f"grain {a.grain} (chi {chi:.3f}, lam {lam:.3f}, mu {mu:.3f}), alpha {a.alpha}")
    print(f"Assumptions: shot start {a.shot_start_mpa} MPa, ignition {a.ignition_mpa} MPa, mean bore diameter, "
          f"boat-tail volume ignored\n")

    mv = a.measured_mv_ms if a.measured_mv_ms else (a.measured_mv_fps * 0.3048 if a.measured_mv_fps else None)
    results = []
    if mv:
        hs = [a.heat_loss] if a.heat_loss is not None else [0.0, 0.10, 0.20, 0.30]
        print(f"Calibrating vivacity to measured MV {mv:.0f} m/s")
        print(f"{'Heat loss':>9} {'Vivacity A':>11} {'MV m/s':>7} {'Pmax bar':>9} {'Pmax psi':>9} {'Burnt@muzzle':>12}")
        for h in hs:
            A, r = calibrate(prm, mv, h)
            if r is None:
                print(f"{h*100:8.0f}%  calibration failed (target velocity not reachable with these parameters)")
                continue
            results.append(r["pmax"])
            print(f"{h*100:8.0f}% {A:11.3f} {r['v']:7.0f} {r['pmax']/1e5:9.0f} {r['pmax']/1e5*BAR_PSI:9.0f} "
                  f"{r['psi_muzzle']*100:11.0f}%")
    else:
        h = a.heat_loss if a.heat_loss is not None else 0.15
        r = run(prm, a.vivacity, h)
        if r is None:
            sys.exit("Simulation did not converge: check parameters")
        results.append(r["pmax"])
        print(f"Heat loss {h*100:.0f}%, vivacity {a.vivacity}")
        print(f"MV {r['v']:.0f} m/s ({r['v']/0.3048:.0f} fps), Pmax {r['pmax']/1e5:.0f} bar "
              f"({r['pmax']/1e5*BAR_PSI:.0f} psi), muzzle pressure {r['p_muzzle']/1e5:.0f} bar, "
              f"burnt at muzzle {r['psi_muzzle']*100:.0f}%")

    if results:
        worst = max(results) / 1e5
        print(f"\nConservative predicted Pmax: {worst:.0f} bar ({worst*BAR_PSI:.0f} psi)")
        if a.pmax_bar:
            ratio = worst / a.pmax_bar
            state = "ABOVE the limit" if ratio > 1.0 else ("within 5% of the limit" if ratio > 0.95 else "below the limit")
            print(f"Limit {a.pmax_bar:.0f} bar {a.pmax_std}: predicted {ratio*100:.0f}% of limit -> {state}")
    if a.book_max_gr:
        diff = a.charge_gr - a.book_max_gr
        if diff > 0:
            print(f"WARNING: charge is {diff:.2f} gr ({diff/a.book_max_gr*100:.1f}%) OVER the producer's published max "
                  f"({a.book_max_gr} gr) for this combination.")
        else:
            print(f"Charge is {-diff:.2f} gr below the producer's published max ({a.book_max_gr} gr).")
    print("\nThis is a model estimate. Real pressure depends on lot, temperature, brass, primer and barrel; "
          "verify with velocity against published data and stop at the first pressure sign.")


if __name__ == "__main__":
    main()
