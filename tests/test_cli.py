# Copyright (c) 2026 Ishanu Chakraborty. All rights reserved.
# Licensed under the MIT License. See LICENSE in the project root for license information.
#
# WARNING: THIS SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND.

import os
from unittest.mock import patch
import pytest


def test_cli_serve_help():
    # Verify serve help executes and prints options without crashing
    from google_workspace_mcp.cli import serve

    with (
        patch("sys.argv", ["gws-serve", "--help"]),
        pytest.raises(SystemExit) as excinfo,
        patch("sys.stdout"),
    ):
        serve()
    assert excinfo.value.code == 0


def test_cli_serve_overrides():
    from google_workspace_mcp.cli import serve

    # Set up arguments that override config settings
    test_args = [
        "gws-serve",
        "--profile",
        "testprofile",
        "--mode",
        "readonly",
        "--pii-mode",
        "redact",
        "--allowed-domains",
        "domain1.com,domain2.com",
    ]

    with (
        patch("sys.argv", test_args),
        patch("google_workspace_mcp.server.run") as mock_run,
        patch("sys.stderr"),
    ):
        serve()

        # Check environment variables were overridden correctly
        assert os.environ.get("GWS_PROFILE") == "testprofile"
        assert os.environ.get("GWS_MODE") == "readonly"
        assert os.environ.get("GWS_PII_MODE") == "redact"
        assert os.environ.get("GWS_ALLOWED_DOMAINS") == "domain1.com,domain2.com"
        assert mock_run.called


def test_cli_purge_token_only(tmp_path):
    from google_workspace_mcp.cli import purge

    # Mock configuration token path
    mock_token = tmp_path / "token_test.json"
    mock_token.write_text("{}", encoding="utf-8")

    with (
        patch("sys.argv", ["gws-purge", "--token-only"]),
        patch("google_workspace_mcp.config.TOKEN_PATH", mock_token),
        patch("google_workspace_mcp.config.APP_DIR", tmp_path),
    ):
        purge()
        assert not mock_token.exists()
