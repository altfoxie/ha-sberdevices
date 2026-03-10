"""
Script to obtain SBER_ACCESS_TOKEN via OAuth2 flow.

Run:
    python scripts/get_token.py
"""

import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from custom_components.sberdevices.api import SberAPI


async def main():
    sber = SberAPI()

    url = sber.create_authorization_url()
    print("1. Откройте эту ссылку в браузере и авторизуйтесь в Сбербанк Онлайн:\n")
    print(url)
    print("\n2. После авторизации браузер перенаправит на URL вида:")
    print("   companionapp://host?code=...&state=...\n")
    print("3. Скопируйте ПОЛНЫЙ URL редиректа и вставьте сюда:\n")

    redirect_url = input("URL: ").strip()

    success = await sber.authorize_by_url(redirect_url)

    if not success:
        print("\nОшибка авторизации. Проверьте URL.")
        return

    token = sber.token

    env_lines = [
        f"SBER_ACCESS_TOKEN={token['access_token']}",
        f"SBER_REFRESH_TOKEN={token.get('refresh_token', '')}",
        f"SBER_TOKEN_TYPE={token.get('token_type', 'Bearer')}",
        f"SBER_EXPIRES_AT={int(token.get('expires_at', 0))}",
    ]

    env_path = os.path.join(os.path.dirname(__file__), "..", ".env.local")
    with open(env_path, "w") as f:
        f.write("\n".join(env_lines) + "\n")

    print("\nУспешно! Токен сохранён в .env.local\n")
    for line in env_lines:
        print(f"  {line}")
    print(f"\nПолный токен (JSON):\n{json.dumps(token, indent=2)}")


if __name__ == "__main__":
    asyncio.run(main())
