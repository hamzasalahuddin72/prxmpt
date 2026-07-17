from __future__ import annotations


SERVICE_NAME = "prxmpt Coach"
LEGACY_SERVICE_NAME = "ClearCue Coach"


class SecretStoreError(RuntimeError):
    pass


def _get_secret(username: str) -> str:
    try:
        import keyring

        current = keyring.get_password(SERVICE_NAME, username) or ""
        if current:
            return current
        legacy = keyring.get_password(LEGACY_SERVICE_NAME, username) or ""
        if legacy:
            keyring.set_password(SERVICE_NAME, username, legacy)
        return legacy
    except Exception as exc:  # platform keyring failures vary
        raise SecretStoreError(f"Windows Credential Manager could not be read: {exc}") from exc


def _set_secret(username: str, value: str) -> None:
    try:
        import keyring

        if value.strip():
            keyring.set_password(SERVICE_NAME, username, value.strip())
        else:
            try:
                keyring.delete_password(SERVICE_NAME, username)
            except keyring.errors.PasswordDeleteError:
                pass
    except Exception as exc:
        raise SecretStoreError(f"Windows Credential Manager could not be updated: {exc}") from exc


def get_openai_key() -> str:
    return _get_secret("openai_api_key")


def set_openai_key(value: str) -> None:
    _set_secret("openai_api_key", value)


def get_gemini_key() -> str:
    return _get_secret("gemini_api_key")


def set_gemini_key(value: str) -> None:
    _set_secret("gemini_api_key", value)
