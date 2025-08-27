# Gap Fix 02: UPC Check Digit Validation

## Objective

Implement UPC-A check digit validation and integrate it into ID normalization so only valid UPCs are accepted as UPCs. Invalid 12-digit codes are not treated as UPCs. Preserve current behavior for EAN-13 and ASIN.

## Problem Statement

The current system classified any 12-digit numeric code as a UPC without validating the check digit. This led to:

1. Invalid product codes being treated as legitimate UPCs
2. Potential downstream issues with product identification
3. Reduced data quality for UPC-based operations

## Implementation Details

### Files Modified/Added

#### 1. `backend/lotgenius/ids.py` - New Function Added

**Added UPC check digit validation function:**

```python
def validate_upc_check_digit(upc: str) -> bool:
    """
    Validate UPC-A check digit using modulo-10 algorithm.

    Args:
        upc: String containing exactly 12 digits

    Returns:
        True if check digit is valid, False otherwise
    """
    if not isinstance(upc, str) or len(upc) != 12 or not upc.isdigit():
        return False

    # Calculate check digit using UPC-A algorithm
    # Odd positions (1st, 3rd, 5th, 7th, 9th, 11th) - indices 0,2,4,6,8,10
    odd_sum = sum(int(upc[i]) for i in [0, 2, 4, 6, 8, 10])

    # Even positions (2nd, 4th, 6th, 8th, 10th) - indices 1,3,5,7,9
    even_sum = sum(int(upc[i]) for i in [1, 3, 5, 7, 9])

    # Calculate expected check digit
    check = (10 - ((odd_sum * 3 + even_sum) % 10)) % 10

    # Compare with actual check digit (12th digit, index 11)
    return int(upc[11]) == check
```

#### 2. `backend/lotgenius/ids.py` - Updated extract_ids Function

**Modified UPC classification logic to include validation:**

**Before:**

```python
# Classify by digit count
if len(canonical_digits) == 12:
    result_upc = canonical_digits
elif len(canonical_digits) == 13:
    result_ean = canonical_digits
```

**After:**

```python
# Classify by digit count with UPC validation
if len(canonical_digits) == 12:
    if validate_upc_check_digit(canonical_digits):
        result_upc = canonical_digits
elif len(canonical_digits) == 13:
    result_ean = canonical_digits
```

**Similar change for separate UPC field processing:**

**Before:**

```python
if upc_digits and len(upc_digits) == 12:
    result_upc = upc_digits
    result_canonical = upc_digits
```

**After:**

```python
if upc_digits and len(upc_digits) == 12 and validate_upc_check_digit(upc_digits):
    result_upc = upc_digits
    result_canonical = upc_digits
```

#### 3. `backend/tests/test_ids_upc_check_digit.py` - New Test File

**Created comprehensive test suite with 10 test cases:**

```python
class TestUpcCheckDigitValidation:
    def test_validate_upc_check_digit_valid_examples(self):
        """Test validation returns True for known valid UPCs."""
        assert validate_upc_check_digit("012345678905") == True  # Common test UPC
        assert validate_upc_check_digit("123456789012") == True  # Another test UPC
        assert validate_upc_check_digit("036000291452") == True  # Coca-Cola Classic

    def test_validate_upc_check_digit_invalid_last_digit(self):
        """Test validation returns False for UPC with invalid check digit."""
        assert validate_upc_check_digit("012345678901") == False

    def test_validate_upc_check_digit_invalid_formats(self):
        """Test validation handles invalid input formats."""
        # Tests empty, too short/long, letters, None, wrong type

    def test_extract_ids_rejects_invalid_upc_in_upc_field(self):
        """Test extract_ids rejects invalid UPC in upc field."""
        # Tests that invalid UPCs aren't classified as UPCs

    def test_extract_ids_rejects_invalid_upc_in_canonical(self):
        """Test extract_ids rejects invalid UPC in upc_ean_asin field."""
        # Tests canonical field preservation with invalid UPC

    def test_extract_ids_accepts_valid_upc(self):
        """Test extract_ids accepts valid UPC and sets canonical."""
        # Tests valid UPC processing

    def test_ean_13_behavior_unchanged(self):
        """Test EAN-13 behavior is not affected by UPC validation."""
        # Regression test for EAN-13

    def test_asin_behavior_unchanged(self):
        """Test ASIN behavior is not affected by UPC validation."""
        # Regression test for ASIN

    def test_mixed_valid_and_invalid_upcs(self):
        """Test precedence with mix of valid and invalid UPCs."""
        # Tests complex precedence scenarios
```

## Algorithm Details

### UPC-A Check Digit Calculation

The UPC-A check digit uses the standard modulo-10 algorithm:

1. **Odd Position Sum**: Sum digits at positions 1, 3, 5, 7, 9, 11 (indices 0,2,4,6,8,10)
2. **Even Position Sum**: Sum digits at positions 2, 4, 6, 8, 10 (indices 1,3,5,7,9)
3. **Weighted Sum**: `odd_sum * 3 + even_sum`
4. **Check Digit**: `(10 - (weighted_sum % 10)) % 10`
5. **Validation**: Compare calculated check digit with 12th digit

### Example Calculation for "012345678905":

- Odd positions: 0+2+4+6+8+0 = 20
- Even positions: 1+3+5+7+9 = 25
- Weighted sum: 20\*3 + 25 = 85
- Check digit: (10 - (85 % 10)) % 10 = (10 - 5) % 10 = 5
- Actual 12th digit: 5 ✅ Valid

## Test Results

### New UPC Check Digit Tests

```bash
cd /c/Users/Husse/lot-genius && set PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 && python -m pytest -q backend/tests/test_ids_upc_check_digit.py
```

**Result:** ✅ `..........` (10 passed in 0.05s)

### Existing ID Extraction Tests (Regression Check)

```bash
cd /c/Users/Husse/lot-genius && set PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 && python -m pytest -q backend/tests/test_ids_extract.py
```

**Result:** ✅ `..................` (18 passed in 0.04s)

### Combined Test Run

```bash
cd /c/Users/Husse/lot-genius && set PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 && python -m pytest -q backend/tests/test_ids_upc_check_digit.py backend/tests/test_ids_extract.py
```

**Result:** ✅ `............................` (28 passed in 0.05s)

### Related Tests (Wider Regression Check)

```bash
cd /c/Users/Husse/lot-genius && set PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 && python -m pytest -q backend/tests/test_header_mapper.py backend/tests/test_parse_clean.py
```

**Result:** ✅ `........` (8 passed in 1.59s)

## Behavior Changes

### Before Implementation

```python
# Any 12-digit code was classified as UPC
item = {"upc": "999888777666"}  # Invalid check digit
result = extract_ids(item)
# Result: {"upc": "999888777666", "upc_ean_asin": "999888777666"}
```

### After Implementation

```python
# Only valid 12-digit codes are classified as UPC
item = {"upc": "999888777666"}  # Invalid check digit
result = extract_ids(item)
# Result: {"upc": None, "upc_ean_asin": None}

item = {"upc": "012345678905"}  # Valid check digit
result = extract_ids(item)
# Result: {"upc": "012345678905", "upc_ean_asin": "012345678905"}
```

### Edge Case: Invalid UPC in Canonical Field

```python
item = {"upc_ean_asin": "999888777666"}  # Invalid check digit
result = extract_ids(item)
# Result: {
#   "upc": None,                    # Not classified as UPC
#   "upc_ean_asin": "999888777666", # Canonical preserved
#   "ean": None,
#   "asin": None
# }
```

## Validation Examples

### Valid UPC Examples

- `"012345678905"` ✅ Check digit 5 is correct
- `"123456789012"` ✅ Check digit 2 is correct
- `"036000291452"` ✅ Real UPC (Coca-Cola Classic 12oz Can)

### Invalid UPC Examples

- `"012345678901"` ❌ Check digit should be 5, not 1
- `"999888777666"` ❌ Check digit validation fails
- `"12345"` ❌ Too short (not 12 digits)
- `"1234567890123"` ❌ Too long (13 digits, would be EAN)

## Impact Assessment

### Positive Impacts

✅ **Data Quality**: Only valid UPCs are classified as UPCs
✅ **Downstream Reliability**: Invalid codes won't propagate as UPCs
✅ **Industry Standard**: Implements proper UPC-A validation
✅ **Backward Compatibility**: EAN-13 and ASIN behavior unchanged
✅ **Canonical Field**: Invalid UPC codes preserved in canonical for visibility

### No Breaking Changes

- Parse-level normalization unchanged (as requested)
- EAN-13 processing unaffected (no check digit validation added)
- ASIN processing unaffected
- Canonical field preservation for invalid UPCs
- All existing tests pass

### Edge Cases Handled

1. **Invalid UPC in canonical field**: Field preserved but not classified as UPC
2. **Mixed valid/invalid UPCs**: Proper precedence maintained
3. **Type safety**: Handles non-string inputs gracefully
4. **Format validation**: Rejects non-12-digit inputs

## Validation Against Requirements

### ✅ Acceptance Criteria Met

- [x] `validate_upc_check_digit` accurately validates UPC-A check digit
- [x] `extract_ids` only classifies 12-digit codes as UPC when check digit is valid
- [x] No regressions in existing ids tests (18/18 passing)
- [x] EAN-13 behavior unchanged (13-digit codes processed without check digit validation)
- [x] ASIN behavior unchanged (10 alphanumeric codes processed normally)

### ✅ Implementation Requirements Met

- [x] Algorithm implemented exactly as specified
- [x] Integration in `extract_ids` function as specified
- [x] Parse-level normalization unchanged
- [x] UPC validity enforced only in `ids.extract_ids`
- [x] All test cases implemented and passing
- [x] Exact test commands documented with outputs

## Follow-up Considerations

### Potential Future Enhancements (Not in Scope)

1. **EAN-13 Check Digit Validation**: Could be added in future gap fix
2. **Performance Optimization**: Validation is currently O(1) and fast
3. **Extended UPC Formats**: Currently supports UPC-A only (12-digit)
4. **Logging**: Could add debug logging for validation failures

### Production Readiness

- All edge cases tested and handled
- No performance impact (simple arithmetic)
- Type-safe implementation
- Comprehensive test coverage
- Backward compatible

## Completion Status

✅ **COMPLETE** - All requirements implemented, tested, and verified.

**Files Changed:**

- Modified: `backend/lotgenius/ids.py` (added validation function and integrated)
- Added: `backend/tests/test_ids_upc_check_digit.py` (10 comprehensive tests)

**Test Results:** 28/28 tests passing, no regressions detected.

**Next Steps:** This gap fix is ready for integration. UPC validation is now properly enforced while maintaining all existing behavior for EAN-13 and ASIN processing.
