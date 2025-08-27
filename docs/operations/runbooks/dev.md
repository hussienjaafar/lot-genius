# Development Runbook

Local development environment setup and common workflows for Lot Genius.

## Prerequisites

### System Requirements

- **Operating System**: Windows 10/11, macOS, or Linux
- **Python**: Version 3.13+ (3.13 recommended)
- **Node.js**: Version 18+ for frontend development
- **Git**: Version control
- **Optional**: Docker for containerized development

### Windows-Specific Setup

**Python Installation**:

```cmd
# Download Python 3.13 from python.org
# Ensure "Add to PATH" is checked during installation

# Verify installation
python --version
pip --version
```

**Virtual Environment**:

```cmd
# Create virtual environment
python -m venv .venv

# Activate (Command Prompt)
.venv\Scripts\activate

# Activate (PowerShell)
.venv\Scripts\Activate.ps1

# Deactivate
deactivate
```

**Git Configuration**:

```cmd
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
```

## Repository Setup

### 1. Clone Repository

```cmd
git clone https://github.com/your-org/lot-genius.git
cd lot-genius
```

### 2. Backend Setup

**Install Dependencies**:

```cmd
# Activate virtual environment
.venv\Scripts\activate

# Upgrade pip and install tools
pip install -U pip pre-commit

# Install backend package in editable mode
pip install -e backend

# Setup pre-commit hooks
pre-commit install
```

**Environment Configuration**:

```cmd
# Copy environment template
copy infra\.env.example .env

# Edit .env file with your settings
notepad .env
```

**Required Environment Variables**:

```bash
# Keepa API key (required for ID resolution and pricing)
KEEPA_API_KEY=your_keepa_api_key_here

# Optional API key for server authentication
LOTGENIUS_API_KEY=your_server_api_key

# Optional: Override default settings
SELLTHROUGH_HORIZON_DAYS=60
MIN_ROI_TARGET=1.25
RISK_THRESHOLD=0.80
```

### 3. Frontend Setup

```cmd
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Verify installation
npm run build
```

### 4. Verify Installation

**Backend Tests**:

```cmd
# Run quick smoke tests
set PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
python -m pytest backend\tests\test_api_*.py -q

# Run specific module tests
python -m pytest backend\tests\test_roi_mc.py -v
```

**Frontend Build**:

```cmd
cd frontend
npm run lint
npm run build
```

## Development Workflows

### Backend Development

#### Starting API Server

```cmd
# Development mode with auto-reload
uvicorn backend.app.main:app --port 8787 --reload

# Production mode
uvicorn backend.app.main:app --host 0.0.0.0 --port 8787
```

**Verification**:

```cmd
# Test health endpoint
curl http://localhost:8787/healthz

# Expected response: {"status": "ok", "timestamp": "..."}
```

#### CLI Development

**Common Commands**:

```cmd
# Test manifest validation
python -m backend.cli.validate_manifest data\samples\minimal.csv --show-coverage

# Test ID resolution (no API calls)
python -m backend.cli.resolve_ids data\samples\minimal.csv --no-network

# Quick optimization test
python -m backend.cli.optimize_bid data\samples\processed.csv --sims 100
```

**Creating Test Data**:

```cmd
# Generate minimal test CSV
python -c "
import pandas as pd
df = pd.DataFrame([
    {'sku_local': 'TEST-001', 'title': 'Test Item', 'condition': 'New'},
    {'sku_local': 'TEST-002', 'title': 'Another Item', 'condition': 'Used'}
])
df.to_csv('test_manifest.csv', index=False)
"
```

#### Testing Workflows

**Targeted Tests** (recommended):

```cmd
# Disable plugin autoload for speed
set PYTEST_DISABLE_PLUGIN_AUTOLOAD=1

# Run specific test files
python -m pytest backend\tests\test_roi_mc.py -q
python -m pytest backend\tests\test_calibration_log.py -v

# Run with coverage
python -m pytest backend\tests\test_survivorship_*.py --cov=lotgenius.survivorship
```

**Integration Tests** (requires API key):

```cmd
# Set API key for integration tests
set KEEPA_API_KEY=your_key_here

# Run integration tests
python -m pytest backend\tests\test_*_integration.py -v
```

**Test Categories**:

- **Unit Tests**: `test_*.py` (no external dependencies)
- **Integration Tests**: `test_*_integration.py` (requires API keys)
- **End-to-End**: `test_e2e_*.py` (full pipeline tests)

### Frontend Development

#### Development Server

```cmd
cd frontend

# Start development server
npm run dev

# Visit http://localhost:3000
```

**Hot Reload Features**:

- Component changes update immediately
- TypeScript compilation errors shown in browser
- Tailwind CSS changes applied instantly

#### Component Development

**Creating New Components**:

```typescript
// frontend/components/NewComponent.tsx
interface NewComponentProps {
  title: string;
  value: number;
  className?: string;
}

export default function NewComponent({ title, value, className = '' }: NewComponentProps) {
  return (
    <div className={`p-4 border rounded-lg ${className}`}>
      <h3 className="text-lg font-medium">{title}</h3>
      <p className="text-2xl font-bold">{value}</p>
    </div>
  );
}
```

**Testing Components**:

```cmd
# Type checking
npm run build

# Linting
npm run lint

# Manual testing in browser
npm run dev
```

#### API Integration

**Testing API Calls**:

```typescript
// frontend/lib/api.ts
export async function testApiCall() {
  try {
    const response = await fetch("http://localhost:8787/healthz");
    const data = await response.json();
    console.log("API Response:", data);
  } catch (error) {
    console.error("API Error:", error);
  }
}
```

**CORS Configuration**: API server includes CORS headers for localhost development.

## Common Development Tasks

### Adding New CLI Command

**1. Create Command Module**:

```python
# backend/lotgenius/cli/new_command.py
import argparse
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description="New command description")
    parser.add_argument("input_file", help="Input file path")
    parser.add_argument("--output", "-o", help="Output file path")

    args = parser.parse_args()

    # Command implementation
    print(f"Processing {args.input_file}")
    # ... implementation ...

if __name__ == "__main__":
    main()
```

**2. Add CLI Entry Point**:

```cmd
# Test command directly
python -m backend.cli.new_command --help
```

**3. Write Tests**:

```python
# backend/tests/test_cli_new_command.py
def test_new_command_basic():
    # Test implementation
    pass
```

### Adding New API Endpoint

**1. Create Endpoint**:

```python
# backend/app/routes/new_endpoint.py
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

class NewRequest(BaseModel):
    param1: str
    param2: int

class NewResponse(BaseModel):
    result: str

@router.post("/new-endpoint", response_model=NewResponse)
async def new_endpoint(request: NewRequest):
    # Implementation
    return NewResponse(result=f"Processed {request.param1}")
```

**2. Register Router**:

```python
# backend/app/main.py
from .routes.new_endpoint import router as new_router

app.include_router(new_router, prefix="/v1")
```

**3. Test Endpoint**:

```cmd
curl -X POST http://localhost:8787/v1/new-endpoint \
  -H "Content-Type: application/json" \
  -d '{"param1": "test", "param2": 42}'
```

### Database Migrations

**SQLite Cache Management**:

```cmd
# Clear cache database
del data\.cache\keepa.db

# View cache contents
python -c "
import sqlite3
conn = sqlite3.connect('data/.cache/keepa.db')
cursor = conn.cursor()
cursor.execute('SELECT name FROM sqlite_master WHERE type=\"table\"')
print('Tables:', cursor.fetchall())
"
```

### Adding New Tests

**Unit Test Template**:

```python
# backend/tests/test_new_feature.py
import pytest
from lotgenius.new_module import new_function

def test_new_function_basic():
    """Test basic functionality"""
    result = new_function(input_data="test")
    assert result == expected_output

def test_new_function_edge_case():
    """Test edge cases"""
    with pytest.raises(ValueError):
        new_function(input_data=None)

@pytest.mark.integration
def test_new_function_integration():
    """Integration test requiring external dependencies"""
    # Requires API key or other setup
    pass
```

**Running New Tests**:

```cmd
# Run only new tests
python -m pytest backend\tests\test_new_feature.py -v

# Run with coverage
python -m pytest backend\tests\test_new_feature.py --cov=lotgenius.new_module
```

## Debugging & Troubleshooting

### Common Issues

#### ModuleNotFoundError

**Error**: `ModuleNotFoundError: No module named 'lotgenius'`

**Solution**:

```cmd
# Ensure backend package is installed in editable mode
pip install -e backend

# Verify installation
python -c "import lotgenius; print('OK')"
```

#### API Key Issues

**Error**: `KEEPA_API_KEY environment variable not set`

**Solution**:

```cmd
# Check environment variable
echo %KEEPA_API_KEY%

# Set temporarily
set KEEPA_API_KEY=your_key_here

# Add to .env file for persistence
echo KEEPA_API_KEY=your_key_here >> .env
```

#### Path Issues on Windows

**Error**: `FileNotFoundError` or path-related errors

**Solutions**:

```cmd
# Use forward slashes or double backslashes
python -m backend.cli.command "data/file.csv"
python -m backend.cli.command "data\\file.csv"

# Use raw strings in Python
python -c "r'C:\Users\path\file.csv'"
```

#### Port Already in Use

**Error**: `[Errno 10048] Only one usage of each socket address is normally permitted`

**Solutions**:

```cmd
# Find process using port 8787
netstat -ano | findstr :8787

# Kill process by PID
taskkill /PID <PID> /F

# Use different port
uvicorn backend.app.main:app --port 8788 --reload
```

### Debugging Tools

#### Python Debugging

**Built-in Debugger**:

```python
# Insert breakpoint in code
import pdb; pdb.set_trace()

# Modern Python 3.7+
breakpoint()
```

**VS Code Debugging**:

```json
// .vscode/launch.json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: CLI Command",
      "type": "python",
      "request": "launch",
      "module": "backend.cli.command_name",
      "args": ["data/test.csv", "--output", "results.json"],
      "console": "integratedTerminal"
    }
  ]
}
```

#### API Debugging

**Request Logging**:

```python
# Add to API endpoints for debugging
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@router.post("/endpoint")
async def endpoint(request: RequestModel):
    logger.debug(f"Received request: {request}")
    # ... implementation
```

**cURL Testing**:

```cmd
# Debug API calls with verbose output
curl -v -X POST http://localhost:8787/v1/endpoint \
  -H "Content-Type: application/json" \
  -d '{"param": "value"}'
```

## Performance Tips

### Development Speed

**Fast Test Cycles**:

```cmd
# Use targeted tests instead of full suite
python -m pytest backend\tests\test_specific.py::test_function -v

# Skip slow integration tests during development
python -m pytest -m "not integration"
```

**Cache Management**:

```cmd
# Use cache for repeated API calls
# Cache is automatically used with 7-day TTL

# Clear cache when testing new API behavior
del data\.cache\keepa.db
```

### Hot Reload Optimization

**Backend**: Use `--reload` flag with uvicorn for auto-restart on code changes

**Frontend**: Next.js dev server provides instant hot reload for most changes

**Configuration Changes**: Require server restart (environment variables, etc.)

## Code Quality

### Pre-commit Hooks

**Automatic Formatting**:

- **Black**: Python code formatting
- **isort**: Import organization
- **flake8**: Style checking
- **mypy**: Type checking

**Manual Run**:

```cmd
# Run hooks on all files
pre-commit run --all-files

# Run specific hook
pre-commit run black --all-files
```

### Type Safety

**Python**:

```python
# Use type hints
def process_data(items: list[dict]) -> dict[str, float]:
    return {"result": 42.0}
```

**TypeScript**:

```typescript
// Strict mode enabled in tsconfig.json
interface ComponentProps {
  value: number;
  onChange: (value: number) => void;
}
```

### Documentation

**Code Comments**:

```python
def complex_function(data: list[dict]) -> float:
    """
    Compute complex metric from data.

    Args:
        data: List of item dictionaries with price/quantity

    Returns:
        Computed metric value

    Raises:
        ValueError: If data is empty or invalid
    """
    pass
```

**API Documentation**: FastAPI automatically generates OpenAPI docs at `/docs`

---

**Next**: [Lot Optimization Runbook](optimize-lot.md) for end-to-end optimization procedures
