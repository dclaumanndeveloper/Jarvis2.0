import asyncio
import aiohttp
import sys

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

async def main():
    try:
        async with aiohttp.ClientSession() as session:
            payload = {
                "model": "llama3",
                "prompt": "Say hello",
                "stream": False
            }
            async with session.post("http://localhost:11434/api/generate", json=payload, timeout=30) as response:
                print(f"Status: {response.status}")
                print(f"Text: {await response.text()}")
    except Exception as e:
        import traceback
        print(f"Exception: {e}")
        traceback.print_exc()

asyncio.run(main())
