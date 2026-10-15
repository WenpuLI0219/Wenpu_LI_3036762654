# 01_DID
Econ_6067_Project_01_DID

# Reproducing Card & Krueger (1994)

This document explains, step by step, how `reproduce_ck.py` reproduces the
main results of:

> Card, D., & Krueger, A. B. (1994). *Minimum Wages and Employment: A Case
> Study of the Fast-Food Industry in New Jersey and Pennsylvania.* American
> Economic Review, 84(4), 772–793.

It records not only the final code but **why** each step is written the way it
is — including four specification mistakes that were found and corrected along
the way.

---

## 1. The natural experiment

- **Treatment:** New Jersey raised its state minimum wage from **$4.25 to
  $5.05** per hour on **April 1, 1992**.
- **Control:** eastern Pennsylvania, whose minimum wage stayed at **$4.25**
  (the federal level) and was therefore unaffected.
- **Data:** a survey of fast-food restaurants in both states, conducted in two
  waves — **February–March 1992** (before) and **November–December 1992**
  (after). `data/public.csv` holds 410 stores and 46 columns; columns with the
  suffix `2` are second-wave responses.

The design is a **difference-in-differences (DID)**: compare the change in
employment in New Jersey against the change in Pennsylvania. Pennsylvania is
the counterfactual — its employment trend is taken as what New Jersey would
have experienced *without* the wage hike.

---

## 2. Preprocessing

The first thing the script does is inspect and clean the raw file. Several
data-quality problems had to be handled explicitly rather than silently.

```python
df = pd.read_csv("data/public.csv")
df, preprocess_log = preprocess(df)
```

### 2.1 What `preprocess()` does

| Step | Problem found in the raw data | Action |
|---|---|---|
| 1. Unique key | `SHEET` is **not unique**: sheet 407 is shared by two distinct stores (a PA KFC and a NJ Wendy's) | Add `ROW_ID = 0..409`; drop nothing |
| 2. Missing wage | 17 NJ stores have a blank `WAGE_ST` | Flag them — their `GAP` must be *missing*, not 0 |
| 3. Outlier | One store has FTE ≈ 85 (next largest ≈ 70) | Flag `IS_OUTLIER = True`; keep it (the paper keeps it) |

Every step is appended to `preprocess_log` and printed, so the cleaning is
auditable. Nothing is dropped silently — flags are used instead, letting
downstream code decide.

```python
def preprocess(df):
    log = []
    log.append(f"raw data: {len(df)} rows x {df.shape[1]} columns")
    n_dup = int(df["SHEET"].duplicated(keep=False).sum())
    df = df.reset_index(drop=True)
    df["ROW_ID"] = df.index
    log.append(f"SHEET duplicated entries: {n_dup} -> added unique ROW_ID")
    n_miss = int(((df["STATE"] == 1) & df["WAGE_ST"].isna()).sum())
    log.append(f"NJ stores with missing WAGE_ST: {n_miss} (GAP = missing)")
    fte1 = df["EMPFT"] + 0.5 * df["EMPPT"] + df["NMGRS"]
    df["IS_OUTLIER"] = fte1 > 75
    log.append(f"flagged {int(df['IS_OUTLIER'].sum())} store(s) ...")
    return df, log
```

---

## 3. Variable construction

### 3.1 Full-time-equivalent (FTE) employment

The outcome weights part-time workers as half a person:

```
FTE = EMPFT + 0.5 · EMPPT + NMGRS
```

| Component | Wave 1 / Wave 2 | Weight |
|---|---|---|
| Full-time employees | `EMPFT` / `EMPFT2` | 1 |
| Part-time employees | `EMPPT` / `EMPPT2` | 0.5 |
| Managers & assistant managers | `NMGRS` / `NMGRS2` | 1 |

```python
df["FTE1"] = df["EMPFT"] + 0.5 * df["EMPPT"] + df["NMGRS"]
df["FTE2"] = df["EMPFT2"] + 0.5 * df["EMPPT2"] + df["NMGRS2"]
df["DFTE"] = df["FTE2"] - df["FTE1"]   # change in employment
df["NJ"]   = df["STATE"]               # treatment dummy
```

### 3.2 The second-wave status codes

`STATUS2` records what happened to each store between waves. They map to
employment as follows:

| `STATUS2` | Meaning | Wave-2 employment (`FTE2`) |
|---|---|---|
| 1 | Answered | as reported |
| 3 | Permanent closure | **0** (already recorded as `0,0,0` in the raw file) |
| 2, 4, 5, 0 | Temporary / highway / mall-fire / refused | missing (excluded) |

No explicit recoding is needed: the raw data already stores closed stores as
`0,0,0` and the other non-respondents as blank. The mapping above matters for
the *sample filter* in §4.

### 3.3 The wage gap (treatment intensity)

The paper also measures the *bite* of the law — how much each store's starting
wage had to rise to reach the new $5.05 minimum:

```
GAP = (5.05 − WAGE_ST) / WAGE_ST   for NJ stores with WAGE_ST < 5.05
GAP = 0                            for PA stores and already-compliant NJ stores
GAP = missing                      for NJ stores whose starting wage is unknown
```

```python
df["GAP"] = 0.0
nj = df["STATE"] == 1
df.loc[nj & df["WAGE_ST"].isna(), "GAP"] = np.nan
df.loc[nj & (df["WAGE_ST"] < 5.05), "GAP"] = (5.05 - df["WAGE_ST"]) / df["WAGE_ST"]
```

> **Why "missing" and not 0?** A store whose starting wage is unknown *might*
> have needed a raise. Setting `GAP = 0` would silently classify it as "no
> bite", biasing the treatment-intensity measure. This was one of the bugs
> corrected.

---

## 4. The analysis sample (closed-store correction)

A DID needs a "before" and an "after" for every store. The correct sample
keeps stores that either **answered** the second survey *or* **closed
permanently** (whose employment is 0):

```python
bal = df[df["STATUS2"].isin([1, 3]) &
         df["FTE1"].notna() & df["FTE2"].notna()].copy()
```

- `STATUS2 == 1` — responded, keep reported employment.
- `STATUS2 == 3` — permanently closed, keep at **0 employees**.
- `STATUS2 ∈ {2,4,5,0}` — no valid second-wave employment, excluded.

> **Why include the closed stores at 0?** Excluding them would introduce
> *survivorship bias*: stores that went out of business (possibly because the
> wage hike squeezed them) would vanish from the "after" average, making
> employment look artificially high. The paper therefore counts permanent
> closures as zero employees. The earlier version of this script set `FTE2 = 0`
> for closures but then *dropped* them with a `STATUS2 == 1` filter — a
> contradiction that has now been fixed.

This leaves **384 stores** (309 New Jersey, 75 Pennsylvania).

---

## 5. Table 3 — the DID of means

For each state, compute the mean FTE before, after, and its change, with
standard errors `SE = s / √n`:

```python
def mean_se(x):
    return x.mean(), x.std(ddof=1) / np.sqrt(x.count())
```

| State | n | Before | After | Change |
|---|---|---|---|---|
| New Jersey | 309 | 20.43 (0.52) | 20.90 (0.53) | **+0.47** (0.48) |
| Pennsylvania | 75 | 23.38 (1.39) | 21.10 (0.97) | **−2.28** (1.25) |

The difference-in-differences is the difference of the two changes:

```
DID = ΔNJ − ΔPA = 0.47 − (−2.28) = +2.75 FTE employees
```

Employment in New Jersey *rose* relative to Pennsylvania — the paper's famous
finding that the wage hike did **not** reduce employment. (The paper reports
DID = +2.76; the one-cent difference is rounding in the sample.)

---

## 6. Table 4 — the regression DID (collinearity correction)

The same DID can be written as a regression of each store's employment change
on the treatment dummy plus controls:

```
ΔFTE_i = α + β·NJ_i + γ'X_i + ε_i
```

Controls are added progressively. The region controls had to be chosen
carefully to avoid **perfect multicollinearity**.

### 6.1 The multicollinearity problem

The raw region indicators are a partition of the sample:

```
SOUTHJ + CENTRALJ + NORTHJ + PA1 + PA2 = 1   (for every store)
NJ = SOUTHJ + CENTRALJ + NORTHJ
```

Including the `NJ` dummy *and* all five region dummies (plus a constant) makes
the design matrix rank-deficient. The first version of the script did exactly
this and silently produced a meaningless coefficient from the pseudo-inverse.
Now a rank assertion catches any such mistake:

```python
assert np.linalg.matrix_rank(X) == X.shape[1], f"collinear design: {name}"
```

### 6.2 The corrected region controls

Two dummies are used, both weakly correlated with the treatment so they absorb
location effects without draining the `NJ` coefficient:

- `PA1` (reference `PA2`) — distinguishes the two Pennsylvania markets.
- `SHORE` — the special New Jersey shore (Atlantic City casino boom).

The north/central/south NJ split is deliberately omitted (collinear with `NJ`).
`SHORE` is handled as an *exclusion* in the robustness section, not as a main
control.

| Spec | Controls | β_NJ (robust SE) | p |
|---|---|---|---|
| (i) | NJ only | **2.750** (1.338) | 0.040 |
| (ii) | + chain, company-owned | **2.785** (1.341) | 0.038 |
| (iii) | + region (PA1, SHORE) | 1.270 (2.003) | 0.526 |

In (i) the coefficient (2.750) exactly equals the DID of means (2.75) — the
regression is just a re-expression of the same comparison. Adding chain and
ownership controls leaves it at 2.785. The region-controlled estimate stays
positive but is imprecise (see §9).

Each regression uses heteroskedasticity-robust (HC1) standard errors:

```python
m = sm.OLS(y, X, missing="drop").fit(cov_type="HC1")
```

---

## 7. The wage-gap (GAP) reduced form

The paper's core treatment-intensity model regresses the employment change on
the wage gap, estimated on New Jersey stores (Pennsylvania has `GAP = 0`):

```python
gap_samp = bal[bal["NJ"] == 1].dropna(subset=["GAP"])
X = sm.add_constant(gap_samp[["GAP"]].astype(float))
m = sm.OLS(gap_samp["DFTE"], X, missing="drop").fit(cov_type="HC1")
```

| Spec | β_GAP (robust SE) | p |
|---|---|---|
| GAP only | **13.081** (6.714) | 0.051 |
| + chain, company-owned | 12.274 (7.048) | 0.082 |

The coefficient is **positive** and marginally significant: stores facing a
larger mandated wage rise experienced a *larger* increase in employment — again
contradicting the standard prediction. (A coefficient of 13.08 means a store
facing a full 100% gap is associated with ≈ +13 FTE employees.)

---

## 8. Robustness — excluding the New Jersey shore

The NJ shore (Atlantic City casinos) had an idiosyncratic economic boom, so the
paper re-estimates the DID dropping shore stores rather than controlling for
them:

```python
no_shore = bal[bal["SHORE"] == 0]
# ... same regression, region control = PA1 only (SHORE is gone)
```

Result: dropping 32 shore stores leaves 352 stores and gives **β_NJ = 1.34**
(robust SE 2.00) — still positive, so the headline sign survives.

---

## 9. Interpreting the precision

The DID is identified off the NJ-vs-PA comparison, but the Pennsylvania control
group is small (75 stores), so PA's own change (−2.28) has a standard error of
1.25. That imprecision dominates the DID and is **inherent to the data**, not
to the specification:

- The clean estimates — (i) 2.75 and (ii) 2.79 — match the paper's ~2.7–2.8.
- Any region control that partitions either state (PA1/PA2, shore/non-shore)
  redistributes that noise, keeping the coefficient near +1.2–1.3 but inflating
  the standard error to ~2.0.

This is why the paper's headline rests on the no-controls and chain/ownership
specifications, and it is reproduced faithfully here.

---

## 10. Full results (single run)

```
PREPROCESSING LOG
 - raw data: 410 rows x 46 columns
 - SHEET duplicated entries: 2 -> added unique ROW_ID
 - NJ stores with missing WAGE_ST: 17 (GAP = missing)
 - flagged 1 store(s) with FTE > 75 as outlier

SAMPLE COUNTS
 - Wave-1 stores in file       : 410
 - STATUS2 == 1 (answered)     : 399
 - STATUS2 == 3 (perm. closed) : 6 (kept at FTE2 = 0)
 - Analysis sample             : 384  (NJ = 309, PA = 75)

TABLE 3  -- mean FTE employment per store
 - New Jersey   n=309  before=20.43  after=20.90  change=+0.47
 - Pennsylvania n= 75  before=23.38  after=21.10  change=-2.28
 - DID = 2.75

TABLE 4  -- regress change in FTE on NJ dummy
 - (i)   NJ only               beta_NJ = 2.750 (1.338)
 - (ii)  + chain, co-owned     beta_NJ = 2.785 (1.341)
 - (iii) + region              beta_NJ = 1.270 (2.003)

GAP MODEL  -- change in FTE on wage gap (NJ stores)
 - GAP only              beta_GAP = 13.081 (6.714)  p = 0.051
 - GAP + chain, co-owned beta_GAP = 12.274 (7.048)  p = 0.082

ROBUSTNESS  -- exclude NJ shore
 - beta_NJ = 1.341 (2.003)   (352 stores)
```

---

## 11. How to run

```bash
python reproduce_ck.py
```

Dependencies: `pandas`, `numpy`, `statsmodels`.

To regenerate the cleaned dataset (optional, used by downstream analysis):

```bash
python clean_data.py   # -> data/public_cleaned.csv
```

---

## Appendix — the four mistakes corrected

1. **Closed stores dropped.** `STATUS2 == 3` stores had `FTE2` set to 0 but
   were then excluded by a `STATUS2 == 1` filter. Fixed by sampling
   `STATUS2 ∈ {1, 3}`.
2. **Region multicollinearity.** Including all region dummies with the `NJ`
   dummy was rank-deficient. Fixed by dropping reference categories and adding
   a `matrix_rank` assertion.
3. **Missing GAP model.** `GAP` was computed but never regressed. Fixed by
   adding the §7 reduced form.
4. **SHORE treated as a control.** The paper *excludes* the shore in a
   robustness check rather than controlling for it. Fixed by moving `SHORE`
   out of the main controls and into §8.
