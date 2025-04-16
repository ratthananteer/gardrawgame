import asyncio
import websockets

async def test():
    try:
        async with websockets.connect("ws://localhost:8000/ws/test") as ws:
            await ws.send("Hello")
            print(await ws.recv())
    except Exception as e:
        print("Error:", e)

asyncio.run(test())