# Acceptance Criteria - Step 1

## Step 1 passes if

1. **Files exist with content committed:**
   - `/README.md` - Project overview with configurable investment gate
   - `/docs/PRD.md` - Full Product Requirements Document
   - `/docs/ARCH.md` - Architecture notes and data flows
   - `/docs/GLOSSARY.md` - Key terms and definitions
   - `/docs/ACCEPTANCE.md` - This file
   - `/infra/.env.example` - Environment template with decision policy
   - `/infra/Makefile` - Common development tasks
   - `/.gitignore` - Git ignore patterns
   - `/.editorconfig` - Editor configuration
   - `/.pre-commit-config.yaml` - Pre-commit hooks
   - `/infra/ci/github-actions.yml` - CI/CD configuration

2. **Documentation quality:**
   - PRD and ARCH render without lint errors
   - All markdown files properly formatted

3. **Configuration:**
   - Pre-commit hooks install and run successfully
   - `.env.example` contains `MIN_ROI_TARGET` and `SELLTHROUGH_HORIZON_DAYS`
   - README documents the investment gate as configurable (not hard-coded)

4. **CI/CD:**
   - GitHub Actions workflow configured
   - Pre-commit checks run in CI

## Validation Steps

```bash
# Install pre-commit
pip install pre-commit
pre-commit install

# Run hooks locally
pre-commit run --all-files

# Verify structure
tree -L 2

# Check environment template
cat infra/.env.example | grep MIN_ROI_TARGET
cat infra/.env.example | grep SELLTHROUGH_HORIZON_DAYS
```

## Success Criteria

- [ ] All files created as specified
- [ ] Pre-commit hooks pass
- [ ] Environment variables documented
- [ ] CI pipeline configured
- [ ] Investment gate clearly marked as configurable
- [ ] No hard-coded ROI targets or horizons

## Next Step

Once Step 1 is complete and accepted, proceed to:
**Step 2 - Canonical schema & header mapping (Keepa-first; ROI gate read from env)**
