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
    """Clean the raw survey data. Returns (df, log) where log lists changes.

    Does not silently mutate: every step is logged so the reproduction stays
    auditable. Nothing is dropped here (the paper keeps the outlier and the
    duplicate); they are flagged so downstream code can decide.
    """
    log = []
    log.append(f"raw data: {len(df)} rows x {df.shape[1]} columns")

    # (1) SHEET is not a unique key -- sheet 407 is shared by two distinct
    #     stores (a PA KFC and a NJ Wendy's). Re-key on a unique row id.
    n_dup = int(df["SHEET"].duplicated(keep=False).sum())
    df = df.reset_index(drop=True)
    df["ROW_ID"] = df.index
    log.append(f"SHEET duplicated entries: {n_dup} -> added unique ROW_ID (no rows dropped)")

    # (2) Missing starting wage must not be silently treated as "no raise".
    #     Flag it here; GAP is set to missing (NaN) for those stores below.
    n_missing_wage_nj = int(((df["STATE"] == 1) & df["WAGE_ST"].isna()).sum())
    log.append(f"NJ stores with missing WAGE_ST: {n_missing_wage_nj} "
               f"(GAP set to missing, not 0)")

    # (3) Outlier flag: an extreme store (FTE ~ 85) would tug the NJ mean.
    df["FTE1"] = df["EMPFT"] + 0.5 * df["EMPPT"] + df["NMGRS"]
    df["IS_OUTLIER"] = df["FTE1"] > 75
    log.append(f"flagged {int(df['IS_OUTLIER'].sum())} store(s) with FTE1 > 75 as outlier")

    return df, log


df = pd.read_csv("data/public.csv")
df, preprocess_log = preprocess(df)

print("=" * 72)
print("PREPROCESSING LOG")
print("=" * 72)
for line in preprocess_log:
    print(" -", line)

# ---------------------------------------------------------------------------
# 1. Variables: FTE employment, change, treatment dummy, wage gap
# ---------------------------------------------------------------------------
# FTE = full-time employees + managers + 0.5 * part-time employees
df["FTE2"] = df["EMPFT2"] + 0.5 * df["EMPPT2"] + df["NMGRS2"]   # FTE1 built in preprocess

# Second-wave store status:
#   STATUS2 == 3 (permanent closure) -> 0 employees
#   STATUS2 == 2 (temporary closure) -> missing (long-run employment unknown)
df.loc[df["STATUS2"] == 3, "FTE2"] = 0
df.loc[df["STATUS2"] == 2, "FTE2"] = np.nan

df["DFTE"] = df["FTE2"] - df["FTE1"]   # change in FTE employment
df["NJ"]   = df["STATE"]               # 1 = New Jersey, 0 = Pennsylvania

# GAP = proportional increase needed to reach the $5.05 minimum.
#   PA stores                        -> 0 (no bite)
#   NJ stores with WAGE_ST < 5.05    -> (5.05 - WAGE_ST) / WAGE_ST
#   NJ stores with WAGE_ST >= 5.05   -> 0 (already compliant)
#   NJ stores with missing WAGE_ST   -> missing (unknown bite), NOT 0
df["GAP"] = 0.0
df.loc[df["STATE"] == 0, "GAP"] = 0.0
nj = df["STATE"] == 1
df.loc[nj & df["WAGE_ST"].isna(), "GAP"] = np.nan
df.loc[nj & (df["WAGE_ST"] < 5.05), "GAP"] = (5.05 - df["WAGE_ST"]) / df["WAGE_ST"]

# ---------------------------------------------------------------------------
# 2. Balanced sample: answered wave 2 and has employment in both waves
# ---------------------------------------------------------------------------
bal = df[(df["STATUS2"] == 1) &
         df["FTE1"].notna() & df["FTE2"].notna()].copy()

print()
print("=" * 72)
print("SAMPLE COUNTS")
print("=" * 72)
print(f"Wave-1 stores in file : {len(df)}")
print(f"STATUS2 == 1 (answered): {int((df['STATUS2'] == 1).sum())}")
print(f"Balanced sample       : {len(bal)}  "
      f"(NJ = {int((bal['NJ'] == 1).sum())}, "
      f"PA = {int((bal['NJ'] == 0).sum())})")

# GAP summary (why the missing-handling fix matters)
print()
print("=" * 72)
print("GAP SUMMARY (treatment intensity)")
print("=" * 72)
print(f"NJ stores with missing GAP (unknown starting wage): "
      f"{int(bal['GAP'].isna().sum())}")
print(f"GAP distribution among NJ stores with valid GAP:")
print(bal.loc[bal["NJ"] == 1, "GAP"].describe().round(3).to_string())

# ---------------------------------------------------------------------------
# 3. Table 3 reproduction: mean FTE employment before / after, by state
# ---------------------------------------------------------------------------
def mean_se(x):
    return x.mean(), x.std(ddof=1) / np.sqrt(x.count())

print()
print("=" * 72)
print("TABLE 3 (balanced sample) -- mean FTE employment per store")
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
# 4. Regression-based DID (Table 4 style), with controls added progressively
# ---------------------------------------------------------------------------
print()
print("=" * 72)
print("TABLE 4 style: regress change in FTE on NJ dummy (+ controls)")
print("=" * 72)

chain_dummies = pd.get_dummies(bal["CHAIN"], prefix="chain", drop_first=True).astype(float)
region = bal[["SOUTHJ", "CENTRALJ", "NORTHJ", "PA1", "PA2", "SHORE"]].astype(float)

specs = {
    "(i) NJ only":              sm.add_constant(bal[["NJ"]].astype(float)),
    "(ii) + chain, co-owned":   sm.add_constant(pd.concat([bal[["NJ", "CO_OWNED"]].astype(float),
                                                           chain_dummies], axis=1)),
    "(iii) + region":           sm.add_constant(pd.concat([bal[["NJ", "CO_OWNED"]].astype(float),
                                                           chain_dummies, region], axis=1)),
}

for name, X in specs.items():
    y = bal["DFTE"]
    m = sm.OLS(y, X, missing="drop").fit(cov_type="HC1")
    b = m.params["NJ"]; se = m.bse["NJ"]
    print(f"{name:<24}  beta_NJ = {b:6.3f}  (robust SE {se:.3f})  "
          f"t = {b/se:5.2f}  p = {m.pvalues['NJ']:.3f}")

print()
print("Paper's headline finding: NJ employment ROSE relative to PA (DID ~ +2.7 FTE).")
print("i.e. no evidence that the minimum-wage hike reduced employment.")
