"""Generate the documentation figures from the model code.

Writes three figures:

- docs/img/straight_fin_correlations.png: laminar Nu (H1) and Darcy f·Re against
  channel aspect ratio (used by both channel models), with the Shah & London
  (1978) table points and the former full_wetted_area circular-tube constants
  (Nu = 4.36, f·Re = 64) as flat reference lines.
- docs/img/default_plate_tj_vs_flow.png: junction temperature and pressure drop
  against flow for the default plate (700 W, water, 25 °C), with the corrected
  model (solid) and the former circular-tube laminar constants (dashed).
- docs/img/chip_reference_case.png: junction temperature, pressure drop and the
  H100 resistance stack for the public chips at 35 °C inlet, from
  examples/reference_case.py (A: default plate 8 LPM; B: default plate and
  C: reference straight-fin plate, both at 1.5 LPM/kW).

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
from reference_case import FLOW_PER_KW_LPM, INLET_C, LEGACY_FLOW_LPM, reference_case  # noqa: E402

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


# Okabe-Ito colours; marker shape also distinguishes the configurations.
CONFIG_STYLE = {
    "A": {"color": "#7f7f7f", "marker": "s", "label": f"A  default plate, {LEGACY_FLOW_LPM:g} LPM"},
    "B": {"color": "#D55E00", "marker": "^", "label": f"B  default plate, {FLOW_PER_KW_LPM:g} LPM/kW"},
    "C": {"color": "#0072B2", "marker": "o", "label": f"C  straight-fin plate, {FLOW_PER_KW_LPM:g} LPM/kW"},
}
STACK_STYLE = (
    ("junction_to_case", "R_jc", "#4d4d4d"),
    ("tim", "R_tim", "#9a9a9a"),
    ("base_conduction", "base", "#E69F00"),
    ("convection", "convection", "#56B4E9"),
)


def chip_reference_case(out_dir: Path) -> Path:
    data = reference_case()
    points = data["points"]
    chips: list[str] = []
    for p in points:
        if p["chip"] not in chips:
            chips.append(p["chip"])
    by_key = {(p["chip"], p["config"]): p for p in points}
    rows = list(range(len(chips)))[::-1]  # first chip on top
    row_of = dict(zip(chips, rows))
    labels = [f"{c}\n{by_key[(c, 'A')]['tdp_w']:.0f} W" for c in chips]

    fig = plt.figure(figsize=(10.0, 6.6))
    grid = fig.add_gridspec(2, 2, width_ratios=[1.35, 1.0], height_ratios=[1.75, 1.0], hspace=0.55, wspace=0.08)
    ax_t = fig.add_subplot(grid[0, 0])
    ax_p = fig.add_subplot(grid[0, 1], sharey=ax_t)
    ax_r = fig.add_subplot(grid[1, :])

    for chip in chips:
        y = row_of[chip]
        trio = [by_key[(chip, cfg)] for cfg in ("A", "B", "C")]
        for ax, key in ((ax_t, "tj_c"), (ax_p, "dp_kpa")):
            xs = [p[key] for p in trio]
            ax.plot([min(xs), max(xs)], [y, y], color="#cfcfcf", lw=2.0, zorder=1)
            for cfg, p in zip(("A", "B", "C"), trio):
                style = CONFIG_STYLE[cfg]
                ax.plot([p[key]], [y], style["marker"], ms=7.5, color=style["color"], mec="white", mew=0.8, zorder=3)
        ax_t.plot([trio[0]["tj_limit_c"]], [y], "|", ms=24, mew=1.6, color="black", zorder=2)

    ax_t.set_yticks(rows)
    ax_t.set_yticklabels(labels, fontsize=8.5)
    ax_t.set_ylim(-0.6, len(chips) - 0.4)
    ax_t.set_xlabel("junction temperature (°C)")
    ax_t.set_title(f"Junction temperature, water at {INLET_C:g} °C inlet", fontsize=10, loc="left")
    ax_t.grid(True, axis="x", color="#e5e5e5", lw=0.6)
    ax_t.set_axisbelow(True)

    ax_p.set_xscale("log")
    ax_p.set_xlabel("cold-plate pressure drop (kPa, log scale)")
    ax_p.set_title("Pressure drop", fontsize=10, loc="left")
    ax_p.grid(True, axis="x", which="major", color="#e5e5e5", lw=0.6)
    ax_p.set_axisbelow(True)
    ax_p.tick_params(axis="y", left=False, labelleft=False)
    ax_p.set_xlim(0.4, 40.0)
    ax_p.set_xticks([0.5, 1, 2, 5, 10, 20])
    ax_p.set_xticklabels(["0.5", "1", "2", "5", "10", "20"])

    for ax in (ax_t, ax_p, ax_r):
        ax.tick_params(axis="x", labelsize=9)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)

    handles = [
        plt.Line2D([], [], ls="none", marker=s["marker"], ms=7.5, color=s["color"], mec="white", mew=0.8, label=s["label"]) for s in CONFIG_STYLE.values()
    ]
    handles.append(plt.Line2D([], [], ls="none", marker="|", ms=12, mew=1.6, color="black", label="chip limit"))
    fig.legend(handles=handles, loc="upper center", ncol=4, fontsize=8.5, frameon=False, bbox_to_anchor=(0.5, 0.995), handletextpad=0.3, columnspacing=1.4)

    # Resistance stack for the first chip (H100) in A, B, C.
    chip = chips[0]
    stack_rows = [2, 1, 0]
    for cfg, y in zip(("A", "B", "C"), stack_rows):
        p = by_key[(chip, cfg)]
        left = 0.0
        for key, name, colour in STACK_STYLE:
            width = p["resistances_k_per_w"][key] * 1000.0
            ax_r.barh(y, width, left=left, height=0.62, color=colour, edgecolor="white", lw=0.8)
            if width >= 5.0:
                text_colour = "white" if key in ("junction_to_case",) else "black"
                ax_r.text(left + width / 2, y, f"{width:.1f}", ha="center", va="center", fontsize=8, color=text_colour)
            left += width
        ax_r.text(left + 1.0, y, f"{left:.1f} mK/W", ha="left", va="center", fontsize=8.5)
    plate_name = {"default": "default plate", "reference": "straight-fin plate"}
    ax_r.set_yticks(stack_rows)
    ax_r.set_yticklabels(
        [f"{cfg}  {plate_name[by_key[(chip, cfg)]['plate']]}, {by_key[(chip, cfg)]['flow_lpm']:.2f} LPM" for cfg in ("A", "B", "C")],
        fontsize=8.5,
    )
    ax_r.set_xlim(0.0, 112.0)
    ax_r.set_xlabel("thermal resistance (mK/W)")
    ax_r.set_title(f"{chip} resistance stack (coolant bulk rise not included)", fontsize=10, loc="left")
    ax_r.grid(True, axis="x", color="#e5e5e5", lw=0.6)
    ax_r.set_axisbelow(True)
    ax_r.legend(
        handles=[plt.Rectangle((0, 0), 1, 1, color=colour, label=name) for _, name, colour in STACK_STYLE],
        loc="lower right",
        ncol=4,
        fontsize=8,
        frameon=False,
        bbox_to_anchor=(1.0, 1.0),
        handlelength=1.2,
        columnspacing=1.0,
    )

    fig.subplots_adjust(left=0.2, right=0.97, top=0.9, bottom=0.08)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "chip_reference_case.png"
    fig.savefig(path, dpi=120, metadata={"Software": None})
    plt.close(fig)
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=ROOT / "docs" / "img", help="output directory (default: docs/img)")
    args = parser.parse_args()
    print(f"wrote {straight_fin_correlations(args.out)}")
    print(f"wrote {default_plate_tj_vs_flow(args.out)}")
    print(f"wrote {chip_reference_case(args.out)}")


if __name__ == "__main__":
    main()
