import os

import pytest


@pytest.fixture(autouse=True, scope="session")
def _clear_api_key_env():
    # Ensure tests don't inherit LOTGENIUS_API_KEY from CI/host
    os.environ.pop("LOTGENIUS_API_KEY", None)
