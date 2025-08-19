from __future__ import annotations

import great_expectations as ge
import pandas as pd

ALLOWED_CONDITIONS = {"New", "LikeNew", "UsedGood", "UsedFair", "Salvage"}


def run_ge_checks(df: pd.DataFrame) -> dict:
    """
    Minimal, programmatic GE checks on a *mapped* DataFrame (some columns may be missing).
    Returns a dict with 'success' and 'results' (list of {expectation, success}).
    """
    gdf = ge.from_pandas(df.copy())
    results = []

    # Expect at least 1 row
    r = gdf.expect_table_row_count_to_be_between(min_value=1)
    results.append({"expectation": "row_count>=1", "success": r.success})

    # If quantity exists, expect strictly positive
    if "quantity" in gdf.columns:
        r = gdf.expect_column_values_to_be_between(
            "quantity", min_value=1, strict_min=False
        )
        results.append({"expectation": "quantity>0", "success": r.success})

    # If condition exists, expect values within enum
    if "condition" in gdf.columns:
        r = gdf.expect_column_values_to_be_in_set("condition", list(ALLOWED_CONDITIONS))
        results.append({"expectation": "condition in enum", "success": r.success})

    # If msrp exists, expect non-negative (allow nulls)
    if "msrp" in gdf.columns:
        non_null = gdf["msrp"].dropna()
        if not non_null.empty:
            r = gdf.expect_column_values_to_be_between("msrp", min_value=0.0)
            results.append({"expectation": "msrp>=0", "success": r.success})

    overall = all(x["success"] for x in results) if results else True
    return {"success": overall, "results": results}
