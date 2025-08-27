from __future__ import annotations

import pandas as pd

from .schema import ConditionEnum

try:
    import great_expectations as ge

    HAS_GE = hasattr(ge, "from_pandas")
except Exception:
    ge = None
    HAS_GE = False

ALLOWED_CONDITIONS = {e.value for e in ConditionEnum}


def _pandas_checks(df: pd.DataFrame) -> list[dict]:
    out = []
    out.append({"expectation": "row_count>=1", "success": bool(len(df) >= 1)})
    if "quantity" in df.columns:
        q = pd.to_numeric(df["quantity"], errors="coerce")
        out.append(
            {
                "expectation": "quantity>0",
                "success": bool(
                    (q.dropna() > 0).all() if len(q.dropna()) > 0 else True
                ),
            }
        )
    if "condition" in df.columns:
        ok = df["condition"].dropna().isin(ALLOWED_CONDITIONS).all()
        out.append({"expectation": "condition in enum", "success": bool(ok)})
    if "msrp" in df.columns:
        m = pd.to_numeric(df["msrp"], errors="coerce").dropna()
        out.append(
            {
                "expectation": "msrp>=0",
                "success": bool((m >= 0).all() if len(m) > 0 else True),
            }
        )
    return out


def run_ge_checks(df: pd.DataFrame) -> dict:
    """
    Minimal checks on a mapped DataFrame. Uses Great Expectations if available,
    otherwise falls back to equivalent pandas logic.
    """
    if HAS_GE:
        gdf = ge.from_pandas(df.copy())
        results = []
        r = gdf.expect_table_row_count_to_be_between(min_value=1)
        results.append({"expectation": "row_count>=1", "success": bool(r.success)})
        if "quantity" in gdf.columns:
            r = gdf.expect_column_values_to_be_between(
                "quantity", min_value=1, strict_min=False
            )
            results.append({"expectation": "quantity>0", "success": bool(r.success)})
        if "condition" in gdf.columns:
            r = gdf.expect_column_values_to_be_in_set(
                "condition", list(ALLOWED_CONDITIONS)
            )
            results.append(
                {"expectation": "condition in enum", "success": bool(r.success)}
            )
        if "msrp" in gdf.columns:
            non_null = gdf["msrp"].dropna()
            if len(non_null) > 0:
                r = gdf.expect_column_values_to_be_between("msrp", min_value=0.0)
                results.append({"expectation": "msrp>=0", "success": bool(r.success)})
    else:
        results = _pandas_checks(df.copy())

    # Normalize all successes to plain bool (handles numpy.bool_ too)
    results = [
        {"expectation": it["expectation"], "success": bool(it["success"])}
        for it in results
    ]

    overall = all(x["success"] for x in results) if results else True
    return {"success": overall, "results": results}
