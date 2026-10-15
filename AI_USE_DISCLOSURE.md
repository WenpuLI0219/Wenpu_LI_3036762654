# AI-Use Disclosure

**Project:** Replication of Card & Krueger (1994), "Minimum Wages and
Employment" (ECON6067).

This disclosure records how an AI assistant (Claude Code, running the
`deepseek-v4-pro` model) was used in this project, how its output was verified,
and the specific errors that were caught and corrected. All claims below refer
to the concrete, documented working history of this project.

---

## 1. Where and how AI was used

| Stage | What the AI did | What the human did |
|---|---|---|
| **Data exploration** | Loaded `public.csv`, ran diagnostics (missing values, dtypes, outliers, duplicate IDs, region-dummy structure). | Directed which data-quality questions to investigate. |
| **Coding** | Wrote `reproduce_ck.py` (core replication), `clean_data.py` (cleaned dataset), and `extension.py` (extensions). | Reviewed the code, then identified four methodological problems in it (see §3). |
| **Analysis** | Ran the regressions and DID calculations; produced the numeric results. | Interpreted the results; provided the domain judgment on which specifications were correct. |
| **Writing** | Drafted `REPRODUCTION.md` (methodology) and `EMPIRICAL_REPORT.md` (the report). | Specified the required structure and corrected content. |

In short: the AI carried out the mechanical work — writing code, running it,
and drafting text — while the **human set the research direction, supplied the
econometric judgment, and caught the substantive errors** the AI initially
made. The AI did *not* independently originate the research design; it
implemented and checked a design specified and corrected by the human.

---

## 2. How AI-generated code, analysis, and writing were checked

The central safeguard was that **every quantitative claim was validated against
the data and against the original paper**, not taken from the AI on faith.

1. **Execution over assertion.** No result was accepted until the corresponding
   script actually ran and printed it. Several claims were checked by running
   small diagnostic scripts against `public.csv` before being believed.

2. **Benchmarking against the published paper.** The strongest check was that
   the replicated DID had to reproduce Card & Krueger's published estimate.
   After corrections, our DID (**2.75**) matched the paper (**2.76**), and the
   NJ pre-treatment mean (20.43) matched the paper (20.44). A mismatch was
   treated as evidence of a bug, not shrugged off.

3. **Formal correctness checks in code.** A `matrix_rank` assertion was added to
   the regression so that any future collinear specification fails loudly
   rather than silently producing a wrong coefficient.

4. **Human review of the econometrics.** The human independently identified the
   four specification errors in §3 below. The AI's role was to *verify each
   against the data* (e.g. confirming that `SOUTHJ+CENTRALJ+NORTHJ+PA1+PA2 = 1`
   and that `NJ = SOUTHJ+CENTRALJ+NORTHJ`, which established the collinearity).

5. **Cross-checking of documentation.** The written documents were checked for
   consistency with the code's actual output; where the AI's prose and the
   numbers disagreed, the prose was corrected (see §3, item 6).

---

## 3. Important AI errors or suggestions that were corrected or rejected

These are the substantive mistakes the AI made or proposed, and how each was
handled. The most consequential ones were **caught by the human, not the AI**.

### (a) Closed stores silently excluded — *caught by the human*

The first version of the script set `FTE2 = 0` for permanently closed stores
(`STATUS2 == 3`) but then filtered the sample to `STATUS2 == 1` only, dropping
them. This was self-contradictory and would have introduced survivorship bias.
The human flagged it; the AI confirmed the closed stores exist in the data and
fixed the sample filter to `STATUS2 ∈ {1, 3}`. After this fix the DID moved
from 2.72 to 2.75, landing on the paper's 2.76.

### (b) Region fixed effects caused multicollinearity — *caught by the human*

The first regression included the `NJ` dummy together with all five region
dummies. Because `NJ = SOUTHJ+CENTRALJ+NORTHJ` and
`SOUTHJ+CENTRALJ+NORTHJ+PA1+PA2 = 1`, the design matrix was rank-deficient, and
the AI had reported a coefficient (1.529) that was a pseudo-inverse artifact,
not a valid OLS estimate. The human flagged it; the AI confirmed the rank
deficiency with `np.linalg.matrix_rank` and corrected the specification
(dropping reference categories and adding a rank assertion).

### (c) Missing wage-gap model — *caught by the human*

The AI computed the `GAP` treatment-intensity variable but never used it in any
regression, omitting a core result of the paper. The human pointed this out;
the AI added the wage-gap reduced form (β = 13.08, p = 0.051).

### (d) SHORE treated as a control instead of an exclusion — *caught by the human*

The AI included `SHORE` as a region control. The human noted that the paper
*excludes* the New Jersey shore (an area hit by the Atlantic City casino boom)
in robustness checks rather than controlling for it. The AI moved `SHORE` out
of the controls and added a shore-exclusion robustness run.

### (e) Wrong proposed fix for the missing-wage GAP — *AI error, self-corrected*

When discussing how to handle the 17 NJ stores with a missing starting wage,
the AI first suggested *backfilling* `WAGE_ST` from the second-wave wage
`WAGE_ST2`. On closer inspection the AI recognised this was wrong — `WAGE_ST2`
is the *post*-raise wage, so backfilling would still produce `GAP = 0` — and
corrected the approach to *marking* `GAP` as missing instead.

### (f) Two coding bugs — *AI errors, fixed during execution*

- In `clean_data.py` the AI wrote `int(... .sum())` as `int(...).sum()`,
  applying `int()` to a Series; the script threw a `TypeError` and was fixed.
- In `extension.py` the AI referenced a `ROW_ID` column that had not been
  created, causing a `KeyError`; it was replaced with a direct boolean mask.

### (g) Imprecise explanation of the DID discrepancy — *AI error, corrected*

The AI initially described the small gap between its DID (2.75) and the paper's
(2.76) as "rounding," when the difference actually reflects slightly different
sample-selection choices. The AI flagged this correction itself in the
methodology write-up.

---

## Summary

The AI was an efficient implementation and documentation tool, but it was **not
the source of econometric correctness** in this project. Its initial
reproduction contained four substantive specification errors — the closed-store
handling, the region multicollinearity, the missing wage-gap model, and the
SHORE control — all of which were identified by the human and then verified
and fixed with the AI's assistance. The final results are trustworthy precisely
because they were benchmarked against the published paper and subjected to
human review of the identification strategy.
