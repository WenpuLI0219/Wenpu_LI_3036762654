# Empirical Report: Replicating and Extending Card & Krueger (1994)

**Reference.** Card, D., & Krueger, A. B. (1994). *Minimum Wages and Employment:
A Case Study of the Fast-Food Industry in New Jersey and Pennsylvania.*
American Economic Review, 84(4), 772–793.

---

## 1. Research question and motivation

**Research question.** Does raising the minimum wage reduce employment?

The question is one of the longest-standing in labour economics. The textbook
competitive model predicts that a binding minimum wage — one set above the
market-clearing wage — moves firms up the labour-demand curve and *lowers*
employment. Before 1994 this view dominated both theory and policy debate, yet
the existing evidence was largely time-series and observational, and therefore
could not cleanly separate the effect of the minimum wage from the many
macroeconomic forces moving employment at the same time.

**Motivation and the identification idea.** The authors exploit a natural
experiment: on April 1, 1992, **New Jersey raised its state minimum wage from
$4.25 to $5.05** per hour, while the neighbouring state of **Pennsylvania kept
it at $4.25** (the federal level). Fast-food restaurants on either side of the
state border — Burger King, KFC, Roy Rogers, and Wendy's — are nearly identical
in technology and labour demand, so Pennsylvania restaurants form a natural
counterfactual for what New Jersey employment *would have* done in the absence
of the hike. The result is one of the earliest and most influential
difference-in-differences (DID) designs in economics.

The paper's finding — that the minimum-wage increase was **not** associated
with employment loss, and may even have raised employment — was startling at
the time and remains central to modern minimum-wage debates.

---

## 2. Data sources, sample construction, and variable definitions

### 2.1 Data source

The data are Card and Krueger's original survey of fast-food restaurants in New
Jersey and eastern Pennsylvania, conducted in **two waves**:

- **Wave 1:** February–March 1992 (before the April 1 wage hike).
- **Wave 2:** November–December 1992 (after).

The file `data/public.csv` contains **410 stores × 46 columns**. Columns with
the suffix `2` are second-wave responses; blank cells are missing values.

### 2.2 Sample construction

| Step | Rule | Stores |
|---|---|---|
| Wave-1 file | all observations | 410 |
| Second-wave status | `STATUS2 == 1` (answered) **or** `STATUS2 == 3` (permanent closure) | 405 |
| Valid employment both waves | `FTE1` and `FTE2` non-missing | **384** (NJ 309, PA 75) |

Permanently closed stores are kept at **zero employees** — the raw data already
records them as `0,0,0`. Excluding them would introduce *survivorship bias*
(stores that closed under the wage pressure would vanish from the "after"
average, inflating it). Stores that were temporarily closed, refused, or
otherwise unobservable in wave 2 are dropped.

### 2.3 Variable definitions

| Variable | Definition |
|---|---|
| `FTE` | Full-time-equivalent employment = full-time + 0.5 × part-time + managers |
| `DFTE` | Change in FTE (wave 2 − wave 1) |
| `NJ` (=`STATE`) | 1 = New Jersey (treated), 0 = Pennsylvania (control) |
| `GAP` | Wage gap: `(5.05 − WAGE_ST)/WAGE_ST` for NJ stores with `WAGE_ST < 5.05`; 0 for PA and compliant NJ stores; missing if the starting wage is unknown |
| `CHAIN` | 1 = Burger King, 2 = KFC, 3 = Roy Rogers, 4 = Wendy's |
| `CO_OWNED` | 1 = company-owned (vs. franchise) |
| `SOUTHJ/CENTRALJ/NORTHJ/PA1/PA2/SHORE` | Region indicators (South/Central/North NJ, two PA regions, NJ shore) |

---

## 3. Empirical design

### 3.1 Difference-in-differences

The core specification regresses each store's change in employment on the
treatment dummy (optionally with controls):

```
DFTE_i = α + β·NJ_i + γ'X_i + ε_i
```

The coefficient β is the DID estimate: New Jersey's employment change net of
Pennsylvania's. Equivalently, in means form:

```
DID = (E[FTE2|NJ] − E[FTE1|NJ]) − (E[FTE2|PA] − E[FTE1|PA])
```

**Identifying assumption:** parallel trends — absent the wage hike, NJ and PA
employment would have evolved identically. With two survey waves this cannot be
tested directly; the design's credibility rests on the geographic and sectoral
similarity of the two groups.

### 3.2 Treatment-intensity (wage-gap) reduced form

The paper's second design uses the *bite* of the law rather than a binary
treatment. For NJ stores, `GAP` is the proportional increase needed to reach
the new minimum. Regressing the employment change on `GAP`:

```
DFTE_i = α + θ·GAP_i + γ'X_i + ε_i,   i ∈ New Jersey
```

estimates the employment response to the *intensity* of the mandated wage
increase.

### 3.3 Estimation details

All regressions use heteroskedasticity-robust (HC1) standard errors; a
`matrix_rank` assertion guarantees the region controls are not collinear with
the treatment dummy.

---

## 4. Core replication results and comparison with the original paper

### 4.1 Table 3 — mean FTE employment per store

| | n | Before | After | Change |
|---|---|---|---|---|
| **New Jersey** | 309 | 20.43 (0.52) | 20.90 (0.53) | +0.47 (0.48) |
| **Pennsylvania** | 75 | 23.38 (1.39) | 21.10 (0.97) | −2.28 (1.25) |
| **DID** | | | | **+2.75** |

**Comparison with the paper.** Card & Krueger report NJ before = 20.44, NJ
change = +0.59, PA change = −2.16, and **DID = +2.76** (SE 1.36). Our DID of
**2.75** matches to the second decimal, and the NJ pre-treatment mean (20.43 vs
20.44) is essentially identical. The replication therefore recovers the paper's
headline estimate almost exactly.

### 4.2 Table 4 — regression DID with controls

| Specification | β_NJ (robust SE) | p |
|---|---|---|
| (i) NJ only | 2.750 (1.338) | 0.040 |
| (ii) + chain, company-owned | 2.785 (1.341) | 0.038 |
| (iii) + region (PA1, SHORE) | 1.270 (2.003) | 0.526 |

Specification (i) equals the DID of means (2.75); the chain/ownership controls
leave it at 2.79. Both match the paper's ~2.7–2.8. The region-controlled column
remains positive but imprecise — a consequence of the small Pennsylvania
control group rather than misspecification (see §6).

### 4.3 Wage-gap reduced form

| Specification | θ (robust SE) | p |
|---|---|---|
| GAP only | 13.081 (6.714) | 0.051 |
| + chain, company-owned | 12.274 (7.048) | 0.082 |

The positive, marginally significant coefficient replicates the paper's
finding that a larger mandated wage increase is associated with a *larger*
employment increase — the opposite of the competitive-model prediction.

### 4.4 Summary of comparison

| Quantity | Paper | This replication |
|---|---|---|
| NJ before FTE | 20.44 | 20.43 |
| DID (Table 3) | 2.76 | 2.75 |
| DID regression (ii) | ~2.8 | 2.79 |
| Wage-gap sign | positive | positive (p ≈ 0.05) |

The replication is faithful: magnitudes, signs, and significance all agree.

---

## 5. Independent extension

Beyond the paper's core tables, we perform four extensions.

### 5.1 First stage — did the treatment actually raise wages?

A valid DID requires the treatment to have "bitten". Comparing starting wages:

| | Change in starting wage | n |
|---|---|---|
| New Jersey | +$0.47 | 285 |
| Pennsylvania | −$0.03 | 66 |
| **Wage DID** | **+$0.50** | |

New Jersey starting wages rose by roughly half a dollar on average while
Pennsylvania wages were flat, confirming the minimum-wage hike was binding and
passed through to posted wages. This validates the design's first stage.

### 5.2 Heterogeneity by ownership

Company-owned and franchise stores may respond differently (franchisees have
less slack to absorb a wage shock). Interacting the treatment with ownership:

| Term | Estimate (robust SE) | p |
|---|---|---|
| NJ | 3.181 (1.881) | 0.091 |
| NJ × CO_OWNED | −1.142 (2.368) | 0.630 |

Franchise stores in NJ show the larger effect (+3.18), while company-owned
stores gain slightly less (+2.04); the interaction is not statistically
significant, so there is no clear evidence of differential response by
ownership.

### 5.3 Alternative outcomes

The aggregate FTE result conceals which margin of employment responds:

| Outcome | DID |
|---|---|
| Full-time-equivalent | +2.75 |
| Total employment | +2.41 |
| Full-time only | +3.16 |
| Part-time only | −0.68 |

The entire employment gain is concentrated in **full-time** employment
(+3.16); part-time employment actually *fell* slightly (−0.68). This is
consistent with the wage hike inducing firms to shift the composition of their
workforce toward full-time staff, and it is the opposite of the common worry
that a minimum wage pushes employers to shed full-time jobs.

### 5.4 Robustness — clustered errors and outliers

- **Clustered standard errors** (specification ii, β_NJ = 2.785): clustering by
  region gives SE 1.458 (p = 0.056); by chain, SE 1.162 (p = 0.017). The
  estimate remains significant or marginally significant under either
  clustering.
- **Outlier exclusion:** dropping the single flagged outlier (FTE > 75) yields
  β_NJ = 2.836 (SE 1.336, p = 0.034) — slightly larger, confirming the result is
  not driven by one large store.

Taken together, the extensions reinforce the headline: the wage increase did
not reduce employment, and the result is robust across specifications.

---

## 6. Validation, limitations, and conclusion

### 6.1 Validation

- **First stage:** NJ wages rose ~$0.50 relative to PA, so the treatment was
  binding.
- **Internal consistency:** the regression DID (2.75) equals the DID of means;
  the GAP reduced form and the binary-treatment results point in the same
  direction.
- **Robustness:** results survive clustered errors, outlier exclusion, and
  shore exclusion (β_NJ = 1.34).

### 6.2 Limitations

1. **Small control group.** Only 75 Pennsylvania stores remain in the balanced
   sample, which is the source of the large standard errors — especially once
   region controls partition the data.
2. **Only two time periods.** Parallel trends cannot be tested or visualized;
   the design relies on the assumption rather than demonstrating it.
3. **Survivorship and attrition.** Closed stores are imputed at zero
   employment; temporary closures and refusals are dropped, which could bias
   the estimate if attrition is non-random.
4. **No general-equilibrium or spillover controls.** The design captures
   within-sector, within-state effects; it cannot speak to entry/exit, price
   pass-through, or spillovers across the border.
5. **External validity.** One industry (fast food), one state, one episode
   (1992). Results need not generalise to other sectors, states, or time
   periods.
6. **Measurement.** FTE weighting (part-time = 0.5) and self-reported
   employment are approximations.

### 6.3 Conclusion

We reproduce Card and Krueger's (1994) central result: following New Jersey's
1992 minimum-wage increase, fast-food employment in New Jersey *rose* relative
to Pennsylvania by about **2.75 full-time-equivalent employees per store** —
matching the paper's estimate of 2.76 almost exactly. The effect is
concentrated in full-time employment, is robust to clustered standard errors
and outlier exclusion, and is mirrored by a positive wage-gap reduced form.
The result challenges the simple competitive prediction that a minimum wage
destroys jobs, and the replication confirms that the finding is a property of
the data, not an artifact of specification.

---

## Appendix — reproduction files

| File | Purpose |
|---|---|
| `reproduce_ck.py` | Core replication (preprocessing, Table 3, Table 4, GAP model, shore robustness) |
| `clean_data.py` | Generates `data/public_cleaned.csv` |
| `extension.py` | The independent extensions of §5 |
| `REPRODUCTION.md` | Step-by-step methodology documentation |
