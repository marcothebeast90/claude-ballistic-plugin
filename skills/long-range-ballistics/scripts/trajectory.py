#!/usr/bin/env python3
"""Point-mass (3-DOF) trajectory solver for long-range rifle shooting.

Physics:
  - Standard drag tables G1 / G7 (taken from the py-ballisticcalc package, LGPL-3.0).
    Drag deceleration = rho * v_rel^2 * Cd_std(Mach) * pi / (8 * BC_SI),  BC_SI = BC[lb/in2] * 703.0696
  - Air density from temperature, STATION pressure and humidity (ideal gas, dry air + water vapour).
  - Wind as a constant vector (clock direction the wind comes FROM).
  - Coriolis / Eotvos computed in the integrator (-2 Omega x v) when latitude and azimuth are given.
  - Spin drift added with the Litz empirical formula SD[in] = 1.25*(Sg+1.2)*TOF^1.83 (right twist = right)
    when bullet length and twist are given.
  - Inclined shots via look angle (gravity rotated into the line-of-sight frame).
  - RK4 integration, fixed time step 0.5 ms.

Not modelled: aerodynamic jump from crosswind, yaw of repose beyond the Litz spin drift fit,
custom drag curves (CDM), BC variation with velocity beyond the standard table shape.

Requirements: pip install py-ballisticcalc   (only the drag tables are used)

Example (metric):
  python3 trajectory.py --bc 0.315 --model G7 --mv-ms 850 --weight-gr 140 --diam-in 0.264 \
      --length-mm 35.0 --twist-in 8 --sight-height-mm 50 --zero-m 100 --max-m 1000 --step-m 100 \
      --temp-c 15 --pressure-hpa 1013.25 --humidity 50 --wind-ms 4 --wind-clock 3 \
      --latitude 45.6 --azimuth 0

Example (imperial):
  python3 trajectory.py --bc 0.243 --model G7 --mv-fps 2650 --weight-gr 175 --diam-in 0.308 \
      --sight-height-in 2.0 --zero-yd 100 --max-yd 1000 --step-yd 100 --temp-f 59 --pressure-inhg 29.92 \
      --wind-mph 10 --wind-clock 9 --units imperial
"""
import argparse
import math
import sys

try:
    from py_ballisticcalc import TableG1, TableG7
except ImportError:
    sys.exit("Missing dependency: pip install py-ballisticcalc  (add --break-system-packages if needed)")

G = 9.80665
OMEGA_EARTH = 7.2921159e-5  # rad/s
M_PER_YD = 0.9144
M_PER_FT = 0.3048
MM_PER_IN = 25.4
MS_PER_MPH = 0.44704
HPA_PER_INHG = 33.8638866667
J_PER_FTLBF = 1.3558179483
BC_SI_PER_LBIN2 = 0.45359237 / 0.00064516  # 703.0696 kg/m^2 per lb/in^2
KG_PER_GR = 0.06479891e-3

TABLES = {"G1": TableG1, "G7": TableG7}


class DragTable:
    def __init__(self, table):
        self.mach = [p["Mach"] for p in table]
        self.cd = [p["CD"] for p in table]

    def __call__(self, m):
        ms, cs = self.mach, self.cd
        if m <= ms[0]:
            return cs[0]
        if m >= ms[-1]:
            return cs[-1]
        lo, hi = 0, len(ms) - 1
        while hi - lo > 1:
            mid = (lo + hi) // 2
            if ms[mid] <= m:
                lo = mid
            else:
                hi = mid
        f = (m - ms[lo]) / (ms[hi] - ms[lo])
        return cs[lo] + f * (cs[hi] - cs[lo])


def air(temp_c, station_hpa, rh_pct):
    """Return (density kg/m3, speed of sound m/s)."""
    T = temp_c + 273.15
    p = station_hpa * 100.0
    psat = 610.78 * 10 ** (7.5 * temp_c / (temp_c + 237.3))  # Tetens, Pa
    pv = max(0.0, min(rh_pct, 100.0)) / 100.0 * psat
    pd = p - pv
    rho = pd / (287.058 * T) + pv / (461.495 * T)
    c = math.sqrt(1.4 * 287.058 * T)
    return rho, c


def miller_sg(weight_gr, diam_in, length_in, twist_in, mv_fps, temp_f, p_inhg):
    l = length_in / diam_in
    t = twist_in / diam_in
    sg = 30.0 * weight_gr / (t ** 2 * diam_in ** 3 * l * (1.0 + l ** 2))
    return sg * (mv_fps / 2800.0) ** (1 / 3) * (temp_f + 460.0) / 519.0 * 29.92 / p_inhg


def simulate(elev, cfg, ranges, use_env=True):
    """Integrate trajectory. Frame: x downrange along line of sight, y up (perpendicular to LOS), z right.
    Returns list of rows at requested ranges: (x, y, z, v, t)."""
    rho, c = cfg["rho"], cfg["c"]
    k = math.pi / (8.0 * cfg["bc_si"])
    drag = cfg["drag"]
    la = cfg["look"] if use_env else 0.0
    gx, gy = -G * math.sin(la), -G * math.cos(la)
    w = cfg["wind"] if use_env else (0.0, 0.0, 0.0)
    om = cfg["omega"] if use_env else (0.0, 0.0, 0.0)
    x, y, z = 0.0, -cfg["sh"], 0.0
    v0 = cfg["mv"]
    vx, vy, vz = v0 * math.cos(elev), v0 * math.sin(elev), 0.0
    t, dt = 0.0, 0.0005
    out, idx = [], 0
    targets = sorted(ranges)

    def acc(vx, vy, vz):
        rx, ry, rz = vx - w[0], vy - w[1], vz - w[2]
        vr = math.sqrt(rx * rx + ry * ry + rz * rz)
        a = rho * vr * drag(vr / c) * k
        ax, ay, az = -a * rx + gx, -a * ry + gy, -a * rz
        # Coriolis: -2 Omega x v
        ox, oy, oz = om
        ax += -2.0 * (oy * vz - oz * vy)
        ay += -2.0 * (oz * vx - ox * vz)
        az += -2.0 * (ox * vy - oy * vx)
        return ax, ay, az

    while idx < len(targets):
        px, py, pz, pvx, pvy, pvz, pt = x, y, z, vx, vy, vz, t
        k1 = acc(vx, vy, vz)
        k2 = acc(vx + 0.5 * dt * k1[0], vy + 0.5 * dt * k1[1], vz + 0.5 * dt * k1[2])
        k3 = acc(vx + 0.5 * dt * k2[0], vy + 0.5 * dt * k2[1], vz + 0.5 * dt * k2[2])
        k4 = acc(vx + dt * k3[0], vy + dt * k3[1], vz + dt * k3[2])
        nvx = vx + dt / 6 * (k1[0] + 2 * k2[0] + 2 * k3[0] + k4[0])
        nvy = vy + dt / 6 * (k1[1] + 2 * k2[1] + 2 * k3[1] + k4[1])
        nvz = vz + dt / 6 * (k1[2] + 2 * k2[2] + 2 * k3[2] + k4[2])
        x += dt * (vx + nvx) / 2
        y += dt * (vy + nvy) / 2
        z += dt * (vz + nvz) / 2
        vx, vy, vz = nvx, nvy, nvz
        t += dt
        while idx < len(targets) and x >= targets[idx]:
            f = (targets[idx] - px) / (x - px)
            out.append((targets[idx], py + f * (y - py), pz + f * (z - pz),
                        math.sqrt((pvx + f * (vx - pvx)) ** 2 + (pvy + f * (vy - pvy)) ** 2 + (pvz + f * (vz - pvz)) ** 2),
                        pt + f * (t - pt)))
            idx += 1
        if t > 15 or vx <= 0:
            break
    return out


def find_zero(cfg, zero_m):
    lo, hi = -0.01, 0.05
    for _ in range(60):
        mid = (lo + hi) / 2
        r = simulate(mid, cfg, [zero_m], use_env=False)
        if not r or r[0][1] < 0:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--bc", type=float, required=True, help="ballistic coefficient, lb/in^2")
    ap.add_argument("--model", choices=["G1", "G7"], required=True)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--mv-ms", type=float); g.add_argument("--mv-fps", type=float)
    ap.add_argument("--weight-gr", type=float, help="needed for energy and spin drift")
    ap.add_argument("--diam-in", type=float, help="needed for spin drift")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--length-mm", type=float); g.add_argument("--length-in", type=float)
    ap.add_argument("--twist-in", type=float, help="inches per turn; negative = left twist")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--sight-height-mm", type=float); g.add_argument("--sight-height-in", type=float)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--zero-m", type=float); g.add_argument("--zero-yd", type=float)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--max-m", type=float); g.add_argument("--max-yd", type=float)
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--step-m", type=float); g.add_argument("--step-yd", type=float)
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--temp-c", type=float); g.add_argument("--temp-f", type=float)
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--pressure-hpa", type=float, help="STATION (absolute) pressure")
    g.add_argument("--pressure-inhg", type=float, help="STATION (absolute) pressure")
    ap.add_argument("--humidity", type=float, default=0.0, help="%%RH")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--wind-ms", type=float, default=None); g.add_argument("--wind-mph", type=float)
    ap.add_argument("--wind-clock", type=float, default=3.0, help="direction wind comes FROM, 12 = from target")
    ap.add_argument("--look-angle-deg", type=float, default=0.0, help="uphill +, downhill -")
    ap.add_argument("--latitude", type=float, help="deg, N positive (enables Coriolis)")
    ap.add_argument("--azimuth", type=float, help="deg true, direction of fire (enables Coriolis)")
    ap.add_argument("--units", choices=["metric", "imperial"], default="metric", help="output table units")
    a = ap.parse_args()

    mv = a.mv_ms if a.mv_ms else a.mv_fps * M_PER_FT
    sh = (a.sight_height_mm / 1000 if a.sight_height_mm is not None else
          a.sight_height_in * MM_PER_IN / 1000 if a.sight_height_in is not None else 0.050)
    zero = a.zero_m if a.zero_m else a.zero_yd * M_PER_YD
    imperial_range = a.max_yd is not None
    rmax = a.max_m if a.max_m else a.max_yd * M_PER_YD
    if a.step_m:
        step = a.step_m
    elif a.step_yd:
        step = a.step_yd * M_PER_YD
    else:
        step = (100 * M_PER_YD) if imperial_range else 100.0
    tc = a.temp_c if a.temp_c is not None else ((a.temp_f - 32) * 5 / 9 if a.temp_f is not None else 15.0)
    p = a.pressure_hpa if a.pressure_hpa else (a.pressure_inhg * HPA_PER_INHG if a.pressure_inhg else 1013.25)
    ws = a.wind_ms if a.wind_ms is not None else (a.wind_mph * MS_PER_MPH if a.wind_mph is not None else 0.0)
    th = math.radians(a.wind_clock * 30.0)
    wind = (-ws * math.cos(th), 0.0, -ws * math.sin(th))

    omega = (0.0, 0.0, 0.0)
    if a.latitude is not None and a.azimuth is not None:
        lat, az = math.radians(a.latitude), math.radians(a.azimuth)
        omega = (OMEGA_EARTH * math.cos(lat) * math.cos(az), OMEGA_EARTH * math.sin(lat),
                 -OMEGA_EARTH * math.cos(lat) * math.sin(az))

    rho, c = air(tc, p, a.humidity)
    cfg = dict(rho=rho, c=c, bc_si=a.bc * BC_SI_PER_LBIN2, drag=DragTable(TABLES[a.model]),
               sh=sh, mv=mv, wind=wind, omega=omega, look=math.radians(a.look_angle_deg))
    # zero is computed in standard-free conditions of the day but without wind/coriolis/incline
    elev = find_zero(cfg, zero)

    length_in = a.length_in if a.length_in else (a.length_mm / MM_PER_IN if a.length_mm else None)
    sg = None
    if a.weight_gr and a.diam_in and length_in and a.twist_in:
        sg = miller_sg(a.weight_gr, a.diam_in, length_in, abs(a.twist_in), mv / M_PER_FT,
                       tc * 9 / 5 + 32, p / HPA_PER_INHG)

    n = int(rmax / step + 1e-9)
    ranges = [step * i for i in range(1, n + 1)]
    rows = simulate(elev, cfg, ranges)

    print(f"Air: {tc:.1f} C, {p:.1f} hPa station, {a.humidity:.0f}% RH -> rho {rho:.4f} kg/m3, "
          f"sound {c:.1f} m/s (std 1.2250)")
    print(f"Bullet: BC {a.bc} {a.model}, MV {mv:.1f} m/s ({mv / M_PER_FT:.0f} fps), sight height {sh*1000:.0f} mm, "
          f"zero {zero:.1f} m")
    print(f"Wind {ws:.2f} m/s from {a.wind_clock:g} o'clock; look angle {a.look_angle_deg:g} deg; "
          + (f"Coriolis ON (lat {a.latitude}, az {a.azimuth})" if a.latitude is not None and a.azimuth is not None
             else "Coriolis OFF"))
    print(f"Spin drift: " + (f"ON, Sg {sg:.2f} (Miller)" if sg else "OFF (needs weight, diam, length, twist)"))
    print("Holds: elevation + = dial UP; windage + = dial RIGHT. Holds are angles on the line of sight.\n")

    if a.units == "metric":
        hdr = f"{'Range m':>8} {'Drop cm':>8} {'Elev mil':>8} {'Elev MOA':>8} {'Wind cm':>8} {'Wind mil':>8} " \
              f"{'V m/s':>6} {'Mach':>5} {'E J':>6} {'TOF s':>6}"
    else:
        hdr = f"{'Range yd':>8} {'Drop in':>8} {'Elev mil':>8} {'Elev MOA':>8} {'Wind in':>8} {'Wind mil':>8} " \
              f"{'V fps':>6} {'Mach':>5} {'E ftlb':>6} {'TOF s':>6}"
    print(hdr)
    trans_flag = False
    for (x, y, z, v, t) in rows:
        if sg:
            sd = 1.25 * (sg + 1.2) * t ** 1.83 * MM_PER_IN / 1000
            z += sd if a.twist_in > 0 else -sd
        elev_mil = -math.atan2(y, x) * 1000
        wind_mil = -math.atan2(z, x) * 1000
        elev_moa = elev_mil * 3.4377468
        mach = v / c
        e = 0.5 * a.weight_gr * KG_PER_GR * v * v if a.weight_gr else float("nan")
        mark = ""
        if mach < 1.2 and not trans_flag:
            mark, trans_flag = "  <- below Mach 1.2 (transonic)", True
        if a.units == "metric":
            print(f"{x:8.0f} {y*100:8.1f} {elev_mil:8.2f} {elev_moa:8.2f} {z*100:8.1f} {wind_mil:8.2f} "
                  f"{v:6.0f} {mach:5.2f} {e:6.0f} {t:6.3f}{mark}")
        else:
            print(f"{x/M_PER_YD:8.0f} {y/0.0254:8.1f} {elev_mil:8.2f} {elev_moa:8.2f} {z/0.0254:8.1f} "
                  f"{wind_mil:8.2f} {v/M_PER_FT:6.0f} {mach:5.2f} {e/J_PER_FTLBF:6.0f} {t:6.3f}{mark}")


if __name__ == "__main__":
    main()
