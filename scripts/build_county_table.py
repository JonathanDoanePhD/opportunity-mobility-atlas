"""Build the Opportunity Atlas county table.

One row per county (2022 Census geography, 3,144 counties incl. DC).
Run from anywhere:  python3 -I scripts/build_county_table.py
Inputs are expected in data/raw/ (see README.md for download links).
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "output"
OUT.mkdir(exist_ok=True)

# NTEE codes (IRS category codes) used as a rough proxy for youth mentoring supply
MENTORING_NTEE = ("O30", "O31")              # Adult/child matching programs; Big Brothers Big Sisters
YOUTH_DEV_NTEE = ("O20", "O21", "O22", "O23", "O50")  # Youth centers & clubs; youth development programs


def fips(state, county):
    return state.astype(int).map("{:02d}".format) + county.astype(int).map("{:03d}".format)


def pct_rank(s):
    """Percentile rank 0-100 among counties with data (higher = higher value)."""
    return s.rank(pct=True) * 100


# ---------- 1. Base geography + child poverty (Census SAIPE 2022) ----------
sa = pd.read_excel(RAW / "saipe_est22all.xls", header=3, dtype=str)
sa = sa[sa["County FIPS Code"] != "000"].copy()
base = pd.DataFrame({
    "fips": sa["State FIPS Code"] + sa["County FIPS Code"],
    "state": sa["Postal Code"],
    "county_name": sa["Name"],
    "child_poverty_pct_2022": pd.to_numeric(sa["Poverty Percent, Age 0-17"], errors="coerce"),
    "child_poverty_pct_ci90_low": pd.to_numeric(sa.iloc[:, 14], errors="coerce"),
    "child_poverty_pct_ci90_high": pd.to_numeric(sa.iloc[:, 15], errors="coerce"),
    "children_in_poverty_2022": pd.to_numeric(sa["Poverty Estimate, Age 0-17"], errors="coerce"),
    "median_hh_income_2022": pd.to_numeric(sa["Median Household Income"], errors="coerce"),
})

# ---------- 2. Structural barriers (CDC/ATSDR Social Vulnerability Index 2022) ----------
svi = pd.read_csv(RAW / "SVI_2022_US_county.csv", dtype={"FIPS": str}, encoding="utf-8-sig")
svi = svi.replace(-999, np.nan)
svi = svi.rename(columns={
    "FIPS": "fips",
    "E_TOTPOP": "population_acs2022",
    "E_AGE17": "children_0_17_acs2022",
    "RPL_THEMES": "svi_overall_pctile",
    "RPL_THEME1": "svi_socioeconomic_pctile",
    "RPL_THEME2": "svi_household_pctile",
    "RPL_THEME3": "svi_minority_language_pctile",
    "RPL_THEME4": "svi_housing_transport_pctile",
    "EP_NOHSDP": "pct_adults_no_hs_diploma",
    "EP_SNGPNT": "pct_single_parent_hh",
    "EP_NOINT": "pct_hh_no_internet",
    "AREA_SQMI": "area_sqmi",
})
svi_cols = ["fips", "population_acs2022", "children_0_17_acs2022", "area_sqmi",
            "svi_overall_pctile", "svi_socioeconomic_pctile", "svi_household_pctile",
            "svi_minority_language_pctile", "svi_housing_transport_pctile",
            "pct_adults_no_hs_diploma", "pct_single_parent_hh", "pct_hh_no_internet"]
base = base.merge(svi[svi_cols], on="fips", how="left")
for c in [c for c in svi_cols if c.startswith("svi_")]:
    base[c] = base[c] * 100  # 0-1 -> 0-100

# ---------- 3. Upward mobility (Opportunity Insights, children born 1978-83) ----------
oi = pd.read_csv(RAW / "county_outcomes_simple.csv")
oi["fips"] = fips(oi.state, oi.county)
oi = oi.rename(columns={
    "czname": "commuting_zone",
    "kfr_pooled_pooled_p25": "mobility_p25_income_rank",
    "kfr_pooled_pooled_p25_se": "mobility_p25_income_rank_se",
    "kfr_black_pooled_p25": "mobility_p25_black",
    "kfr_hisp_pooled_p25": "mobility_p25_hispanic",
    "kfr_white_pooled_p25": "mobility_p25_white",
    "jail_pooled_pooled_p25": "incarceration_p25",
    "pooled_pooled_count": "mobility_sample_n",
})
oi_cols = ["fips", "commuting_zone", "mobility_p25_income_rank", "mobility_p25_income_rank_se",
           "mobility_p25_black", "mobility_p25_hispanic", "mobility_p25_white",
           "incarceration_p25", "mobility_sample_n"]
oi = oi[oi_cols].copy()
for c in oi_cols[2:-1]:
    oi[c] = oi[c] * 100  # fraction -> percentile points / percent
base = base.merge(oi, on="fips", how="left")

# ---------- 4. Social capital (Social Capital Atlas, 2022) ----------
sc = pd.read_csv(RAW / "social_capital_county.csv", dtype={"county": str})
sc["fips"] = sc.county.str.zfill(5)
sc = sc.rename(columns={
    "ec_county": "economic_connectedness",
    "child_ec_county": "economic_connectedness_childhood",
    "clustering_county": "friendship_clustering",
    "support_ratio_county": "support_ratio",
    "volunteering_rate_county": "volunteering_rate",
    "civic_organizations_county": "civic_orgs_per_1k_fb_users",
})
sc_cols = ["fips", "economic_connectedness", "economic_connectedness_childhood",
           "friendship_clustering", "support_ratio", "volunteering_rate",
           "civic_orgs_per_1k_fb_users"]
base = base.merge(sc[sc_cols], on="fips", how="left")

# ---------- 5. Mentoring supply proxy (IRS Exempt Organizations Business Master File) ----------
eo = pd.concat(
    [pd.read_csv(RAW / f"eo{i}.csv", dtype=str,
                 usecols=["EIN", "CITY", "STATE", "ZIP", "NTEE_CD", "REVENUE_AMT"]) for i in range(1, 5)],
    ignore_index=True,
).drop_duplicates("EIN")
eo["ntee3"] = eo.NTEE_CD.fillna("").str[:3]
eo["is_mentoring"] = eo.ntee3.isin(MENTORING_NTEE)
eo["is_youth_dev"] = eo.ntee3.isin(YOUTH_DEV_NTEE)
youth = eo[eo.is_mentoring | eo.is_youth_dev].copy()
youth["revenue"] = pd.to_numeric(youth.REVENUE_AMT, errors="coerce").fillna(0)
youth["zcta"] = youth.ZIP.fillna("").str[:5]

# ZIP -> county: treat ZIP as ZCTA and pick the county with the largest land-area overlap
rel = pd.read_csv(RAW / "zcta_county_2020.txt", sep="|", dtype=str, encoding="utf-8-sig")
rel = rel.dropna(subset=["GEOID_ZCTA5_20"])
rel["land"] = pd.to_numeric(rel.AREALAND_PART, errors="coerce")
z2c = (rel.sort_values("land", ascending=False)
          .drop_duplicates("GEOID_ZCTA5_20")[["GEOID_ZCTA5_20", "GEOID_COUNTY_20"]]
          .rename(columns={"GEOID_ZCTA5_20": "zcta", "GEOID_COUNTY_20": "fips"}))
youth = youth.merge(z2c, on="zcta", how="left")

# Independent cities (38 in VA, plus Baltimore, St. Louis, Carson City) are small, so the
# largest-land-area rule sends most of their ZIPs to the surrounding county. If an org's
# mailing city is an independent city in the same state, and its ZIP overlaps that city
# (or is a PO-box ZIP that matched nothing), assign it to the city.
indep = base[base.county_name.str.endswith(" city")][["fips", "state", "county_name"]].copy()
indep["CITY"] = indep.county_name.str[:-5].str.upper()
indep = indep.rename(columns={"state": "STATE", "fips": "city_fips"})
youth = youth.merge(indep[["STATE", "CITY", "city_fips"]], on=["STATE", "CITY"], how="left")
pairs = set(zip(rel.GEOID_ZCTA5_20, rel.GEOID_COUNTY_20))
overlaps = [(z, f) in pairs for z, f in zip(youth.zcta, youth.city_fips)]
use_city = youth.city_fips.notna() & (pd.Series(overlaps, index=youth.index) | youth.fips.isna())
youth.loc[use_city, "fips"] = youth.loc[use_city, "city_fips"]
print(f"Reassigned to independent cities: {use_city.sum()}")

match = {
    "youth_orgs_total": len(youth),
    "youth_orgs_matched_to_2022_county": int(youth.fips.isin(base.fips).sum()),
}

agg = youth.dropna(subset=["fips"]).groupby("fips").agg(
    mentoring_orgs=("is_mentoring", "sum"),
    mentoring_orgs_with_revenue=("revenue", lambda r: int(((r > 0) & youth.loc[r.index, "is_mentoring"]).sum())),
    mentoring_revenue=("revenue", lambda r: float(r[youth.loc[r.index, "is_mentoring"]].sum())),
    youth_dev_orgs=("is_youth_dev", "sum"),
).reset_index()
base = base.merge(agg, on="fips", how="left")

# Connecticut moved from 8 counties to 9 planning regions in 2022; the 2020 ZIP file
# and Opportunity Insights still use the old counties, so CT can't be scored here.
ct = base.fips.str.startswith("09")
for c in ["mentoring_orgs", "mentoring_orgs_with_revenue", "mentoring_revenue", "youth_dev_orgs"]:
    base[c] = base[c].fillna(0)
    base.loc[ct, c] = np.nan

kids = base.children_0_17_acs2022.where(base.children_0_17_acs2022 > 0)
base["mentoring_orgs_per_10k_children"] = base.mentoring_orgs / kids * 1e4
base["youth_dev_orgs_per_10k_children"] = base.youth_dev_orgs / kids * 1e4
base["mentoring_revenue_per_child"] = base.mentoring_revenue / kids

# ---------- 6. Composite scores ----------
# Need: higher = more structural barriers. Average of available percentile ranks (needs >=2 of 3).
need_parts = pd.DataFrame({
    "child_poverty": pct_rank(base.child_poverty_pct_2022),
    "svi": pct_rank(base.svi_overall_pctile),
    "low_mobility": pct_rank(-base.mobility_p25_income_rank),
})
base["need_parts_available"] = need_parts.notna().sum(axis=1)
base["need_index"] = need_parts.mean(axis=1).where(base.need_parts_available >= 2)

# Supply: only ~1,000 nonprofits are coded specifically as mentoring, and 85% of counties have
# none, so a per-county rank of that count is mostly ties. Mentoring usually runs inside broader
# youth organizations, so supply = all youth-serving nonprofits (mentoring + youth development)
# per 10k children. Dedicated mentoring presence is kept as a separate yes/no column.
base["youth_serving_orgs"] = base.mentoring_orgs + base.youth_dev_orgs
base["youth_serving_orgs_per_10k_children"] = base.youth_serving_orgs / kids * 1e4
base["has_dedicated_mentoring_org"] = (base.mentoring_orgs > 0).where(~ct)
base["supply_index"] = pct_rank(base.youth_serving_orgs_per_10k_children)

# Gap: high need AND low supply
base["opportunity_gap_score"] = (base.need_index + (100 - base.supply_index)) / 2
base["priority_flag"] = (base.need_index >= 75) & (base.supply_index <= 25)

# Reliability flags
base["flag_small_child_pop"] = base.children_0_17_acs2022 < 2000
base["flag_geography_changed"] = ct | base.fips.isin(["02063", "02066"])
base["opportunity_gap_rank"] = base.opportunity_gap_score.rank(ascending=False, method="min")

base = base.sort_values("opportunity_gap_rank")
base.to_csv(OUT / "county_table.csv", index=False, float_format="%.4g")

priority_cols = ["opportunity_gap_rank", "fips", "county_name", "state", "children_0_17_acs2022",
                 "child_poverty_pct_2022", "svi_overall_pctile", "mobility_p25_income_rank",
                 "economic_connectedness", "youth_serving_orgs", "youth_serving_orgs_per_10k_children",
                 "has_dedicated_mentoring_org", "need_index", "supply_index", "flag_small_child_pop"]
base[base.priority_flag][priority_cols].to_csv(OUT / "priority_counties.csv", index=False,
                                               float_format="%.3g")

# ---------- 7. Console summary ----------
print(f"Counties: {len(base)}")
print(f"Youth/mentoring orgs in IRS file: {match['youth_orgs_total']:,}; "
      f"matched to a 2022 county: {match['youth_orgs_matched_to_2022_county']:,} "
      f"({match['youth_orgs_matched_to_2022_county'] / match['youth_orgs_total']:.0%})")
print("Coverage (non-missing):")
for c in ["child_poverty_pct_2022", "svi_overall_pctile", "mobility_p25_income_rank",
          "economic_connectedness", "mentoring_orgs_per_10k_children", "need_index", "opportunity_gap_score"]:
    print(f"  {c:38s} {base[c].notna().sum():5d}")
print(f"Counties with zero mentoring orgs: {(base.mentoring_orgs == 0).sum()}")
print(f"Priority-flagged counties (need >= 75th pct, supply <= 25th pct): {base.priority_flag.sum()}")
print(f"  ...of which have >= 2,000 children: {(base.priority_flag & ~base.flag_small_child_pop).sum()}")
