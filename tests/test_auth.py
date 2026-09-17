import pytest

from app.auth import AccountError, PasswordHasher


def test_password_hash_round_trip():
    encoded = PasswordHasher.hash("correct horse battery")

    assert encoded.startswith("pbkdf2_sha256$")
    assert PasswordHasher.verify("correct horse battery", encoded) is True
    assert PasswordHasher.verify("wrong password", encoded) is False


def test_short_password_is_rejected():
    with pytest.raises(AccountError):
        PasswordHasher.hash("short")
