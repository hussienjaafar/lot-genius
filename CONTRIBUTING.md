# Contributing to Lot Genius

Guidelines for contributing to the Lot Genius B-Stock analysis platform.

## Getting Started

### Development Environment

1. **Fork and Clone**:

   ```cmd
   git clone https://github.com/your-fork/lot-genius.git
   cd lot-genius
   ```

2. **Setup Environment**:

   ```cmd
   python -m venv .venv
   .venv\Scripts\activate
   pip install -e backend
   pre-commit install
   ```

3. **Configuration**:

   ```cmd
   copy infra\.env.example .env
   # Edit .env with your KEEPA_API_KEY
   ```

4. **Verify Setup**:
   ```cmd
   python -m pytest backend\tests\test_api_*.py -q
   cd frontend && npm install && npm run build
   ```

## Development Guidelines

### Code Style

**Python**:

- Use Black for formatting (configured via pre-commit)
- Follow PEP 8 naming conventions
- Type hints required for all public functions
- Docstrings required for modules and public functions

```python
def calculate_roi(revenue: float, cost: float) -> float:
    """
    Calculate return on investment.

    Args:
        revenue: Total revenue from sales
        cost: Total cost including bid and fees

    Returns:
        ROI multiple (e.g., 1.25 = 25% return)
    """
    return revenue / cost if cost > 0 else 0.0
```

**TypeScript**:

- Strict mode enabled (no `any` types)
- Use interface definitions for component props
- Consistent naming with camelCase
- Tailwind CSS utility classes preferred

```typescript
interface MetricCardProps {
  label: string;
  value: string | number;
  hint?: string;
  className?: string;
}
```

### Testing Requirements

**Backend Testing**:

```cmd
# Run targeted tests (recommended)
set PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
python -m pytest backend\tests\test_your_module.py -v

# Include integration tests (requires API keys)
python -m pytest backend\tests\test_*_integration.py -v
```

**Test Categories**:

- **Unit Tests**: Fast, no external dependencies
- **Integration Tests**: Require API keys, test external services
- **End-to-End**: Full pipeline tests with real data

**Required Test Coverage**:

- New functions must have unit tests
- Bug fixes must include regression tests
- Integration tests for API-dependent functionality

**Frontend Testing**:

```cmd
cd frontend
npm run build  # TypeScript compilation
npm run lint   # ESLint validation
```

### Dependencies

**Backend Dependencies**:

- ✅ **Core Libraries**: numpy, pandas, scikit-learn, scipy, fastapi
- ✅ **Testing**: pytest, requests for API testing
- ❌ **Heavy ML**: Avoid TensorFlow, PyTorch unless critical need
- ❌ **External Services**: Minimize new API dependencies

**Frontend Dependencies**:

- ✅ **Core**: Next.js, React, TypeScript, Tailwind CSS
- ✅ **Utilities**: Minimal utility libraries if needed
- ❌ **Chart Libraries**: Use inline SVG instead of Chart.js/D3
- ❌ **UI Frameworks**: Avoid Bootstrap, Material-UI, etc.

**Adding Dependencies**:

1. Check if existing code can solve the problem
2. Propose in GitHub issue before implementing
3. Justify necessity and evaluate alternatives
4. Update documentation if API surface changes

## Pull Request Process

### Branch Naming

```cmd
# Feature branches
git checkout -b feature/add-seasonal-adjustments

# Bug fixes
git checkout -b fix/price-estimation-edge-case

# Documentation
git checkout -b docs/update-api-examples

# Hotfixes
git checkout -b hotfix/critical-validation-bug
```

### Commit Messages

Use conventional commit format:

```
type(scope): brief description

Longer description if needed explaining the why,
not just the what.

Fixes #123
```

**Types**:

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code formatting (no logic changes)
- `refactor`: Code restructuring (no behavior changes)
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples**:

```
feat(roi): add manifest risk discount factor

Add configurable discount for manifest quality uncertainty.
Includes new parameter manifest_risk_discount (default 0.95)
for conservative bid adjustments.

Fixes #45

---

fix(calibration): handle empty JSONL files gracefully

Previously crashed when calibration log was empty.
Now returns appropriate error message with guidance.

Fixes #67

---

docs(api): add SSE streaming examples

Include curl examples and event format documentation
for real-time pipeline monitoring endpoints.
```

### Pull Request Template

**Title**: Clear, concise description of changes

**Description**:

```markdown
## Summary

Brief description of what this PR does and why.

## Changes Made

- [ ] Added new feature X
- [ ] Fixed bug in Y
- [ ] Updated documentation for Z

## Testing

- [ ] Unit tests added/updated
- [ ] Integration tests pass
- [ ] Manual testing completed

## Breaking Changes

None / List any breaking changes

## Related Issues

Fixes #123
Related to #456
```

### Review Process

**Self-Review Checklist**:

- [ ] Code follows style guidelines
- [ ] Tests added for new functionality
- [ ] Documentation updated if needed
- [ ] No sensitive information committed
- [ ] Breaking changes documented
- [ ] Performance impact considered

**Reviewer Focus Areas**:

1. **Correctness**: Logic errors, edge cases
2. **Security**: Input validation, path traversal, API key handling
3. **Performance**: Efficiency, memory usage, scaling
4. **Maintainability**: Code clarity, documentation, test coverage

**Review Timeline**:

- Small changes (< 100 lines): 1-2 business days
- Medium changes (100-500 lines): 2-3 business days
- Large changes (> 500 lines): 3-5 business days

## Multi-Agent Development

### Run Log Requirements

When implementing multi-step features, document your work:

**Run Log Template**:

````markdown
# Step X: Feature Name

## Overview

Brief description of what was implemented.

## Changes Made

### New Files

- `path/to/new_file.py` - Purpose and key functions
- `path/to/another_file.ts` - Component description

### Modified Files

- `existing_file.py` - What changed and why
- `config.json` - Configuration updates

## Testing Results

- Unit tests: X passed, Y added
- Integration tests: Status
- Manual testing: Key scenarios validated

## Assumptions & Limitations

- List any assumptions made
- Known limitations or future work needed

## Commands Run

```cmd
python -m pytest backend\tests\test_new_feature.py
npm run build
```
````

````

**File Location**: `multi_agent/runlogs/step_XX_feature_name.md`

### Code Quality Standards

**Defensive Programming**:
```python
def process_manifest(file_path: str) -> dict:
    """Process manifest with robust error handling."""
    if not file_path:
        raise ValueError("file_path cannot be empty")

    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"Manifest not found: {file_path}")

    try:
        # Processing logic
        return result
    except Exception as e:
        logger.error(f"Failed to process manifest {file_path}: {e}")
        raise
````

**Input Validation**:

```python
def optimize_bid(roi_target: float, risk_threshold: float) -> dict:
    """Optimize bid with parameter validation."""
    if not 1.0 <= roi_target <= 10.0:
        raise ValueError(f"roi_target must be 1.0-10.0, got {roi_target}")

    if not 0.5 <= risk_threshold <= 1.0:
        raise ValueError(f"risk_threshold must be 0.5-1.0, got {risk_threshold}")

    # Implementation
```

**Error Context**:

```python
try:
    result = expensive_operation()
except APIError as e:
    logger.error(f"API failed for manifest {manifest_id}: {e}")
    # Provide helpful error message to user
    raise ProcessingError(f"Unable to resolve product IDs. Check API key and network.") from e
```

## Security Guidelines

### Sensitive Information

**Never Commit**:

- API keys or tokens
- Database credentials
- Production configuration files
- Personal information in test data

**Use Environment Variables**:

```python
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("KEEPA_API_KEY")
if not api_key:
    raise ValueError("KEEPA_API_KEY environment variable not set")
```

**Test Data Sanitization**:

```python
# Good: Use synthetic test data
test_manifest = pd.DataFrame([
    {"sku_local": "TEST-001", "title": "Test Widget", "condition": "New"}
])

# Bad: Real customer data in tests
# test_manifest = pd.read_csv("customer_manifest.csv")  # DON'T DO THIS
```

### API Security

**Input Validation**:

```python
from pydantic import BaseModel, validator

class OptimizeRequest(BaseModel):
    roi_target: float
    risk_threshold: float

    @validator('roi_target')
    def validate_roi_target(cls, v):
        if not 1.0 <= v <= 10.0:
            raise ValueError('roi_target must be between 1.0 and 10.0')
        return v
```

**Path Safety**:
All file paths are validated through the existing path safety system.
Don't bypass these checks without security review.

## Performance Guidelines

### Optimization Priorities

1. **Correctness First**: Get it working correctly
2. **Profile Before Optimizing**: Measure actual bottlenecks
3. **Optimize Hot Paths**: Focus on frequently called code
4. **Memory Management**: Be mindful of large dataset processing

### Common Patterns

**Efficient Data Processing**:

```python
# Good: Process in chunks for large datasets
def process_large_manifest(df: pd.DataFrame) -> pd.DataFrame:
    chunk_size = 1000
    results = []

    for i in range(0, len(df), chunk_size):
        chunk = df.iloc[i:i+chunk_size]
        processed = process_chunk(chunk)
        results.append(processed)

    return pd.concat(results, ignore_index=True)
```

**API Rate Limiting**:

```python
import time
from functools import wraps

def rate_limit(calls_per_second: float = 1.0):
    def decorator(func):
        min_interval = 1.0 / calls_per_second
        last_called = [0.0]

        @wraps(func)
        def wrapper(*args, **kwargs):
            elapsed = time.time() - last_called[0]
            if elapsed < min_interval:
                time.sleep(min_interval - elapsed)

            last_called[0] = time.time()
            return func(*args, **kwargs)

        return wrapper
    return decorator
```

### Caching Strategy

```python
from functools import lru_cache
from typing import Optional

@lru_cache(maxsize=1000)
def expensive_calculation(param: str) -> float:
    """Cache results of expensive calculations."""
    # Implementation
    return result

# SQLite cache for API results (already implemented)
# Use existing cache infrastructure when possible
```

## Documentation Standards

### Code Documentation

**Module Docstrings**:

```python
"""
ROI optimization module.

This module implements Monte Carlo simulation for finding optimal lot bids
under configurable risk constraints. Main entry point is optimize_bid().

Example:
    from lotgenius.roi import optimize_bid
    result = optimize_bid(items_df, roi_target=1.25, risk_threshold=0.80)
"""
```

**Function Docstrings** (Google Style):

```python
def simulate_revenue(items: pd.DataFrame, bid: float, sims: int = 1000) -> np.ndarray:
    """
    Simulate revenue distributions for given bid amount.

    Args:
        items: DataFrame with price estimates and sell probabilities
        bid: Bid amount for lot acquisition
        sims: Number of Monte Carlo simulations

    Returns:
        Array of simulated revenue values

    Raises:
        ValueError: If bid is negative or items DataFrame is empty

    Example:
        >>> items = pd.DataFrame({'est_price_mu': [25.0], 'sell_p60': [0.7]})
        >>> revenue = simulate_revenue(items, bid=100.0, sims=1000)
        >>> print(f"Expected revenue: {revenue.mean():.2f}")
        Expected revenue: 125.50
    """
```

### API Documentation

FastAPI automatically generates OpenAPI docs, but include examples:

````python
@router.post("/optimize", response_model=OptimizeResponse)
async def optimize_lot(request: OptimizeRequest):
    """
    Optimize lot bid using Monte Carlo simulation.

    Example request:
    ```json
    {
      "items_csv": "data/processed_items.csv",
      "roi_target": 1.25,
      "risk_threshold": 0.80,
      "sims": 2000
    }
    ```

    Returns optimal bid and risk metrics.
    """
````

## Release Process

### Version Numbering

Follow semantic versioning (semver):

- **MAJOR**: Breaking API changes
- **MINOR**: New features, backward compatible
- **PATCH**: Bug fixes, backward compatible

Examples: `1.0.0`, `1.1.0`, `1.1.1`

### Release Checklist

**Pre-Release**:

- [ ] All tests passing
- [ ] Documentation updated
- [ ] Breaking changes documented
- [ ] Performance impact assessed
- [ ] Security review for sensitive changes

**Release**:

- [ ] Tag version: `git tag v1.1.0`
- [ ] Update CHANGELOG.md
- [ ] Deploy to staging environment
- [ ] Run end-to-end tests
- [ ] Deploy to production
- [ ] Monitor for issues

## Community Guidelines

### Communication

- **Be Respectful**: Treat all contributors with respect
- **Be Constructive**: Provide actionable feedback
- **Be Patient**: Code review and discussion take time
- **Be Collaborative**: Work together toward shared goals

### Issue Reporting

**Good Issue Reports Include**:

- Clear, descriptive title
- Steps to reproduce
- Expected vs actual behavior
- Environment details (OS, Python version)
- Error messages and logs
- Minimal example code

**Issue Labels**:

- `bug`: Something is broken
- `enhancement`: New feature request
- `documentation`: Documentation improvements
- `question`: Usage questions
- `help-wanted`: Good for new contributors

### Getting Help

1. **Documentation**: Check docs/ directory first
2. **GitHub Issues**: Search existing issues
3. **GitHub Discussions**: For questions and ideas
4. **Code Review**: Ask for feedback on complex changes

---

Thank you for contributing to Lot Genius! Your efforts help improve B-Stock investment analysis for everyone.
