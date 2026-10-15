"""
Reproduce Card & Krueger (1994), "Minimum Wages and Employment: A Case Study
of the Fast-Food Industry in New Jersey and Pennsylvania", American Economic
Review 84(4), 772-793.

Data: data/public.csv  (410 stores, two survey waves: Feb-Mar 1992 and Nov-Dec 1992)
Treatment: New Jersey raised its minimum wage from $4.25 to $5.05 on 1 Apr 1992.
Control: eastern Pennsylvania (minimum wage unchanged at $4.25).
"""

import pandas as pd
import numpy as np
import statsmodels.api as sm


# ---------------------------------------------------------------------------
# 0. Preprocessing
# ---------------------------------------------------------------------------
def preprocess(df):
    """Clean the raw data; log every change. Nothing is silently dropped."""
    log = []
    log.append(f"raw data: {len(df)} rows x {df.shape[1]} columns")

    # (1) SHEET is not unique (sheet 407 shared by two stores) -> unique ROW_ID
    n_dup = int(df["SHEET"].duplicated(keep=False).sum())
    df = df.reset_index(drop=True)
    df["ROW_ID"] = df.index
    log.append(f"SHEET duplicated entries: {n_dup} -> added unique ROW_ID")

    # (2) NJ stores with missing starting wage -> GAP will be set to missing
    #     (unknown bite), NOT 0 (see GAP construction below)
    n_miss = int(((df["STATE"] == 1) & df["WAGE_ST"].isna()).sum())
    log.append(f"NJ stores with missing WAGE_ST: {n_miss} (GAP = missing)")

    # (3) Flag the extreme store (FTE ~ 85) without dropping it
    fte1 = df["EMPFT"] + 0.5 * df["EMPPT"] + df["NMGRS"]
    df["IS_OUTLIER"] = fte1 > 75
    log.append(f"flagged {int(df['IS_OUTLIER'].sum())} store(s) with FTE > 75 as outlier")

    return df, log


df = pd.read_csv("data/public.csv")
df, preprocess_log = preprocess(df)

print("=" * 72)
print("PREPROCESSING LOG")
print("=" * 72)
for line in preprocess_log:
    print(" -", line)

# ---------------------------------------------------------------------------
# 1. Variables
# ---------------------------------------------------------------------------
df["FTE1"] = df["EMPFT"] + 0.5 * df["EMPPT"] + df["NMGRS"]
df["FTE2"] = df["EMPFT2"] + 0.5 * df["EMPPT2"] + df["NMGRS2"]
# Note on STATUS2:
#   =1 answered           -> FTE2 as reported
#   =3 permanent closure  -> FTE2 is already 0,0,0 in the raw data (kept, = 0)
#   =2,4,5,0 (temporary/refused/etc.) -> FTE2 is already missing (excluded)
df["DFTE"] = df["FTE2"] - df["FTE1"]
df["NJ"] = df["STATE"]

# GAP = proportional increase needed to reach the $5.05 minimum.
#   PA -> 0 | NJ WAGE_ST < 5.05 -> (5.05 - WAGE_ST)/WAGE_ST
#   NJ WAGE_ST >= 5.05 -> 0 | NJ missing WAGE_ST -> missing (unknown)
df["GAP"] = 0.0
nj = df["STATE"] == 1
df.loc[nj & df["WAGE_ST"].isna(), "GAP"] = np.nan
df.loc[nj & (df["WAGE_ST"] < 5.05), "GAP"] = (5.05 - df["WAGE_ST"]) / df["WAGE_ST"]

# ---------------------------------------------------------------------------
# 2. Analysis sample: answered (1) OR permanently closed (3, FTE2 = 0), with
#    valid employment in both waves. Closed stores are KEPT at 0 employees
#    (excluded only if no second-wave employment at all).
# ---------------------------------------------------------------------------
bal = df[df["STATUS2"].isin([1, 3]) &
         df["FTE1"].notna() & df["FTE2"].notna()].copy()

print()
print("=" * 72)
print("SAMPLE COUNTS")
print("=" * 72)
print(f"Wave-1 stores in file      : {len(df)}")
print(f"STATUS2 == 1 (answered)    : {int((df['STATUS2'] == 1).sum())}")
print(f"STATUS2 == 3 (perm. closed): {int((df['STATUS2'] == 3).sum())} "
      f"(kept at FTE2 = 0)")
print(f"Analysis sample            : {len(bal)}  "
      f"(NJ = {int((bal['NJ'] == 1).sum())}, "
      f"PA = {int((bal['NJ'] == 0).sum())})")

# ---------------------------------------------------------------------------
# 3. Table 3: DID of means
# ---------------------------------------------------------------------------
def mean_se(x):
    return x.mean(), x.std(ddof=1) / np.sqrt(x.count())

print()
print("=" * 72)
print("TABLE 3 -- mean FTE employment per store")
print("=" * 72)
rows = []
for state, label in [(1, "New Jersey"), (0, "Pennsylvania")]:
    sub = bal[bal["NJ"] == state]
    m1, s1 = mean_se(sub["FTE1"])
    m2, s2 = mean_se(sub["FTE2"])
    mc, sc = mean_se(sub["DFTE"])
    rows.append((label, len(sub), m1, s1, m2, s2, mc, sc))
    print(f"{label:<12} n={len(sub):>3}  before={m1:6.2f} ({s1:.2f})  "
          f"after={m2:6.2f} ({s2:.2f})  change={mc:6.2f} ({sc:.2f})")

nj_chg = rows[0][6]; pa_chg = rows[1][6]
did = nj_chg - pa_chg
print(f"\nDID = change_NJ - change_PA = {nj_chg:.2f} - ({pa_chg:.2f}) = {did:.2f}")

# ---------------------------------------------------------------------------
# 4. Table 4: regression DID, controls added progressively.
#    Region controls are chosen to be FULL RANK with the NJ dummy + constant:
#      NJ = SOUTHJ + CENTRALJ + NORTHJ,  PA = PA1 + PA2.
#    So we include CENTRALJ, NORTHJ (reference SOUTHJ) and PA1 (reference PA2).
#    SHORE is NOT a control -- the paper drops it in robustness checks.
# ---------------------------------------------------------------------------
print()
print("=" * 72)
print("TABLE 4 -- regress change in FTE on NJ dummy (+ controls)")
print("=" * 72)

chain_dummies = pd.get_dummies(bal["CHAIN"], prefix="chain", drop_first=True).astype(float)
region_ctrl = bal[["CENTRALJ", "NORTHJ", "PA1"]].astype(float)

specs = {
    "(i) NJ only":              sm.add_constant(bal[["NJ"]].astype(float)),
    "(ii) + chain, co-owned":   sm.add_constant(pd.concat([bal[["NJ", "CO_OWNED"]].astype(float),
                                                           chain_dummies], axis=1)),
    "(iii) + region":           sm.add_constant(pd.concat([bal[["NJ", "CO_OWNED"]].astype(float),
                                                           chain_dummies, region_ctrl], axis=1)),
}

for name, X in specs.items():
    y = bal["DFTE"]
    # assert full rank so collinearity cannot silently corrupt the estimates
    assert np.linalg.matrix_rank(X) == X.shape[1], f"collinear design: {name}"
    m = sm.OLS(y, X, missing="drop").fit(cov_type="HC1")
    b = m.params["NJ"]; se = m.bse["NJ"]
    print(f"{name:<24}  beta_NJ = {b:6.3f}  (robust SE {se:.3f})  "
          f"t = {b/se:5.2f}  p = {m.pvalues['NJ']:.3f}")

# ---------------------------------------------------------------------------
# 5. Wage-gap (GAP) reduced form -- the paper's core treatment-intensity model.
#    Regress the employment change on GAP for New Jersey stores (PA has GAP=0).
# ---------------------------------------------------------------------------
print()
print("=" * 72)
print("GAP MODEL -- regress change in FTE on wage gap (NJ stores)")
print("=" * 72)

gap_samp = bal[bal["NJ"] == 1].dropna(subset=["GAP"])
gap_chain = pd.get_dummies(gap_samp["CHAIN"], prefix="chain", drop_first=True).astype(float)

gap_specs = {
    "GAP only":                sm.add_constant(gap_samp[["GAP"]].astype(float)),
    "GAP + chain, co-owned":   sm.add_constant(pd.concat([gap_samp[["GAP", "CO_OWNED"]].astype(float),
                                                          gap_chain], axis=1)),
}
print(f"(NJ stores with valid GAP: {len(gap_samp)}; mean GAP = "
      f"{gap_samp['GAP'].mean():.3f})")
for name, X in gap_specs.items():
    assert np.linalg.matrix_rank(X) == X.shape[1], f"collinear design: {name}"
    m = sm.OLS(gap_samp["DFTE"], X, missing="drop").fit(cov_type="HC1")
    b = m.params["GAP"]; se = m.bse["GAP"]
    print(f"{name:<24}  beta_GAP = {b:6.3f}  (robust SE {se:.3f})  "
          f"t = {b/se:5.2f}  p = {m.pvalues['GAP']:.3f}")

# ---------------------------------------------------------------------------
# 6. Robustness: drop the NJ shore (Atlantic City casino boom).
# ---------------------------------------------------------------------------
print()
print("=" * 72)
print("ROBUSTNESS -- exclude NJ shore (SHORE == 1)")
print("=" * 72)

no_shore = bal[bal["SHORE"] == 0]
chain_ns = pd.get_dummies(no_shore["CHAIN"], prefix="chain", drop_first=True).astype(float)
region_ns = no_shore[["CENTRALJ", "NORTHJ", "PA1"]].astype(float)
X_ns = sm.add_constant(pd.concat([no_shore[["NJ", "CO_OWNED"]].astype(float),
                                  chain_ns, region_ns], axis=1))
assert np.linalg.matrix_rank(X_ns) == X_ns.shape[1]
m_ns = sm.OLS(no_shore["DFTE"], X_ns, missing="drop").fit(cov_type="HC1")
print(f"sample: {len(no_shore)} stores (dropped {int(bal['SHORE'].sum())} shore stores)")
print(f"beta_NJ = {m_ns.params['NJ']:6.3f}  (robust SE {m_ns.bse['NJ']:.3f})  "
      f"t = {m_ns.params['NJ']/m_ns.bse['NJ']:5.2f}  p = {m_ns.pvalues['NJ']:.3f}")

print()
print("Paper's headline finding: NJ employment ROSE relative to PA (DID ~ +2.7 FTE).")
print("i.e. no evidence that the minimum-wage hike reduced employment.")
