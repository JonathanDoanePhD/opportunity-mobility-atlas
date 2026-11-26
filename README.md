# Opportunity & Mobility Atlas

Two questions, one county-level dataset:

1. **Where** do youth face the most structural barriers while youth-serving nonprofits are
   thin? (county table + priority list)
2. **What** place traits go with children from low-income families out-earning their
   parents? (mobility analysis)

> **Exploratory.** Check every figure against its original source before using it in
> funder reports, grant applications or public material. The scores here are a starting
> list for human review, not a decision. All mobility results are associations across
> places, not causal effects.

**Status:** complete (2026-11-13): county table, priority list, mobility analysis,
interactive explorer. Before going public: review of the priority and beat-the-odds lists by
people who know these places; confirm Opportunity Insights citation terms.

**Explore it:** open `output/atlas_explorer.html` in a browser (self-contained; loads D3 and
fonts from public CDNs). Seven layers, state zoom, county search, details panel, ranked
priority list.

## Key findings (mobility analysis)

Outcome: the average adult income percentile of children born 1978-83 whose parents were at
the 25th income percentile ("upward mobility"). Effects are in percentile points per one
standard deviation (SD) of each county trait; 95% CIs account for clustering by commuting zone.

1. **Cross-class friendship is the strongest single correlate of upward mobility.** Counties
   one SD higher in economic connectedness (low-income people having more high-income
   friends) have mobility about **2.7 points higher** (CI 2.4 to 3.0). That holds up after
   adjusting for 14 other traits (2.4) and when comparing only counties within the same state
   (1.4). By itself it predicts **39%** of the variation in states the model never saw, close
   to the five social-capital measures combined (39%) and more than half of what all 15 traits
   together predict (64%). This matches Chetty et al. (2022), and it is the closest public
   measure to the kind of cross-class adult connection mentoring creates.
2. **Family structure and racial composition follow.** Single-parent share in 1990 (-2.0;
   -1.2 adjusted; -1.9 within state) and Black population share in 2000 (-2.5; -1.3 adjusted;
   -0.4 within state). Published research links the racial-composition pattern to segregation
   and discrimination at the place level, not to individual families (check the citation
   before using this point).
3. **Youth-serving nonprofit density shows no relationship once other traits are known**
   (-0.01, CI -0.21 to 0.18), and a slightly *negative* one on its own (-1.0). This is a weak
   test: the counts are from 2026, decades after these children grew up, and they count
   organizations, not mentoring relationships or their quality. It does suggest that *having
   organizations* isn't the same as *building connections*.
4. **The cross-class friendship link is weaker for Black (1.2, CI 0.8 to 1.5) and Hispanic
   (0.4, CI -0.2 to 1.0) children than for white children (2.1, CI 1.9 to 2.4).** County-wide
   friendship measures may miss the networks these children are actually in, and the
   race-specific estimates are noisier. Worth testing more directly, for example with the
   high-school-level measures in the Social Capital Atlas.
5. **Atlas priority counties do worse than their disadvantage predicts.** Of the 62 priority
   counties with enough data, 85% have lower mobility than their 1990 poverty, single-parent
   share and income predict (average -2.6 points). Their median economic connectedness is
   0.60, against 0.81 for all counties. So the priority list points to places where *both*
   formal youth infrastructure and informal cross-class ties are scarce.
6. **315 high-poverty counties "beat the odds"** (top third for 1990 poverty, at least 1,000
   children, mobility more than 2 standard errors above prediction). They are listed in
   `output/mobility/beat_the_odds_counties.csv`, nationally and within their own state. They
   are many in TX, MS, OK, GA, AL and LA, often near priority counties, which makes them
   possible places to learn from. **Caution:** several top counties are oil-boom areas (the
   Permian Basin in TX, the Bakken in ND) where adult incomes were measured at the boom's
   peak, around 2014-15.

**How to read the "adjusted" column:** many traits move together (poverty, income, single
parents, connectedness), so individual adjusted coefficients can change sign. Poverty, for
example, flips from -1.0 to +1.3. Treat the adjusted model as a robustness check on the
leading traits, not as a ranking of separate effects.

## Outputs

| File | What |
|---|---|
| `output/county_table.csv` | 3,144 counties x 51 columns (see Columns below) |
| `output/priority_counties.csv` | The 124 high-need / low-supply counties, ranked |
| `output/priority_map.png` | First-look map, lower 48 |
| `output/atlas_explorer.html` | Interactive explorer (standalone); `atlas_explorer_fragment.html` is the same page without the html/head wrapper |
| `output/mobility/associations.csv`, `.png` | Each trait on its own, adjusted, and adjusted within state, with CIs |
| `output/mobility/prediction_by_group.csv` | Leave-one-state-out R² by group of traits |
| `output/mobility/associations_by_race.csv` | Key traits vs mobility for Black, Hispanic and white children |
| `output/mobility/beat_the_odds_counties.csv` | High-poverty counties with higher mobility than predicted |
| `output/mobility/economic_connectedness.png` | Scatter plot, priority counties highlighted |

## Rebuild

From the repository root:

```bash
pip install -r requirements.txt
python3 -I scripts/fetch_data.py .   # ~350 MB into data/raw/
python3 -I scripts/build_county_table.py   # -> output/county_table.csv, priority list below
python3 -I scripts/map_priority.py         # -> output/priority_map.png
python3 -I scripts/analyze_mobility.py     # -> output/mobility/ (needs county_table.csv)
python3 -I scripts/build_explorer.py       # -> output/atlas_explorer.html (needs both above)
```

Download links live in `data/sources.csv`; `data/sources.lock.csv` records the date and
checksum of the copies the committed outputs were built from. The IRS file is updated
monthly, so a fresh download will change the nonprofit counts slightly.

## Sources (all direct downloads, no account)

| File in `data/raw/` | Source | Link |
|---|---|---|
| `saipe_est22all.xls` | Census Small Area Income & Poverty Estimates, 2022 | https://www2.census.gov/programs-surveys/saipe/datasets/2022/2022-state-and-county/est22all.xls |
| `SVI_2022_US_county.csv` | CDC/ATSDR Social Vulnerability Index 2022 (ACS 2018-22) | https://svi.cdc.gov/Documents/Data/2022/csv/states_counties/SVI_2022_US_county.csv |
| `county_outcomes_simple.csv` | Opportunity Insights county outcomes (children born 1978-83) | https://www2.census.gov/ces/opportunity/county_outcomes_simple.csv |
| `cty_covariates.csv` | Opportunity Insights county characteristics (used in the mobility analysis) | https://opportunityinsights.org/wp-content/uploads/2018/12/cty_covariates.csv |
| `social_capital_county.csv` | Social Capital Atlas (Chetty et al. 2022), via HDX | https://data.humdata.org/dataset/social-capital-atlas |
| `eo1.csv` to `eo4.csv` | IRS Exempt Organizations Business Master File | https://www.irs.gov/pub/irs-soi/eo1.csv (eo2, eo3, eo4 similarly) |
| `zcta_county_2020.txt` | Census 2020 ZCTA-to-county relationship file | https://www2.census.gov/geo/docs/maps-data/data/rel2020/zcta520/tab20_zcta520_county20_natl.txt |
| `shapes/cb_2022_us_county_20m.*` | Census cartographic county boundaries 2022 (map only) | https://www2.census.gov/geo/tiger/GENZ2022/shp/cb_2022_us_county_20m.zip |

Census, CDC and IRS data are U.S. government works (public domain). The county outcomes file is
a Census Bureau public-use release; the covariates file has no published license (cite and link,
or ask Opportunity Insights, before re-hosting it). Opportunity Insights and
the Social Capital Atlas ask for citation; confirm their current terms before publishing.

## Method

**Need index (0-100, higher = more barriers):** the average of three percentile ranks across
counties: child poverty rate (SAIPE 2022), overall SVI, and *low* upward mobility (the
negative of `mobility_p25_income_rank`). A county needs at least 2 of the 3 to get a score.

**Supply index (0-100, higher = more supply):** percentile rank of youth-serving nonprofits
per 10,000 children. "Youth-serving" means IRS category codes O20-O23 (youth centers & clubs),
O50 (youth development programs) and O30/O31 (adult-child matching / Big Brothers Big Sisters).

*Why not mentoring organizations alone:* only about 1,000 nonprofits nationwide are coded
O30/O31, and 85% of counties have none. Most mentoring runs inside broader youth
organizations. Dedicated mentoring presence is kept as its own column
(`has_dedicated_mentoring_org`).

**Opportunity gap score:** the average of need and (100 - supply).
**Priority flag:** need >= 75 *and* supply <= 25. That gives 124 counties, 64 of which have
at least 2,000 children.

**Placing nonprofits in counties:** each mailing ZIP is treated as a ZIP Code Tabulation Area
(ZCTA) and assigned to the county with the largest land overlap. Independent cities (VA,
Baltimore, St. Louis, Carson City) are corrected using the mailing city name, because the
land-area rule would otherwise send their ZIPs to the surrounding county. About 94% of
youth-serving nonprofits get a county; the rest are mostly PO-box ZIPs.

## Columns

| Column | Meaning |
|---|---|
| `fips`, `state`, `county_name` | 5-digit county code, state postal code, name |
| `child_poverty_pct_2022` (+ `_ci90_low/high`) | % of under-18s in poverty, with 90% interval (SAIPE) |
| `children_in_poverty_2022`, `median_hh_income_2022` | SAIPE counts and income |
| `population_acs2022`, `children_0_17_acs2022`, `area_sqmi` | From SVI (ACS 2018-22); children = per-capita denominator |
| `svi_*_pctile` | SVI national percentile (0-100): overall and four themes |
| `pct_adults_no_hs_diploma`, `pct_single_parent_hh`, `pct_hh_no_internet` | SVI component estimates |
| `mobility_p25_income_rank` (+ `_se`) | Average adult income percentile of children raised here by parents at the 25th income percentile (higher = more upward mobility) |
| `mobility_p25_black/hispanic/white` | Same, by race/ethnicity (missing where samples are small) |
| `incarceration_p25` | % incarcerated in 2010 among children from 25th-percentile families |
| `mobility_sample_n` | Children behind the mobility estimate |
| `economic_connectedness` | Share of high-income friends among low-income people (x2; 1 = class-integrated). `_childhood` = measured via high-school friendships |
| `friendship_clustering`, `support_ratio`, `volunteering_rate`, `civic_orgs_per_1k_fb_users` | Other Social Capital Atlas measures |
| `mentoring_orgs`, `mentoring_orgs_with_revenue`, `mentoring_revenue` | O30/O31 nonprofits; revenue is the last reported on IRS file |
| `youth_dev_orgs`, `youth_serving_orgs` | O20-O23/O50 count; mentoring + youth development |
| `*_per_10k_children`, `mentoring_revenue_per_child` | Per-child versions |
| `has_dedicated_mentoring_org` | At least one O30/O31 nonprofit in the county |
| `need_parts_available`, `need_index`, `supply_index`, `opportunity_gap_score`, `opportunity_gap_rank` | See Method |
| `priority_flag` | need >= 75 and supply <= 25 |
| `flag_small_child_pop` | Fewer than 2,000 children: per-child rates are noisy |
| `flag_geography_changed` | CT planning regions and two AK areas: mobility, social-capital and nonprofit data don't align |

## Mobility analysis method (`scripts/analyze_mobility.py`)

- **Unit:** Opportunity Insights counties (2010-era codes, so Connecticut is included; Puerto
  Rico excluded). Weighted by the number of children behind each county's estimate.
- **Traits:** 15 county traits, measured as close to the cohort's childhood as available.
  1990: poverty, single parents, median income. 2000: college share, employment, density,
  Black share. Later: test scores (2013), job growth (2004-13), short commutes (2010),
  social capital (2022). Youth-nonprofit density (2026) is tested separately, because it is
  only available on 2022 geography.
- **Associations:** each trait z-scored and regressed alone, then all together, then all
  together with state fixed effects. Weighted least squares; standard errors clustered by
  commuting zone.
- **Prediction:** leave-one-state-out cross-validated R² for each group of traits alone, and
  the loss when that group is removed from the full model.
- **By race:** county-wide traits vs. race-specific outcomes, in counties with at least 100
  children in the group.
- **Beat the odds:** a county's mobility minus the prediction from 1990 poverty,
  single-parent share and log income (nationally, and with state fixed effects). Flagged if
  the county is in the top third for 1990 poverty, has at least 1,000 children, and the gap
  is more than 2 standard errors of its own estimate.

**Mobility-specific caveats:** the traits span 1990-2026 while the children grew up in the
1980s-90s, so traits measured later (social capital especially) may partly be *results* of
mobility rather than causes. Places that look alike can differ in ways not measured here.
County averages say nothing about any individual child.

## Caveats

- **Nonprofit counts are a proxy for supply, not the real thing.** They miss school-based,
  tribal, faith-based (churches don't have to register) and government programs. They also
  count organizations, not how many youth they serve. A mailing address isn't a service area,
  and statewide organizations get counted wherever their office is. Counties on tribal
  lands and rural areas served by regional organizations will look emptier than they are.
- **Different time periods:** mobility follows children born 1978-83 (adult outcomes around
  2014-15); poverty and SVI describe 2018-2022. Places change.
- **Connecticut** isn't scored (its 2022 planning regions don't match the older county files).
- **Place-level, not individual:** a county's numbers say nothing about any one child.
- Counties under 2,000 children are flagged; per-capita rates there swing on one organization.

## License, citation and data terms

- **Code:** MIT (see `LICENSE`). **Outputs:** CC BY 4.0, subject to the source terms below.
- **Cite this project as:** JonathanDoanePhD (2026). *Opportunity & Mobility Atlas*. https://github.com/JonathanDoanePhD/opportunity-mobility-atlas
- **Data sources and terms** (from `data/sources.csv`; recorded versions and checksums in `data/sources.lock.csv`):

| Source | Terms |
|---|---|
| Census Small Area Income & Poverty Estimates 2022 | U.S. government work (public domain) |
| CDC/ATSDR Social Vulnerability Index 2022 | U.S. government work (public domain) |
| Opportunity Insights county outcomes (Census Bureau public-use release) | Public-use Census Bureau release; no separate license found (checked 2026-11-14); cite Chetty et al. Opportunity Atlas |
| Opportunity Insights county characteristics | No license published on opportunityinsights.org/data (site notice: all rights reserved; checked 2026-11-14); cite and link rather than re-host or ask OI before redistributing |
| Social Capital Atlas (Chetty et al. 2022) via HDX | Meta data license: use/redistribute incl. license; no endorsement; no re-identification |
| IRS Exempt Organizations Business Master File (region 1) | U.S. government work (public domain) |
| IRS Exempt Organizations Business Master File (region 2) | U.S. government work (public domain) |
| IRS Exempt Organizations Business Master File (region 3) | U.S. government work (public domain) |
| IRS Exempt Organizations Business Master File (region 4) | U.S. government work (public domain) |
| Census 2020 ZCTA-to-county relationship file | U.S. government work (public domain) |
| Census cartographic county boundaries 2022 | U.S. government work (public domain) |

Built with AI assistance (Claude). Exploratory research: every statistic needs checking against its original source
before it appears in funder reports, grant applications or public material.

## Status and limitations

Published 2026-11-26 as exploratory research. The analysis is complete and reproducible, but these checks have **not yet been done**, so treat figures as provisional:

- Statistics in this README and in `output/` have not been independently checked against their original sources.
- People who know the places review the priority and beat-the-odds county lists.
- Confirm Chetty et al. citations.
- Opportunity Insights covariates file has no published license: link to it rather than re-hosting, or ask OI.
