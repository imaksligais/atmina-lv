import getpass
import sys

import keyring

SERVICE_NAME = "politracker"

KNOWN_KEYS = [
    "x_username",
    "x_email",
    "x_password",
    "dashboard_password",
    "session_secret",
    "youtube_api_key",
    "facebook_page_token",
    "anthropic_api_key",
    "watchdog_smtp_host",
    "watchdog_smtp_user",
    "watchdog_smtp_pass",
    "watchdog_alert_to",
    "backup_target_path",
    # social_agent
    "telegram_bot_token",
    "telegram_operator_chat_id",
    "x_atmina_cookies_path",
]


def get_credential(name: str) -> str | None:
    return keyring.get_password(SERVICE_NAME, name)


def set_credential(name: str, value: str) -> None:
    keyring.set_password(SERVICE_NAME, name, value)


def verify_all() -> dict[str, bool]:
    return {key: get_credential(key) is not None for key in KNOWN_KEYS}


def main():
    if len(sys.argv) < 2:
        print("Usage: python -m src.credentials <set|check> [key_name]")
        sys.exit(1)

    command = sys.argv[1]

    if command == "check":
        results = verify_all()
        for key, exists in results.items():
            status = "SET" if exists else "NOT SET"
            print(f"  {key}: {status}")
    elif command == "set":
        if len(sys.argv) < 3:
            print("Usage: python -m src.credentials set <key_name>")
            sys.exit(1)
        key_name = sys.argv[2]
        value = getpass.getpass(f"Enter value for {key_name}: ")
        set_credential(key_name, value)
        print(f"Stored {key_name} in keyring.")
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
