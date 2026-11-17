"""Generate the documentation figures from the model code.

Writes two figures:

- docs/img/straight_fin_correlations.png: laminar Nu (H1) and Darcy f·Re against
  channel aspect ratio (used by both channel models), with the Shah & London
  (1978) table points and the former full_wetted_area circular-tube constants
  (Nu = 4.36, f·Re = 64) as flat reference lines.
- docs/img/default_plate_tj_vs_flow.png: junction temperature and pressure drop
  against flow for the default plate (700 W, water, 25 °C), with the corrected
  model (solid) and the former circular-tube laminar constants (dashed).

The "former" curves are computed here from the literal constants 4.36 and 64;
no legacy code path is kept in physics.py. Deterministic and offline. Requires
matplotlib (the `demo` extra).

Run:
    python examples/make_figures.py [--out DIR]
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from thermal_mcp_server.physics import COOLANTS, _f_re_darcy_rectangular, _nu_h1_rectangular, analyze  # noqa: E402
from thermal_mcp_server.schemas import AnalyzeColdplateInput, Geometry  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]

# Shah & London (1978) tabulated fully developed values: alpha, Darcy f·Re, Nu_H1.
SHAH_LONDON_TABLE = [
    (1.0, 56.908, 3.608),
    (0.5, 62.192, 4.123),
    (0.25, 72.932, 5.331),
    (0.125, 82.340, 6.490),
]


def straight_fin_correlations(out_dir: Path) -> Path:
    alphas = [0.01 + i * (0.99 / 400) for i in range(401)]
    nu = [_nu_h1_rectangular(a) for a in alphas]
    f_re = [_f_re_darcy_rectangular(a) for a in alphas]
    table_alpha = [row[0] for row in SHAH_LONDON_TABLE]

    fig, (ax_nu, ax_f) = plt.subplots(1, 2, figsize=(9.0, 3.8))
    for ax, curve, table, legacy, label in (
        (ax_nu, nu, [row[2] for row in SHAH_LONDON_TABLE], 4.36, "Nu (H1)"),
        (ax_f, f_re, [row[1] for row in SHAH_LONDON_TABLE], 64.0, "f·Re (Darcy)"),
    ):
        ax.plot(alphas, curve, color="#1f5fa8", lw=2.0, label="model (both channel models)")
        ax.plot(table_alpha, table, "o", ms=7, mfc="white", mec="#c0392b", mew=1.8, label="Shah & London table")
        ax.axhline(legacy, color="#7f7f7f", ls="--", lw=1.2, label=f"former full_wetted_area tube constant ({legacy:g})")
        ax.set_xlabel("aspect ratio α = short side / long side")
        ax.set_ylabel(label)
        ax.set_xlim(0.0, 1.04)
        ax.grid(True, color="#e5e5e5", lw=0.6)
        ax.legend(fontsize=8, frameon=False)
    ax_nu.set_title("Fully developed laminar Nusselt number", fontsize=10)
    ax_f.set_title("Fully developed laminar friction", fontsize=10)
    fig.tight_layout()

    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "straight_fin_correlations.png"
    fig.savefig(path, dpi=120, metadata={"Software": None})
    plt.close(fig)
    return path


# Former full_wetted_area laminar constants (circular tube): kept here only to draw
# the "before" curve; physics.py no longer contains them.
LEGACY_NU_LAMINAR = 4.36
LEGACY_F_RE_LAMINAR = 64.0


def _legacy_point(flow_lpm: float, heat_load_w: float = 700.0, inlet_c: float = 25.0) -> tuple[float, float]:
    """Tj (°C) and ΔP (Pa) for the default plate with the former laminar constants,
    using the same equations as analyze() (docs/physics.md Sections B and C)."""
    g = Geometry()
    p = COOLANTS["water"]
    w, h_ch = g.channel_width_m, g.channel_height_m
    dh = 2 * w * h_ch / (w + h_ch)
    flow = flow_lpm / 60000.0
    v = flow / (g.channel_count * w * h_ch)
    re = p.density_kg_m3 * v * dh / p.mu_pa_s
    pr = p.cp_j_kgk * p.mu_pa_s / p.k_w_mk
    if re < 2300:
        nu, f = LEGACY_NU_LAMINAR, LEGACY_F_RE_LAMINAR / re
    elif re > 4000:
        nu, f = 0.023 * re**0.8 * pr**0.4, 0.3164 * re**-0.25
    else:
        b = (re - 2300) / 1700
        nu = LEGACY_NU_LAMINAR * (1 - b) + 0.023 * 4000**0.8 * pr**0.4 * b
        f = LEGACY_F_RE_LAMINAR / 2300 * (1 - b) + 0.3164 * 4000**-0.25 * b
    h = nu * p.k_w_mk / dh
    r_conv = 1.0 / (h * g.channel_count * 2 * (w + h_ch) * g.channel_length_m)
    r_base = g.base_thickness_m / (g.copper_k_w_mk * g.contact_area_m2)
    rise = heat_load_w / (flow * p.density_kg_m3 * p.cp_j_kgk)
    tj = inlet_c + 0.5 * rise + heat_load_w * (0.04 + 0.02 + r_base + r_conv)
    dp = f * (g.channel_length_m / dh) * p.density_kg_m3 * v**2 / 2
    return tj, dp


def _flow_at_re(re: float) -> float:
    g = Geometry()
    p = COOLANTS["water"]
    dh = 2 * g.channel_width_m * g.channel_height_m / (g.channel_width_m + g.channel_height_m)
    return re * p.mu_pa_s / (p.density_kg_m3 * dh) * g.channel_count * g.channel_width_m * g.channel_height_m * 60000.0


def default_plate_tj_vs_flow(out_dir: Path) -> Path:
    flows = [0.5 + i * (11.5 / 460) for i in range(461)]
    new = [analyze(AnalyzeColdplateInput(heat_load_w=700.0, flow_rate_lpm=q, coolant="water", inlet_temp_c=25.0)) for q in flows]
    old = [_legacy_point(q) for q in flows]
    q_lam, q_turb = _flow_at_re(2300.0), _flow_at_re(4000.0)
    default = analyze(AnalyzeColdplateInput())

    fig, (ax_t, ax_p) = plt.subplots(1, 2, figsize=(9.6, 3.9))
    series = (
        (ax_t, [r.junction_temp_c for r in new], [o[0] for o in old], default.junction_temp_c, "junction temperature (°C)"),
        (ax_p, [r.pressure_drop_pa / 1000 for r in new], [o[1] / 1000 for o in old], default.pressure_drop_pa / 1000, "pressure drop (kPa)"),
    )
    for ax, curve, legacy, mark, label in series:
        ax.axvspan(0.0, q_lam, color="#eef3fa", lw=0)
        ax.axvspan(q_lam, q_turb, color="#fbf1e6", lw=0)
        ax.axvspan(q_turb, 12.5, color="#f1f1f1", lw=0)
        ax.plot(flows, legacy, color="#7f7f7f", ls="--", lw=1.4, label="former constants (Nu 4.36, f·Re 64)")
        ax.plot(flows, curve, color="#1f5fa8", lw=2.0, label="corrected (Shah & London, α = 1)")
        ax.plot([8.0], [mark], "o", ms=7, mfc="white", mec="#c0392b", mew=1.8, label="8 LPM default")
        ax.set_xlabel("flow (LPM)")
        ax.set_ylabel(label)
        ax.set_xlim(0.0, 12.5)
        ax.grid(True, color="#e5e5e5", lw=0.6)
    top = ax_t.get_ylim()[1]
    for x, text in ((q_lam / 2, "laminar"), ((q_lam + q_turb) / 2, "transition"), ((q_turb + 12.5) / 2, "turbulent")):
        ax_t.text(x, top, text, ha="center", va="top", fontsize=8, color="#555555")
    ax_t.legend(fontsize=8, frameon=False, loc="upper right", bbox_to_anchor=(1.0, 0.93))
    ax_t.set_title("Default plate, 700 W, water, 25 °C inlet", fontsize=10)
    ax_p.set_title("Cold-plate pressure drop", fontsize=10)
    fig.tight_layout()

    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "default_plate_tj_vs_flow.png"
    fig.savefig(path, dpi=120, metadata={"Software": None})
    plt.close(fig)
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=ROOT / "docs" / "img", help="output directory (default: docs/img)")
    args = parser.parse_args()
    print(f"wrote {straight_fin_correlations(args.out)}")
    print(f"wrote {default_plate_tj_vs_flow(args.out)}")


if __name__ == "__main__":
    main()
