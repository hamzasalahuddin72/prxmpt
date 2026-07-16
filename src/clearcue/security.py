from __future__ import annotations


SERVICE_NAME = "ClearCue Coach"


class SecretStoreError(RuntimeError):
    pass


def get_openai_key() -> str:
    try:
        import keyring

        return keyring.get_password(SERVICE_NAME, "openai_api_key") or ""
    except Exception as exc:  # platform keyring failures vary
        raise SecretStoreError(f"Windows Credential Manager could not be read: {exc}") from exc


def set_openai_key(value: str) -> None:
    try:
        import keyring

        if value.strip():
            keyring.set_password(SERVICE_NAME, "openai_api_key", value.strip())
        else:
            try:
                keyring.delete_password(SERVICE_NAME, "openai_api_key")
            except keyring.errors.PasswordDeleteError:
                pass
    except Exception as exc:
        raise SecretStoreError(f"Windows Credential Manager could not be updated: {exc}") from exc

