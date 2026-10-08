import httpx
from pathlib import Path

# Загружаем ключ
env_path = Path(".env")
api_key = None
if env_path.exists():
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("STAYING_KEY="):
            api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
            break

if not api_key:
    print("STAYING_KEY не найден в .env")
    exit(1)

print(f"STAYING_KEY: {api_key[:15]}...")
print()

CITIES = ["Split,HR", "London,GB", "New York,US", "Moscow,RU"]

url = "https://api.stayingapi.com/v1/search"

for city in CITIES:
    print(f"=== {city} ===")
    params = {
        "location": city,
        "checkIn": "2026-10-20",
        "checkOut": "2026-10-22",
        "adults": 2,
        "platforms": "airbnb,booking",
    }

    # Пробуем разные варианты заголовков
    for header_name, header_value in [
        ("x-api-key", {"x-api-key": api_key}),
        ("Authorization Bearer", {"Authorization": f"Bearer {api_key}"}),
    ]:
        try:
            resp = httpx.get(url, params=params, headers=header_value, timeout=30.0)
            print(f"  [{header_name}] HTTP {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                hotels = data.get("data", [])
                print(f"    Отелей: {len(hotels)}")
                for h in hotels[:2]:
                    print(f"      - {h.get('name')} | ${h.get('price')} | {h.get('platform')}")
                break
            else:
                err = resp.json().get("error", {})
                print(f"    Ошибка: {err.get('code')} — {err.get('message', '')[:80]}")
        except Exception as e:
            print(f"  [{header_name}] Exception: {e}")

    print()