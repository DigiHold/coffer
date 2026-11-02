import pytest

from coffer import create_app


@pytest.mark.parametrize("name", ["DATABASE_URL", "JWT_SECRET"])
def test_refuses_to_start_without_a_required_setting(
    monkeypatch: pytest.MonkeyPatch, name: str
) -> None:
    monkeypatch.delenv(name)

    with pytest.raises(RuntimeError, match=f"{name} is not set"):
        create_app()


def test_refuses_a_signing_key_shorter_than_32_bytes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("JWT_SECRET", "k" * 31)

    with pytest.raises(RuntimeError, match="at least 32 bytes"):
        create_app()


def test_accepts_a_signing_key_of_32_bytes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JWT_SECRET", "k" * 32)

    assert create_app().config["JWT_SECRET"] == "k" * 32
