# Release Runbook

This runbook provides a step-by-step checklist for creating and publishing releases of the Lot Genius platform.

## Pre-Release Checklist

### 1. Code Quality Verification

- [ ] All CI quality gates pass locally:
  ```bash
  make quality-check  # or individual commands
  python -m py_compile -b backend/
  ./scripts/check-ellipses.sh
  python scripts/check_ascii.py docs/
  ```
- [ ] All tests pass:
  ```bash
  cd backend && python -m pytest -q
  cd frontend && npm test
  ```
- [ ] No known security vulnerabilities

### 2. Version Management

- [ ] Update version in `backend/lotgenius/__init__.py`
  ```python
  __version__ = "X.Y.Z"  # Follow semver
  ```
- [ ] Update version in `frontend/package.json` to match
- [ ] Version follows semantic versioning (semver) guidelines
- [ ] Breaking changes documented in release notes

### 3. Documentation Updates

- [ ] All docs are ASCII-compliant (validated by check_ascii.py)
- [ ] README files updated with new features
- [ ] API documentation reflects any backend changes
- [ ] Operation runbooks updated if needed

## Release Process

### 1. Create Release Tag

```bash
# Ensure you're on main branch with latest changes
git checkout main
git pull origin main

# Create annotated tag (triggers release workflow)
git tag -a v1.2.3 -m "Release v1.2.3"
git push origin v1.2.3
```

### 2. Monitor GitHub Actions

- [ ] Go to https://github.com/your-org/lot-genius/actions
- [ ] Verify "Release" workflow started automatically
- [ ] Monitor build logs for any failures
- [ ] Ensure all artifacts build successfully:
  - Backend wheel (.whl) and source distribution (.tar.gz)
  - Frontend production build (frontend-build.zip)
  - Documentation bundle (docs-bundle.zip)

### 3. Verify Release Artifacts

Once the workflow completes:

- [ ] Check GitHub Release was created at: https://github.com/your-org/lot-genius/releases
- [ ] Download and verify artifacts:

  ```bash
  # Test backend package
  pip install lotgenius-X.Y.Z-py3-none-any.whl
  python -c "import lotgenius; print(lotgenius.__version__)"

  # Test frontend bundle
  unzip frontend-build.zip
  # Deploy to test environment and verify functionality

  # Test docs bundle
  unzip docs-bundle.zip
  python scripts/check_ascii.py docs/
  ```

### 4. Release Notes Validation

- [ ] Generated release notes are accurate and complete
- [ ] All Gap Fix implementations are categorized correctly
- [ ] Release artifacts section matches actual uploads
- [ ] ASCII compliance verified (no Unicode rendering issues)

## Post-Release Tasks

### 1. Deployment

- [ ] Deploy backend package to production environment
- [ ] Deploy frontend build to hosting platform
- [ ] Update production configuration if needed
- [ ] Verify production deployment functionality

### 2. Communication

- [ ] Announce release to team/stakeholders
- [ ] Update project documentation with new version
- [ ] Close related issues/tickets in tracking system

### 3. Monitoring

- [ ] Monitor production logs for any release-related issues
- [ ] Verify new features work as expected in production
- [ ] Track performance metrics post-release

## Rollback Procedure

If critical issues are discovered post-release:

### 1. Immediate Actions

- [ ] Assess severity and impact of issues
- [ ] Decide on rollback vs hotfix approach
- [ ] Communicate status to team

### 2. Rollback Steps (if necessary)

```bash
# Revert to previous release tag
git checkout v1.2.2  # previous stable version
git tag -a v1.2.4 -m "Rollback to v1.2.2 due to critical issues"
git push origin v1.2.4
```

- [ ] Deploy previous stable version to production
- [ ] Update release notes with rollback information
- [ ] Plan hotfix release with issue resolution

## Troubleshooting

### Common Issues

- **Unicode errors in release notes**: Run `python scripts/check_ascii.py multi_agent/runlogs/` to identify problematic files
- **Build failures**: Check artifact generation locally first:
  ```bash
  cd backend && python -m build
  cd frontend && npm run build && zip -r build.zip .next/ public/
  ```
- **Test failures**: Ensure all environment variables and dependencies are properly configured

### Emergency Contacts

- Release Engineering: [contact info]
- Platform Team Lead: [contact info]
- Security Team: [contact info]

## Version History

- v0.1.0: Initial release with basic functionality
- [Future versions will be documented here]

---

Generated: $(date)
Maintainer: Lot Genius Release Engineering
