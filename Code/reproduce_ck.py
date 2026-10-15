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

df = pd.read_csv("data/public.csv")

# ---------------------------------------------------------------------------
# 1. Full-time-equivalent (FTE) employment, both waves
#    FTE = full-time employees + managers + 0.5 * part-time employees
# ---------------------------------------------------------------------------
df["FTE1"] = df["EMPFT"] + 0.5 * df["EMPPT"] + df["NMGRS"]
df["FTE2"] = df["EMPFT2"] + 0.5 * df["EMPPT2"] + df["NMGRS2"]

# Store status handling: Permanently closed (STATUS2=3) → FTE2=0; 
# Temporarily closed (STATUS2=2) → retain missing values
df.loc[df["STATUS2"] == 3, "FTE2"] = 0
df.loc[df["STATUS2"] == 2, "FTE2"] = np.nan

# Change in FTE employment (wave 2 - wave 1)
df["DFTE"] = df["FTE2"] - df["FTE1"]

# New Jersey dummy
df["NJ"] = df["STATE"]

# ---------------------------------------------------------------------------
# 1.5. Construct the wage gap GAP (core treatment intensity variable)
# PA stores: GAP=0
# NJ stores with WAGE_ST < 5.05: GAP = (5.05 - WAGE_ST) / WAGE_ST
# ---------------------------------------------------------------------------

df["GAP"] = 0.0
nj_need_raise = (df["STATE"] == 1) & (df["WAGE_ST"] < 5.05)
df.loc[nj_need_raise, "GAP"] = (5.05 - df.loc[nj_need_raise, "WAGE_ST"]) / df.loc[nj_need_raise, "WAGE_ST"]

# ---------------------------------------------------------------------------
# 2. Balanced sample: stores that answered wave 2 (STATUS2 == 1)
#    and have non-missing employment in both waves.
# ---------------------------------------------------------------------------
bal = df[(df["STATUS2"] == 1) &
         df["FTE1"].notna() & df["FTE2"].notna()].copy()

print("=" * 72)
print("SAMPLE COUNTS")
print("=" * 72)
print(f"Wave-1 stores in file : {len(df)}")
print(f"STATUS2 == 1 (answered): {int((df['STATUS2'] == 1).sum())}")
print(f"Balanced sample       : {len(bal)}  "
      f"(NJ = {int((bal['NJ'] == 1).sum())}, "
      f"PA = {int((bal['NJ'] == 0).sum())})")

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
    chg = sub["DFTE"]
    mc, sc = mean_se(chg)
    rows.append((label, len(sub), m1, s1, m2, s2, mc, sc))
    print(f"{label:<12} n={len(sub):>3}  before={m1:6.2f} ({s1:.2f})  "
          f"after={m2:6.2f} ({s2:.2f})  change={mc:6.2f} ({sc:.2f})")

# Difference-in-differences
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
X_base = sm.add_constant(bal[["NJ"]].astype(float))
region = bal[["SOUTHJ", "CENTRALJ", "NORTHJ", "PA1", "PA2", "SHORE"]].astype(float)

specs = {
    "(i) NJ only":              sm.add_constant(bal[["NJ"]].astype(float)),
    "(ii) + chain, co-owned":   sm.add_constant(pd.concat([bal[["NJ", "CO_OWNED"]].astype(float),
                                                           chain_dummies], axis=1)),
    "(iii) + region":           sm.add_constant(pd.concat([bal[["NJ", "CO_OWNED"]].astype(float),
                                                           chain_dummies, region], axis=1)),
}

results = []
for name, X in specs.items():
    y = bal["DFTE"]
    m = sm.OLS(y, X, missing="drop").fit(cov_type="HC1")
    b = m.params["NJ"]; se = m.bse["NJ"]
    results.append((name, b, se))
    print(f"{name:<24}  beta_NJ = {b:6.3f}  (robust SE {se:.3f})  "
          f"t = {b/se:5.2f}  p = {m.pvalues['NJ']:.3f}")

print()
print("Paper's headline finding: NJ employment ROSE relative to PA (DID ~ +2.7 FTE).")
print("i.e. no evidence that the minimum-wage hike reduced employment.")
