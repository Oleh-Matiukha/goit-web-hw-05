import sys
import asyncio
import aiohttp
import json
from aiopath import AsyncPath
from datetime import datetime, timedelta
import websockets


class HttpError(Exception):
    pass


class PrivatBankAPI:
    BASE_URL = "https://api.privatbank.ua/p24api/exchange_rates?date={}"

    @staticmethod
    async def fetch_exchange_rates(date: str):
        url = PrivatBankAPI.BASE_URL.format(date)
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        raise HttpError(f"Error status: {response.status} for {url}")
            except aiohttp.ClientError as e:
                raise HttpError(f"Network error: {e}")


class CurrencyService:
    DEFAULT_CURRENCIES = {"EUR", "USD"}

    @staticmethod
    async def get_currency_rates(days: int, currencies: set):
        if not (1 <= days <= 10):
            raise ValueError("Number of days must be between 1 and 10")

        results = []
        for i in range(days):
            date = (datetime.now() - timedelta(days=i)).strftime("%d.%m.%Y")
            try:
                data = await PrivatBankAPI.fetch_exchange_rates(date)
                rates = {}
                for curr in data.get("exchangeRate", []):
                    if curr.get("currency") in currencies:
                        rates[curr["currency"]] = {
                            "sale": curr.get("saleRate", curr.get("saleRateNB")),
                            "purchase": curr.get("purchaseRate", curr.get("purchaseRateNB"))
                        }
                results.append({date: rates})
            except HttpError as e:
                print(f"Error fetching data for {date}: {e}")
                results.append({date: "Error fetching data"})

        return results


async def log_exchange_command(command: str):
    log_file = AsyncPath("exchange_log.txt")
    async with log_file.open(mode="a") as f:
        await f.write(f"[{datetime.now()}] {command}\n")


async def handle_client(websocket):
    async for message in websocket:
        if message.startswith("exchange"):
            parts = message.split()
            days = 1 if len(parts) == 1 else int(parts[1])
            days = min(max(days, 1), 10)
            rates = await CurrencyService.get_currency_rates(days, CurrencyService.DEFAULT_CURRENCIES)
            await websocket.send(json.dumps(rates, indent=2, ensure_ascii=False))
            await log_exchange_command(message)
        else:
            await websocket.send("Unknown command")


async def websocket_server():
    print("WebSocket server is running on ws://localhost:8080")
    async with websockets.serve(handle_client, "localhost", 8080):
        while True:
            await asyncio.sleep(1)  # Запобігає завершенню сервера


async def main():
    if len(sys.argv) < 2:
        print("Usage: python main.py <days> [currencies]")
        return

    try:
        days = int(sys.argv[1])
        currencies = set(sys.argv[2:]) if len(sys.argv) > 2 else CurrencyService.DEFAULT_CURRENCIES
        rates = await CurrencyService.get_currency_rates(days, currencies)
        print(json.dumps(rates, indent=2, ensure_ascii=False))
    except ValueError as e:
        print(f"Invalid input: {e}")


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(websocket_server())
    if len(sys.argv) > 1:
        loop.run_until_complete(main())

    loop.run_forever()
