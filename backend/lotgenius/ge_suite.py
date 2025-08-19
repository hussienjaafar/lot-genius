from __future__ import annotations

import pandas as pd

try:
    import great_expectations as ge

    HAS_GE = hasattr(ge, "from_pandas")
except Exception:
    ge = None
    HAS_GE = False

ALLOWED_CONDITIONS = {"New", "LikeNew", "UsedGood", "UsedFair", "Salvage"}


def _pandas_checks(df: pd.DataFrame) -> list[dict]:
    out = []
    out.append({"expectation": "row_count>=1", "success": len(df) >= 1})
    if "quantity" in df.columns:
        q = pd.to_numeric(df["quantity"], errors="coerce")
        out.append(
            {
                "expectation": "quantity>0",
                "success": (q.dropna() > 0).all() if not q.dropna().empty else True,
            }
        )
    if "condition" in df.columns:
        ok = df["condition"].dropna().isin(ALLOWED_CONDITIONS).all()
        out.append({"expectation": "condition in enum", "success": ok})
    if "msrp" in df.columns:
        m = pd.to_numeric(df["msrp"], errors="coerce").dropna()
        out.append(
            {
                "expectation": "msrp>=0",
                "success": (m >= 0).all() if not m.empty else True,
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
        results.append({"expectation": "row_count>=1", "success": r.success})
        if "quantity" in gdf.columns:
            r = gdf.expect_column_values_to_be_between(
                "quantity", min_value=1, strict_min=False
            )
            results.append({"expectation": "quantity>0", "success": r.success})
        if "condition" in gdf.columns:
            r = gdf.expect_column_values_to_be_in_set(
                "condition", list(ALLOWED_CONDITIONS)
            )
            results.append({"expectation": "condition in enum", "success": r.success})
        if "msrp" in gdf.columns:
            non_null = gdf["msrp"].dropna()
            if not non_null.empty:
                r = gdf.expect_column_values_to_be_between("msrp", min_value=0.0)
                results.append({"expectation": "msrp>=0", "success": r.success})
    else:
        results = _pandas_checks(df.copy())

    overall = all(x["success"] for x in results) if results else True
    return {"success": overall, "results": results}
