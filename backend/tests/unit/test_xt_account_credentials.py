"""Unit tests for XT private credential loading."""

from __future__ import annotations

import pytest

from app.xt_account.credentials import load_credentials
from app.xt_account.errors import CREDENTIALS_MISSING, XtPrivateError


def test_missing_both_credentials() -> None:
    with pytest.raises(XtPrivateError) as exc_info:
        load_credentials(environ={})
    assert exc_info.value.code == CREDENTIALS_MISSING


def test_blank_key_or_secret() -> None:
    with pytest.raises(XtPrivateError) as exc_info:
        load_credentials(environ={"XT_API_KEY": "  ", "XT_API_SECRET": "secret"})
    assert exc_info.value.code == CREDENTIALS_MISSING

    with pytest.raises(XtPrivateError) as exc_info:
        load_credentials(environ={"XT_API_KEY": "key", "XT_API_SECRET": ""})
    assert exc_info.value.code == CREDENTIALS_MISSING


def test_load_success() -> None:
    creds = load_credentials(
        environ={"XT_API_KEY": "key", "XT_API_SECRET": "secret"}
    )
    assert creds.api_key == "key"
    assert creds.api_secret == "secret"
