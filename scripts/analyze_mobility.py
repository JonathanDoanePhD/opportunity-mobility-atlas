"""Which county traits go with upward mobility for children from low-income families?

Outcome: mobility_p25 = average adult income percentile (age ~32-37) of children born
1978-83 whose parents were at the 25th income percentile (Opportunity Insights).
Unit: county (Opportunity Insights' 2010-era county codes; excludes Puerto Rico).

Run after build_county_table.py:  python3 -I scripts/analyze_mobility.py
Outputs in output/mobility/.

All estimates are associations across places, not causal effects.
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "output" / "mobility"
OUT.mkdir(parents=True, exist_ok=True)


def fips(state, county):
    return state.astype(int).map("{:02d}".format) + county.astype(int).map("{:03d}".format)


# ---------------- Data ----------------
oi = pd.read_csv(RAW / "county_outcomes_simple.csv")
oi["fips"] = fips(oi.state, oi.county)
cov = pd.read_csv(RAW / "cty_covariates.csv")
cov["fips"] = fips(cov.state, cov.county)
sc = pd.read_csv(RAW / "social_capital_county.csv", dtype={"county": str})
sc["fips"] = sc.county.str.zfill(5)
tbl = pd.read_csv(ROOT / "output" / "county_table.csv", dtype={"fips": str})

d = (oi[["fips", "state", "cz", "czname", "kfr_pooled_pooled_p25", "kfr_pooled_pooled_p25_se",
         "pooled_pooled_count", "kfr_black_pooled_p25", "kfr_hisp_pooled_p25",
         "kfr_white_pooled_p25", "black_pooled_count", "hisp_pooled_count", "white_pooled_count"]]
     .merge(cov.drop(columns=["state", "county", "cz", "czname"]), on="fips", how="left")
     .merge(sc[["fips", "ec_county", "clustering_county", "support_ratio_county",
                "volunteering_rate_county", "civic_organizations_county"]], on="fips", how="left")
     .merge(tbl[["fips", "county_name", "youth_serving_orgs_per_10k_children", "state"]].rename(
         columns={"state": "st"}), on="fips", how="left"))
# Names for the few 2010-era codes missing from the 2022 table (CT counties, old AK area)
d["county_name"] = d.county_name.fillna("FIPS " + d.fips)
d["st"] = d.st.fillna(d.fips.str[:2].map({"09": "CT", "02": "AK"}))
d = d[d.state != 72].copy()
for c in ["kfr_pooled_pooled_p25", "kfr_pooled_pooled_p25_se", "kfr_black_pooled_p25",
          "kfr_hisp_pooled_p25", "kfr_white_pooled_p25"]:
    d[c] = d[c] * 100
d["mobility_p25"] = d.kfr_pooled_pooled_p25
d["log_med_hhinc1990"] = np.log(d.med_hhinc1990)
d["log_popdensity2000"] = np.log1p(d.popdensity2000)
d["log_youth_orgs"] = np.log1p(d.youth_serving_orgs_per_10k_children)

# Predictors, timed as close to the cohort's childhood (1980s-90s) as the data allows.
PRED = {
    # name: (column, label, group, measured)
    "poverty":        ("poor_share1990", "Poverty rate", "Poverty & family", "1990"),
    "single_parent":  ("singleparent_share1990", "Single-parent households", "Poverty & family", "1990"),
    "income":         ("log_med_hhinc1990", "Median household income (log)", "Poverty & family", "1990"),
    "college":        ("frac_coll_plus2000", "Adults with a college degree", "Education", "2000"),
    "test_scores":    ("gsmn_math_g3_2013", "3rd-grade math scores", "Education", "2013"),
    "employment":     ("emp2000", "Employment rate", "Jobs", "2000"),
    "job_growth":     ("ann_avg_job_growth_2004_2013", "Job growth", "Jobs", "2004-13"),
    "commute":        ("traveltime15_2010", "Share with commute < 15 min", "Place", "2010"),
    "density":        ("log_popdensity2000", "Population density (log)", "Place", "2000"),
    "black_share":    ("share_black2000", "Black population share", "Place", "2000"),
    "econ_connect":   ("ec_county", "Economic connectedness", "Social capital", "2022"),
    "clustering":     ("clustering_county", "Friendship clustering", "Social capital", "2022"),
    "support_ratio":  ("support_ratio_county", "Support ratio", "Social capital", "2022"),
    "volunteering":   ("volunteering_rate_county", "Volunteering rate", "Social capital", "2022"),
    "civic_orgs":     ("civic_organizations_county", "Civic organizations", "Social capital", "2022"),
    "youth_orgs":     ("log_youth_orgs", "Youth-serving nonprofits per child (log)", "Youth nonprofits", "2026"),
}
COLS = [v[0] for v in PRED.values()]
LABEL = {v[0]: v[1] for v in PRED.values()}
GROUP = {v[0]: v[2] for v in PRED.values()}
WHEN = {v[0]: v[3] for v in PRED.values()}


def wz(s, w):
    """Weighted z-score."""
    m = np.average(s, weights=w)
    sd = np.sqrt(np.average((s - m) ** 2, weights=w))
    return (s - m) / sd


def wls(df, y, xs, w, fe=None):
    """Weighted least squares, standard errors clustered by commuting zone."""
    X = df[xs].copy()
    if fe is not None:
        X = pd.concat([X, pd.get_dummies(df[fe], prefix=fe, drop_first=True, dtype=float)], axis=1)
    X = sm.add_constant(X)
    return sm.WLS(df[y], X, weights=df[w]).fit(cov_type="cluster", cov_kwds={"groups": df["cz"]})


def standardized(df, cols, w):
    z = df.copy()
    for c in cols:
        z[c] = wz(z[c], z[w])
    return z


# ---------------- 1. Associations: one at a time, and all together ----------------
rows = []
for c in COLS:
    s = d.dropna(subset=["mobility_p25", c, "pooled_pooled_count", "cz"])
    z = standardized(s, [c], "pooled_pooled_count")
    r = wls(z, "mobility_p25", [c], "pooled_pooled_count")
    rows.append({"predictor": c, "label": LABEL[c], "group": GROUP[c], "measured": WHEN[c],
                 "n_counties": len(s), "bivariate_coef": r.params[c],
                 "bivariate_ci_low": r.conf_int().loc[c, 0], "bivariate_ci_high": r.conf_int().loc[c, 1],
                 "bivariate_r2": r.rsquared})
assoc = pd.DataFrame(rows)

# Multivariable model on a common sample. Youth-org density excluded (2022 geography drops
# CT and it is measured decades later); tested separately below.
MULTI = [c for c in COLS if c != "log_youth_orgs"]
s = d.dropna(subset=["mobility_p25", "pooled_pooled_count", "cz"] + MULTI)
zs = standardized(s, MULTI, "pooled_pooled_count")
m_all = wls(zs, "mobility_p25", MULTI, "pooled_pooled_count")
m_fe = wls(zs, "mobility_p25", MULTI, "pooled_pooled_count", fe="state")
ci, ci_fe = m_all.conf_int(), m_fe.conf_int()
assoc["adjusted_coef"] = assoc.predictor.map(m_all.params)
assoc["adjusted_ci_low"] = assoc.predictor.map(ci[0])
assoc["adjusted_ci_high"] = assoc.predictor.map(ci[1])
assoc["adjusted_state_fe_coef"] = assoc.predictor.map(m_fe.params)
assoc["adjusted_state_fe_ci_low"] = assoc.predictor.map(ci_fe[0])
assoc["adjusted_state_fe_ci_high"] = assoc.predictor.map(ci_fe[1])
assoc = assoc.sort_values("bivariate_coef")
assoc.to_csv(OUT / "associations.csv", index=False, float_format="%.4g")

# Does youth-nonprofit density add anything once the other factors are known?
s_y = d.dropna(subset=["mobility_p25", "pooled_pooled_count", "cz"] + COLS)
z_y = standardized(s_y, COLS, "pooled_pooled_count")
m_y = wls(z_y, "mobility_p25", COLS, "pooled_pooled_count")
youth_adj = (m_y.params["log_youth_orgs"], *m_y.conf_int().loc["log_youth_orgs"])

# ---------------- 2. Out-of-sample prediction by group (leave-one-state-out) ----------------
def cv_r2(df, xs, y="mobility_p25", w="pooled_pooled_count"):
    pred = pd.Series(np.nan, index=df.index)
    for st in df.state.unique():
        tr, te = df[df.state != st], df[df.state == st]
        X = sm.add_constant(tr[xs])
        fit = sm.WLS(tr[y], X, weights=tr[w]).fit()
        pred[te.index] = fit.predict(sm.add_constant(te[xs], has_constant="add"))
    ww = df[w]
    resid = np.average((df[y] - pred) ** 2, weights=ww)
    total = np.average((df[y] - np.average(df[y], weights=ww)) ** 2, weights=ww)
    return 1 - resid / total


groups = sorted(set(GROUP[c] for c in MULTI))
pred_rows = [{"factor_group": "All factors together", "variables": len(MULTI),
              "cv_r2_alone": cv_r2(zs, MULTI), "cv_r2_drop_when_removed": 0.0}]
full = pred_rows[0]["cv_r2_alone"]
for g in groups:
    xs = [c for c in MULTI if GROUP[c] == g]
    rest = [c for c in MULTI if GROUP[c] != g]
    pred_rows.append({"factor_group": g, "variables": len(xs), "cv_r2_alone": cv_r2(zs, xs),
                      "cv_r2_drop_when_removed": full - cv_r2(zs, rest)})
pred_rows.append({"factor_group": "Economic connectedness only", "variables": 1,
                  "cv_r2_alone": cv_r2(zs, ["ec_county"]),
                  "cv_r2_drop_when_removed": full - cv_r2(zs, [c for c in MULTI if c != "ec_county"])})
pred = pd.DataFrame(pred_rows)
pred.to_csv(OUT / "prediction_by_group.csv", index=False, float_format="%.3f")

# ---------------- 3. Same patterns by race/ethnicity? ----------------
KEY = ["poor_share1990", "singleparent_share1990", "frac_coll_plus2000", "ec_county",
       "clustering_county", "volunteering_rate_county", "traveltime15_2010"]
race_rows = []
for grp, y, w in [("Black", "kfr_black_pooled_p25", "black_pooled_count"),
                  ("Hispanic", "kfr_hisp_pooled_p25", "hisp_pooled_count"),
                  ("White", "kfr_white_pooled_p25", "white_pooled_count"),
                  ("All", "mobility_p25", "pooled_pooled_count")]:
    for c in KEY:
        s2 = d.dropna(subset=[y, w, c, "cz"])
        s2 = s2[s2[w] >= 100]  # skip counties with very few children in the group
        z2 = standardized(s2, [c], w)
        r = wls(z2, y, [c], w)
        race_rows.append({"group": grp, "predictor": c, "label": LABEL[c], "n_counties": len(s2),
                          "coef": r.params[c], "ci_low": r.conf_int().loc[c, 0],
                          "ci_high": r.conf_int().loc[c, 1]})
race = pd.DataFrame(race_rows)
race.to_csv(OUT / "associations_by_race.csv", index=False, float_format="%.4g")

# ---------------- 4. Beat-the-odds counties ----------------
# Predicted mobility from childhood disadvantage alone (1990 poverty, single parents, income).
BASE = ["poor_share1990", "singleparent_share1990", "log_med_hhinc1990"]
b = d.dropna(subset=["mobility_p25", "kfr_pooled_pooled_p25_se", "pooled_pooled_count", "cz"] + BASE).copy()
fit = sm.WLS(b.mobility_p25, sm.add_constant(b[BASE]), weights=b.pooled_pooled_count).fit()
b["predicted_mobility"] = fit.predict(sm.add_constant(b[BASE]))
b["mobility_vs_predicted"] = b.mobility_p25 - b.predicted_mobility
# Second version compares each county only with others in the same state (state fixed
# effects), so the list isn't dominated by the Great Plains, a region with high mobility overall.
Xs = pd.concat([b[BASE], pd.get_dummies(b.state, prefix="st", drop_first=True, dtype=float)], axis=1)
fit_s = sm.WLS(b.mobility_p25, sm.add_constant(Xs), weights=b.pooled_pooled_count).fit()
b["predicted_mobility_within_state"] = fit_s.predict(sm.add_constant(Xs))
b["mobility_vs_predicted_within_state"] = b.mobility_p25 - b.predicted_mobility_within_state
# A county "beats the odds" if it is in the top third for 1990 poverty, has >= 1,000 children
# in the sample, and beats its prediction by more than 2 standard errors of its own estimate.
pov_cut = b.poor_share1990.quantile(2 / 3)
eligible = (b.poor_share1990 >= pov_cut) & (b.pooled_pooled_count >= 1000)
b["beats_odds_national"] = eligible & (b.mobility_vs_predicted > 2 * b.kfr_pooled_pooled_p25_se)
b["beats_odds_within_state"] = eligible & (
    b.mobility_vs_predicted_within_state > 2 * b.kfr_pooled_pooled_p25_se)
keep = ["fips", "county_name", "st", "czname", "poor_share1990", "singleparent_share1990",
        "pooled_pooled_count", "mobility_p25", "kfr_pooled_pooled_p25_se", "predicted_mobility",
        "mobility_vs_predicted", "predicted_mobility_within_state",
        "mobility_vs_predicted_within_state", "beats_odds_national", "beats_odds_within_state",
        "ec_county"]
bto = (b[b.beats_odds_national | b.beats_odds_within_state]
       .sort_values("mobility_vs_predicted_within_state", ascending=False)[keep])
bto.to_csv(OUT / "beat_the_odds_counties.csv", index=False, float_format="%.4g")

# How do the Atlas priority counties compare with what their disadvantage predicts?
pri = tbl[tbl.priority_flag & ~tbl.flag_small_child_pop][["fips"]].merge(
    b[["fips", "mobility_vs_predicted", "ec_county"]], on="fips")

# ---------------- Figures ----------------
SURFACE, TEXT, TEXT2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
C1, C2 = "#2a78d6", "#eb6834"
plt.rcParams.update({"font.size": 10.5, "axes.edgecolor": GRID, "axes.labelcolor": TEXT2,
                     "xtick.color": TEXT2, "ytick.color": TEXT2})

# Fig 1: bivariate vs adjusted associations
a = assoc[assoc.predictor != "log_youth_orgs"].sort_values("bivariate_coef")
fig, ax = plt.subplots(figsize=(10, 7.2), dpi=100)
fig.patch.set_facecolor(SURFACE); ax.set_facecolor(SURFACE)
y = np.arange(len(a))
ax.axvline(0, color=TEXT2, lw=0.8)
ax.errorbar(a.bivariate_coef, y + 0.17, xerr=[a.bivariate_coef - a.bivariate_ci_low,
            a.bivariate_ci_high - a.bivariate_coef], fmt="o", ms=7, color=C1, ecolor=C1,
            elinewidth=2, capsize=0, label="On its own")
ax.errorbar(a.adjusted_coef, y - 0.17, xerr=[a.adjusted_coef - a.adjusted_ci_low,
            a.adjusted_ci_high - a.adjusted_coef], fmt="D", ms=6.5, color=C2, ecolor=C2,
            elinewidth=2, capsize=0, label="Adjusted for all other factors")
ax.set_yticks(y, [f"{l}  ({w})" for l, w in zip(a.label, a.measured)], color=TEXT)
ax.set_xlabel("Change in adult income percentile per 1 SD higher (95% CI)")
ax.grid(axis="x", color=GRID, lw=0.6); ax.set_axisbelow(True)
for s_ in ["top", "right", "left"]:
    ax.spines[s_].set_visible(False)
ax.legend(loc="lower right", frameon=False, labelcolor=TEXT)
fig.text(0.02, 0.965, "What goes with upward mobility for children from low-income families",
         fontsize=14.5, weight="bold", color=TEXT)
fig.text(0.02, 0.928, "U.S. counties; children born 1978-83 to parents at the 25th income percentile. "
         "Weighted by children; CIs clustered by commuting zone.", color=TEXT2)
fig.text(0.02, 0.012, "Sources: Opportunity Insights; Social Capital Atlas. Associations across "
         "places, not causal effects. Exploratory - verify before external use.",
         fontsize=8.5, color=TEXT2)
fig.subplots_adjust(left=0.36, right=0.97, top=0.9, bottom=0.1)
fig.savefig(OUT / "associations.png", dpi=150, facecolor=SURFACE)
plt.close(fig)

# Fig 2: economic connectedness vs mobility
s3 = d.dropna(subset=["ec_county", "mobility_p25", "pooled_pooled_count"])
fig, ax = plt.subplots(figsize=(9, 6.4), dpi=100)
fig.patch.set_facecolor(SURFACE); ax.set_facecolor(SURFACE)
sz = np.clip(s3.pooled_pooled_count / 400, 3, 120)
ax.scatter(s3.ec_county, s3.mobility_p25, s=sz, color=C1, alpha=0.35, lw=0)
pri_pts = s3[s3.fips.isin(pri.fips)]
ax.scatter(pri_pts.ec_county, pri_pts.mobility_p25, s=34, color=C2, lw=0.8, edgecolor=SURFACE,
           label="Atlas priority counties (>= 2,000 children)")
f = sm.WLS(s3.mobility_p25, sm.add_constant(s3.ec_county), weights=s3.pooled_pooled_count).fit()
xx = np.linspace(s3.ec_county.min(), s3.ec_county.max(), 50)
ax.plot(xx, f.params.iloc[0] + f.params.iloc[1] * xx, color=TEXT, lw=2)
ax.set_xlabel("Economic connectedness (share of high-income friends among low-income people, x2)")
ax.set_ylabel("Adult income percentile, children from 25th-pct. families")
ax.grid(color=GRID, lw=0.6); ax.set_axisbelow(True)
for s_ in ["top", "right"]:
    ax.spines[s_].set_visible(False)
ax.legend(loc="lower right", frameon=False, labelcolor=TEXT)
fig.text(0.02, 0.96, "Counties with more cross-class friendship have higher upward mobility",
         fontsize=14, weight="bold", color=TEXT)
fig.text(0.02, 0.925, f"Each dot is a county, sized by number of children. Weighted R² = {f.rsquared:.2f}.",
         color=TEXT2)
fig.text(0.02, 0.012, "Connectedness measured in 2022, decades after these children grew up. "
         "Exploratory - verify before external use.", fontsize=8.5, color=TEXT2)
fig.subplots_adjust(left=0.1, right=0.97, top=0.89, bottom=0.12)
fig.savefig(OUT / "economic_connectedness.png", dpi=150, facecolor=SURFACE)
plt.close(fig)

# ---------------- Console summary ----------------
pd.set_option("display.width", 160)
print(f"Counties in multivariable model: {len(zs)} | R² = {m_all.rsquared:.2f} "
      f"(with state fixed effects: {m_fe.rsquared:.2f})")
print(assoc[["label", "bivariate_coef", "bivariate_r2", "adjusted_coef", "adjusted_ci_low",
             "adjusted_ci_high", "adjusted_state_fe_coef"]].round(2).to_string(index=False))
print(f"\nYouth-org density, adjusted for everything else: {youth_adj[0]:.2f} "
      f"[{youth_adj[1]:.2f}, {youth_adj[2]:.2f}] (n={len(s_y)})")
print("\nLeave-one-state-out R²:\n", pred.round(3).to_string(index=False))
print("\nBy race (coef per SD):\n",
      race.pivot(index="label", columns="group", values="coef").round(2).to_string())
print(f"\nBeat-the-odds: national {bto.beats_odds_national.sum()}, within-state "
      f"{bto.beats_odds_within_state.sum()}, either {len(bto)} (poverty cut {pov_cut:.3f})")
print(bto.st.value_counts().head(12).to_dict())
print(bto[bto.beats_odds_within_state].head(15)[["county_name", "st", "pooled_pooled_count",
      "poor_share1990", "mobility_p25", "mobility_vs_predicted_within_state", "ec_county"]]
      .round(2).to_string(index=False))
print(f"\nPriority counties: n={len(pri)}, mean mobility vs predicted = "
      f"{pri.mobility_vs_predicted.mean():.2f}, share below predicted = "
      f"{(pri.mobility_vs_predicted < 0).mean():.0%}")
