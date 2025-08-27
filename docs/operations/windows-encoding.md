# Windows Console Encoding Guide

This document provides guidance for working with Lot Genius CLI tools on Windows to prevent Unicode/encoding issues.

## Overview

Gap Fix 08 (Windows Console Encoding Hardening) eliminates Unicode/encoding issues in CLI tools and logs to ensure proper Windows compatibility.

## Encoding Standards

### File I/O

- **All file operations use explicit UTF-8 encoding**: `encoding='utf-8'`
- **CSV operations**: `pd.read_csv(..., encoding='utf-8')` and `df.to_csv(..., encoding='utf-8')`
- **JSON/text files**: `open(path, 'w', encoding='utf-8')`

### Console Output

- **Unicode characters replaced with ASCII equivalents**:
  - `->` -> `->` (arrow)
  - `<=` -> `<=` (less than or equal)
  - `>=` -> `>=` (greater than or equal)
  - `beta` -> `beta` (Greek beta)
  - `sigma` -> `sigma` (Greek sigma)
  - `mu` -> `mu` (Greek mu)

## Implementation Details

### Files Updated

All CLI files in `backend/cli/` have been updated:

1. **calibration_apply.py** - Added UTF-8 encoding for file I/O
2. **calibration_report.py** - Replaced `->` with `->` in console output
3. **calibration_run.py** - Added UTF-8 encoding for JSON output
4. **estimate_price.py** - Replaced Greek letters with ASCII equivalents, added UTF-8 encoding
5. **estimate_sell.py** - Replaced `<=` and `beta` with ASCII equivalents, added UTF-8 encoding
6. **join_bid.py** - Added UTF-8 encoding for CSV operations
7. **map_preview.py** - Added UTF-8 encoding for CSV reading
8. **optimize_bid.py** - Added UTF-8 encoding for CSV operations
9. **parse_clean.py** - Replaced `->` with `->`, added UTF-8 encoding
10. **resolve_ids.py** - Added UTF-8 encoding for CSV output
11. **stress_scenarios.py** - Added UTF-8 encoding for file operations
12. **sweep_bid.py** - Replaced `>=` with `>=`, added UTF-8 encoding

### Verification

All CLI commands have been tested and confirmed working without encoding errors:

```bash
cd "C:\Users\Husse\lot-genius"
python -m backend.cli.estimate_sell --help     # OK No encoding errors
python -m backend.cli.estimate_price --help    # OK No encoding errors
python -m backend.cli.calibration_report --help # OK No encoding errors
python -m backend.cli.parse_clean --help       # OK No encoding errors
```

## Best Practices

### For Developers

1. **Always specify encoding**: Use `encoding='utf-8'` for all file operations
2. **Test on Windows**: Verify CLI commands work in Windows Command Prompt and PowerShell
3. **Avoid Unicode in help text**: Use ASCII equivalents for mathematical symbols
4. **Use UTF-8 for data files**: Ensure CSV, JSON, and text outputs use UTF-8 encoding

### For Users

1. **Console compatibility**: All CLI tools now work with standard Windows consoles
2. **File compatibility**: Generated files use UTF-8 encoding for cross-platform compatibility
3. **No special setup required**: Windows users can use CLI tools without additional configuration

## Error Prevention

### Common Windows Encoding Issues (Now Fixed)

- X **UnicodeEncodeError with Unicode symbols**: Fixed by replacing with ASCII
- X **File encoding inconsistencies**: Fixed by explicit UTF-8 specification
- X **Console display problems**: Fixed by using ASCII-compatible characters

### If You Encounter Issues

1. **Verify Python encoding**: `python -c "import locale; print(locale.getpreferredencoding())"`
2. **Check console codepage**: `chcp` (should show 65001 for UTF-8)
3. **Use PowerShell or modern terminals**: Better Unicode support than legacy Command Prompt

## Status: OK COMPLETED

Gap Fix 08: Windows Console Encoding Hardening has been successfully implemented:

- OK **All CLI files updated** with UTF-8 encoding and ASCII-safe output
- OK **Unicode characters replaced** with ASCII equivalents
- OK **CLI commands tested** and verified working on Windows
- OK **Documentation created** for ongoing maintenance

The Lot Genius CLI tools are now fully compatible with Windows console environments.
