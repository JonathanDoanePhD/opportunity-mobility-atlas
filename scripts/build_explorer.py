"""Build the interactive County Opportunity Atlas explorer (one self-contained HTML file).

python3 -I scripts/build_explorer.py
  -> output/atlas_explorer.html          standalone page (open in any browser)
  -> output/atlas_explorer_fragment.html  same page without <html>/<head> wrapper (for hosts
                                          that add their own, e.g. a Claude artifact)
Needs output/county_table.csv and output/mobility/beat_the_odds_counties.csv (run the other
scripts first) plus data/raw/shapes/.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import shapefile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output"
TEMPLATE = Path(__file__).with_name("explorer_template.html")

t = pd.read_csv(OUT / "county_table.csv", dtype={"fips": str})

# Within-state "beat the odds" gap for every county (not only flagged ones): recompute from
# the mobility script's logic is heavy, so use its saved per-county output where available.
bto = pd.read_csv(OUT / "mobility" / "beat_the_odds_counties.csv", dtype={"fips": str})
flag = set(bto.fips)


def r(x, nd=1):
    return None if pd.isna(x) else round(float(x), nd)


rows = {}
for _, c in t.iterrows():
    cat = 0
    if c.priority_flag:
        cat = 2 if c.flag_small_child_pop else 3
    elif c.need_index >= 75:
        cat = 1
    rows[c.fips] = [
        c.county_name, c.state, None if pd.isna(c.children_0_17_acs2022) else int(c.children_0_17_acs2022),
        r(c.need_index), r(c.supply_index), cat, r(c.child_poverty_pct_2022),
        r(c.mobility_p25_income_rank), r(c.economic_connectedness, 3),
        r(c.youth_serving_orgs_per_10k_children), None if pd.isna(c.has_dedicated_mentoring_org)
        else int(bool(c.has_dedicated_mentoring_org) and c.has_dedicated_mentoring_org != "False"),
        int(c.fips in flag), None if pd.isna(c.opportunity_gap_rank) else int(c.opportunity_gap_rank),
        r(c.svi_overall_pctile),
    ]

# Geometry: Census 1:20m counties, coordinates rounded to ~100 m
sf = shapefile.Reader(str(ROOT / "data" / "raw" / "shapes" / "cb_2022_us_county_20m.shp"))
features = []
for rec, shp in zip(sf.records(), sf.shapes()):
    if rec["STATEFP"] == "72":
        continue
    pts = np.round(np.array(shp.points), 3)
    parts = list(shp.parts) + [len(pts)]
    # Shapefile convention: outer rings clockwise, holes counter-clockwise. d3-geo uses the
    # same convention, but each hole must stay attached to its outer ring: a lone hole ring
    # would be read as "the whole globe except this area".
    polys = []
    for a, b in zip(parts[:-1], parts[1:]):
        ring = pts[a:b]
        x, y = ring[:, 0], ring[:, 1]
        signed = np.sum(x[:-1] * y[1:] - x[1:] * y[:-1]) / 2
        if signed <= 0 or not polys:      # clockwise -> new outer ring
            polys.append([ring.tolist()])
        else:                             # counter-clockwise -> hole of the last outer ring
            polys[-1].append(ring.tolist())
    features.append({"type": "Feature", "id": rec["GEOID"],
                     "geometry": {"type": "MultiPolygon", "coordinates": polys}})
geo = {"type": "FeatureCollection", "features": features}

data_js = json.dumps(rows, separators=(",", ":"))
geo_js = json.dumps(geo, separators=(",", ":"))
page = TEMPLATE.read_text().replace("__DATA__", data_js).replace("__GEO__", geo_js)
(OUT / "atlas_explorer_fragment.html").write_text(page)
standalone = ("<!doctype html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n"
              "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1, viewport-fit=cover\">\n"
              "</head>\n<body>\n" + page + "\n</body>\n</html>\n")
(OUT / "atlas_explorer.html").write_text(standalone)
print(f"counties: {len(rows)}, features: {len(features)}, "
      f"page: {len(standalone) / 1e6:.2f} MB")
