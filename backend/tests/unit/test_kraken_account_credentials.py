"""Unit tests for Kraken private credential loading."""

from __future__ import annotations

import pytest

from app.account.credentials import load_kraken_credentials
from app.account.errors import CREDENTIALS_MISSING, AccountPrivateError


def test_missing_both_credentials() -> None:
    with pytest.raises(AccountPrivateError) as exc_info:
        load_kraken_credentials(environ={})
    assert exc_info.value.code == CREDENTIALS_MISSING


def test_blank_key_or_secret() -> None:
    with pytest.raises(AccountPrivateError) as exc_info:
        load_kraken_credentials(
            environ={"KRAKEN_API_KEY": "  ", "KRAKEN_API_SECRET": "secret"}
        )
    assert exc_info.value.code == CREDENTIALS_MISSING

    with pytest.raises(AccountPrivateError) as exc_info:
        load_kraken_credentials(
            environ={"KRAKEN_API_KEY": "key", "KRAKEN_API_SECRET": ""}
        )
    assert exc_info.value.code == CREDENTIALS_MISSING


def test_xt_env_is_not_kraken_credentials() -> None:
    with pytest.raises(AccountPrivateError) as exc_info:
        load_kraken_credentials(
            environ={"XT_API_KEY": "xt-key", "XT_API_SECRET": "xt-secret"}
        )
    assert exc_info.value.code == CREDENTIALS_MISSING


def test_load_success() -> None:
    creds = load_kraken_credentials(
        environ={"KRAKEN_API_KEY": "key", "KRAKEN_API_SECRET": "secret"}
    )
    assert creds.api_key == "key"
    assert creds.api_secret == "secret"
