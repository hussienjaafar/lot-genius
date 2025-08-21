import tempfile
from pathlib import Path

import pytest
from fastapi import HTTPException

# Import the guard directly; tests set pythonpath to include 'backend'
from backend.app.main import _validate_path


def test_guard_allows_system_temp():
    tmp = Path(tempfile.gettempdir()) / "lg_ok.csv"
    tmp.write_text("sku_local\nA\n", encoding="utf-8")
    p = _validate_path(str(tmp))
    assert p.exists()
    # Resolved under tempdir
    assert str(p).startswith(str(Path(tempfile.gettempdir()).resolve()))


def test_guard_blocks_windows_drive_on_posix():
    # Should be blocked even on non-Windows systems
    with pytest.raises(HTTPException) as ei:
        _validate_path(r"C:\Windows\system32\config\sam")
    assert ei.value.status_code == 400


def test_guard_blocks_unc():
    with pytest.raises(HTTPException) as ei:
        _validate_path(r"\\server\share\secret.csv")
    assert ei.value.status_code == 400


@pytest.mark.parametrize("bad", ["/etc/passwd", "/root/.ssh/id_rsa", "/dev/null"])
def test_guard_blocks_sensitive_prefixes(bad):
    # On Windows runners, these may not exist; still must raise 400 for safety.
    with pytest.raises(HTTPException) as ei:
        _validate_path(bad)
    assert ei.value.status_code == 400


def test_guard_blocks_outside_allowed_roots():
    # Test with a path that's definitely outside allowed roots
    # Use an absolute path that's not in temp or repo
    with pytest.raises(HTTPException) as ei:
        _validate_path("/some/completely/outside/path.csv")
    assert ei.value.status_code == 400
