import asyncio
import os
from services.external_adapters.search_flights_adapter import SearchFlightsAdapter


async def test():
    a = SearchFlightsAdapter()
    print(f"AIRLABS_KEY: {'OK' if a.api_key else 'ОТСУТСТВУЕТ'}")
    print()

    # 1. Поиск через /routes
    print("=== /routes: Moscow -> Sochi ===")
    flights = await a.search_flights("Moscow", "Sochi")
    print(f"Найдено: {len(flights)}")
    for f in flights[:5]:
        print(f"  {f['flight_iata']}  {f['dep_iata']}->{f['arr_iata']}")

    # 2. Проверка /flight для первого рейса
    if flights:
        test_flight = flights[0]["flight_iata"]
        print(f"\n=== /flight для {test_flight} ===")
        data = await a.get_flight_by_iata(test_flight)
        print(f"Результат: {data}")
    else:
        print("\nРейсы не найдены — /flight проверять нечего")


if __name__ == "__main__":
    asyncio.run(test())
