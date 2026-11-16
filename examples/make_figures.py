"""Generate the documentation figures from the model code.

Writes docs/img/straight_fin_correlations.png: laminar Nu (H1) and Darcy f·Re
against channel aspect ratio for the straight_fin model, with the Shah & London
(1978) table points and the full_wetted_area constants (Nu = 4.36, f·Re = 64)
as flat reference lines. Deterministic and offline. Requires matplotlib
(the `demo` extra).

Run:
    python examples/make_figures.py [--out DIR]
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from thermal_mcp_server.physics import _f_re_darcy_rectangular, _nu_h1_rectangular  # noqa: E402

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
        ax.plot(alphas, curve, color="#1f5fa8", lw=2.0, label="straight_fin model")
        ax.plot(table_alpha, table, "o", ms=7, mfc="white", mec="#c0392b", mew=1.8, label="Shah & London table")
        ax.axhline(legacy, color="#7f7f7f", ls="--", lw=1.2, label=f"full_wetted_area constant ({legacy:g})")
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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=ROOT / "docs" / "img", help="output directory (default: docs/img)")
    args = parser.parse_args()
    print(f"wrote {straight_fin_correlations(args.out)}")


if __name__ == "__main__":
    main()
