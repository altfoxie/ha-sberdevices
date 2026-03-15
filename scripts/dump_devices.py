#!/usr/bin/env python3
"""
v3: Использует русский root CA для SSL + фикс парсинга.
Запуск: sudo -u homeassistant /opt/homeassistant/venv/bin/python3 /tmp/dump_devices_v3.py
"""
import json
import asyncio
import ssl
import sys
from pathlib import Path

CONFIG_PATH = Path("/opt/homeassistant/.homeassistant/.storage/core.config_entries")
# Русский корневой CA — уже есть в компоненте
RU_CA_PATH = Path("/opt/homeassistant/.homeassistant/custom_components/sberdevices/russian_trusted_root_ca.pem")

def get_sber_token():
    data = json.loads(CONFIG_PATH.read_text())
    for entry in data["data"]["entries"]:
        if entry["domain"] == "sberdevices":
            return entry["data"].get("token")
    print("ОШИБКА: sberdevices не найден")
    sys.exit(1)

def make_ssl_ctx():
    """SSL контекст с русским CA."""
    ctx = ssl.create_default_context()
    if RU_CA_PATH.exists():
        ctx.load_verify_locations(cafile=str(RU_CA_PATH))
        print(f"Загружен русский CA: {RU_CA_PATH}")
    else:
        print(f"ВНИМАНИЕ: {RU_CA_PATH} не найден, используем системный")
    return ctx

async def main():
    sys.path.insert(0, "/opt/homeassistant/.homeassistant")

    from custom_components.sberdevices.api import SberAPI, HomeAPI
    from httpx import AsyncClient

    token = get_sber_token()
    print(f"OAuth token: {token['access_token'][:30]}...")

    sber = SberAPI(token=token)
    home = HomeAPI(sber)
    ssl_ctx = make_ssl_ctx()

    # 1. IoT Gateway tree
    print("\n=== 1. IoT Gateway: /device_groups/tree ===")
    try:
        tree = await home.get_device_tree()
        count = 0
        def count_dev(d):
            nonlocal count
            count += len(d.get("devices", []))
            for c in d.get("children", []): count_dev(c)
        count_dev(tree)
        print(f"IoT устройств: {count}")
    except Exception as e:
        print(f"Ошибка: {e}")

    # 2. IoT Gateway: /devices
    print("\n=== 2. IoT Gateway: /devices ===")
    try:
        res = await home.request("GET", "/devices")
        out = json.dumps(res, indent=2, ensure_ascii=False)
        Path("/tmp/sber_iot_devices.json").write_text(out)
        print(f"Ответ сохранён: /tmp/sber_iot_devices.json")
        print(out[:2000])
    except Exception as e:
        print(f"Ошибка: {e}")

    # 3. Companion API с русским CA
    print("\n=== 3. Companion API (с русским CA) ===")
    try:
        home_token = await sber.fetch_home_token()
        print(f"Home token: {home_token[:30]}...")

        headers = {"X-AUTH-jwt": home_token}

        async with AsyncClient(verify=ssl_ctx) as client:
            for path in [
                "/v13/smarthome/devices",
                "/v13/smarthome/user/devices",
                "/v13/devices",
                "/v13/smarthome/device_groups/tree",
            ]:
                url = f"https://companion.devices.sberbank.ru{path}"
                try:
                    r = await client.get(url, headers=headers)
                    print(f"\n  GET {path} → {r.status_code}")
                    if r.status_code == 200:
                        data = r.json()
                        fname = path.replace("/", "_").strip("_")
                        Path(f"/tmp/sber_companion{fname}.json").write_text(
                            json.dumps(data, indent=2, ensure_ascii=False)
                        )
                        print(json.dumps(data, indent=2, ensure_ascii=False)[:3000])
                    else:
                        print(f"  Body: {r.text[:300]}")
                except Exception as e:
                    print(f"  {path}: {e}")

        # Также с Authorization: Bearer
        print("\n=== 4. Companion API (Authorization: Bearer) ===")
        headers2 = {"Authorization": f"Bearer {token['access_token']}"}
        async with AsyncClient(verify=ssl_ctx) as client:
            for path in [
                "/v13/smarthome/token",
                "/v13/smarthome/devices",
            ]:
                url = f"https://companion.devices.sberbank.ru{path}"
                try:
                    r = await client.get(url, headers=headers2)
                    print(f"\n  GET {path} → {r.status_code}")
                    print(f"  Body: {r.text[:500]}")
                except Exception as e:
                    print(f"  {path}: {e}")

    except Exception as e:
        print(f"Ошибка: {e}")

    print("\n✅ Готово")

asyncio.run(main())
