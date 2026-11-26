"""First-look map: high-need counties and where youth-serving nonprofit supply is thin.

python3 -I scripts/map_priority.py  ->  output/priority_map.png
Lower 48 + DC only (Alaska/Hawaii are in the table, not drawn here).
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shapefile
from matplotlib.collections import PolyCollection
from matplotlib.patches import Patch

ROOT = Path(__file__).resolve().parents[1]
d = pd.read_csv(ROOT / "output" / "county_table.csv", dtype={"fips": str}).set_index("fips")

# Albers equal-area conic (USA Contiguous), lon/lat degrees -> metres
def albers(lon, lat, lat1=29.5, lat2=45.5, lat0=37.5, lon0=-96.0):
    p = np.radians
    n = (np.sin(p(lat1)) + np.sin(p(lat2))) / 2
    C = np.cos(p(lat1)) ** 2 + 2 * n * np.sin(p(lat1))
    rho = lambda la: np.sqrt(C - 2 * n * np.sin(p(la))) / n
    th = n * p(np.asarray(lon) - lon0)
    r = rho(np.asarray(lat))
    return r * np.sin(th), rho(lat0) - r * np.cos(th)

SURFACE, NEUTRAL, EDGE = "#fcfcfb", "#e4e3df", "#fcfcfb"
HIGH_NEED, PRIORITY = "#2a78d6", "#eb6834"
TEXT, TEXT2 = "#0b0b0b", "#52514e"

def category(f):
    if f not in d.index:
        return "none"
    r = d.loc[f]
    if r.priority_flag:
        return "priority_small" if r.flag_small_child_pop else "priority"
    if r.need_index >= 75:
        return "high_need"
    return "other"

style = {
    "other": dict(fc=NEUTRAL, hatch=None),
    "none": dict(fc=NEUTRAL, hatch=None),
    "high_need": dict(fc=HIGH_NEED, hatch=None),
    "priority": dict(fc=PRIORITY, hatch=None),
    "priority_small": dict(fc="#f6b89c", hatch="////"),
}

sf = shapefile.Reader(str(ROOT / "data" / "raw" / "shapes" / "cb_2022_us_county_20m.shp"))
groups = {k: [] for k in style}
for rec, shp in zip(sf.records(), sf.shapes()):
    if rec["STATEFP"] in ("02", "15", "72"):
        continue
    cat = category(rec["GEOID"])
    pts = np.array(shp.points)
    for a, b in zip(shp.parts, list(shp.parts[1:]) + [len(pts)]):
        x, y = albers(pts[a:b, 0], pts[a:b, 1])
        groups[cat].append(np.column_stack([x, y]))

fig, ax = plt.subplots(figsize=(13, 8.4), dpi=100)
fig.patch.set_facecolor(SURFACE)
ax.set_facecolor(SURFACE)
for cat in ["other", "none", "high_need", "priority_small", "priority"]:
    s = style[cat]
    pc = PolyCollection(groups[cat], facecolors=s["fc"], edgecolors=EDGE, linewidths=0.25)
    if s["hatch"]:
        pc.set_hatch(s["hatch"]); pc.set_edgecolor("#c9561f"); pc.set_linewidth(0.0)
        plt.rcParams["hatch.linewidth"] = 0.6
    ax.add_collection(pc)
ax.autoscale_view(); ax.set_aspect("equal"); ax.axis("off")

n_pri = int((d.priority_flag & ~d.flag_small_child_pop).sum())
n_pri_s = int((d.priority_flag & d.flag_small_child_pop).sum())
n_high = int(((d.need_index >= 75) & ~d.priority_flag).sum())
ax.legend(handles=[
    Patch(fc=PRIORITY, label=f"High need, fewest youth-serving nonprofits ({n_pri})"),
    Patch(fc="#f6b89c", hatch="////", ec="#c9561f", lw=0,
          label=f"Same, but < 2,000 children: less reliable ({n_pri_s})"),
    Patch(fc=HIGH_NEED, label=f"High need, more youth-serving nonprofits ({n_high})"),
    Patch(fc=NEUTRAL, label="Lower need / no data (CT)"),
], loc="lower left", frameon=False, fontsize=10.5, labelcolor=TEXT, bbox_to_anchor=(0.0, -0.02))

fig.text(0.04, 0.95, "Where youth face the most barriers and youth-serving nonprofits are thinnest",
         fontsize=16, weight="bold", color=TEXT)
fig.text(0.04, 0.915,
         "High need = top quarter of counties on a blend of child poverty (2022), CDC Social Vulnerability "
         "Index (2022) and low upward mobility.\nFewest = bottom quarter of youth-serving nonprofits "
         "(mentoring + youth development, IRS) per 10,000 children.",
         fontsize=10.5, color=TEXT2, va="top")
fig.text(0.04, 0.015,
         "Sources: Census SAIPE 2022; CDC/ATSDR SVI 2022; Opportunity Insights county outcomes; IRS Exempt "
         "Organizations BMF.\nNonprofit counts miss school, tribal, faith-based and government programs. "
         "Exploratory - verify before external use.",
         fontsize=8.5, color=TEXT2)
fig.subplots_adjust(left=0.02, right=0.98, top=0.86, bottom=0.06)
fig.savefig(ROOT / "output" / "priority_map.png", dpi=150, facecolor=SURFACE)
print("wrote output/priority_map.png")
