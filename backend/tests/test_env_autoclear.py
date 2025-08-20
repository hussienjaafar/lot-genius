import os


def test_env_key_cleared_session():
    assert "LOTGENIUS_API_KEY" not in os.environ
