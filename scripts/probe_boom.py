#!/usr/bin/env python3
"""
Зонд WebSocket на SberBoom (порт 20000).
Пробует подключиться и узнать что колонка отвечает.

Запуск на козанауте:
  pip3 install websockets
  python3 /tmp/probe_boom.py
"""
import asyncio
import ssl
import json
import sys

BOOM_IP = "192.168.1.132"
BOOM_PORT = 20000
BOOM_URL = f"wss://{BOOM_IP}:{BOOM_PORT}"

async def probe():
    try:
        import websockets
    except ImportError:
        print("Установи: pip3 install websockets")
        sys.exit(1)

    # Отключаем проверку SSL (self-signed cert)
    ssl_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE

    print(f"Подключаюсь к {BOOM_URL}...")

    try:
        async with websockets.connect(
            BOOM_URL,
            ssl=ssl_ctx,
            open_timeout=10,
            close_timeout=5,
        ) as ws:
            print(f"✅ Подключено! Протокол: {ws.subprotocol}")
            print(f"   Headers: {dict(ws.response_headers)}")

            # Пробуем получить сообщение (если колонка шлёт что-то сама)
            print("\nЖду сообщение от колонки (5 сек)...")
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=5)
                print(f"📨 Получено: {msg[:500]}")
            except asyncio.TimeoutError:
                print("   (тишина — колонка сама не шлёт)")

            # Пробуем послать разные запросы
            test_messages = [
                # JSON-RPC стиль
                json.dumps({"jsonrpc": "2.0", "method": "getState", "id": 1}),
                json.dumps({"type": "ping"}),
                json.dumps({"command": "get_device_info"}),
                json.dumps({"action": "status"}),
                # gRPC-web style
                "ping",
            ]

            for msg_out in test_messages:
                print(f"\n📤 Отправляю: {msg_out[:80]}")
                try:
                    await ws.send(msg_out)
                    reply = await asyncio.wait_for(ws.recv(), timeout=3)
                    print(f"📨 Ответ: {reply[:500]}")
                except asyncio.TimeoutError:
                    print("   (нет ответа)")
                except Exception as e:
                    print(f"   Ошибка: {e}")

    except ConnectionRefusedError:
        print("❌ Соединение отклонено")
    except Exception as e:
        print(f"❌ Ошибка: {type(e).__name__}: {e}")

    # Также попробуем openssl для инфо о сертификате
    print("\n=== SSL Cert Info ===")
    import subprocess
    try:
        result = subprocess.run(
            ["openssl", "s_client", "-connect", f"{BOOM_IP}:{BOOM_PORT}", "-showcerts"],
            input=b"",
            capture_output=True,
            timeout=5,
        )
        output = result.stdout.decode(errors="replace")
        # Показать subject и issuer
        for line in output.split("\n"):
            if any(k in line.lower() for k in ["subject", "issuer", "cn=", "serial"]):
                print(f"  {line.strip()}")
    except Exception as e:
        print(f"  openssl: {e}")

asyncio.run(probe())
