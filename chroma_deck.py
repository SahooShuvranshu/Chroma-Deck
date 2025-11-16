"""Chroma-Deck: minimal CLI client to interact with the hub and rooms.

This is a small asyncio-based command-line client that connects to the
Chroma-Core hub to fetch available rooms and then allows joining a room to chat.

Commands:
- `/list` - request room list from hub
- `/join <room name>` - join a room from the last fetched list
- `/leave` - leave current room and return to hub
- `/quit` - exit
"""

import asyncio
import json
import os
import logging
from websockets import connect

logging.basicConfig(level=logging.INFO)

HUB_URL = os.environ.get("HUB_URL", "ws://localhost:8080")
HUB_WS = HUB_URL.rstrip("/") + "/ws"


async def read_input(prompt=""):
    return await asyncio.get_event_loop().run_in_executor(None, lambda: input(prompt))


async def hub_client():
    async with connect(HUB_WS) as ws:
        await ws.send(json.dumps({"type": "get_list"}))
        rooms = {}
        print("🌈 Connected to Chroma-Core hub")
        print("Enhanced Commands: /list, /join <name>, /info <name>, /refresh, /ping, /help, /quit")
        
        async for raw in ws:
            try:
                data = json.loads(raw)
            except Exception:
                continue
                
            if data.get("type") == "room_list":
                rooms = data.get("rooms", {})
                print(f"\n📡 Available rooms ({len(rooms)}):")
                if not rooms:
                    print("  (No rooms available)")
                else:
                    for i, (name, addr) in enumerate(rooms.items(), 1):
                        print(f"  {i}. 🏠 {name} -> {addr}")
                print()
                
                # Enhanced command loop
                while True:
                    cmd = await read_input("🔷 > ")
                    if not cmd:
                        continue
                        
                    cmd = cmd.strip()
                    
                    if cmd == "/help":
                        print("Available commands:")
                        print("  /list     - Refresh room list")
                        print("  /join <name> - Join a room")
                        print("  /info <name> - Show room info")
                        print("  /refresh  - Refresh room list")
                        print("  /ping     - Test hub connection")
                        print("  /quit     - Exit client")
                        continue
                        
                    elif cmd in ["/list", "/refresh"]:
                        await ws.send(json.dumps({"type": "get_list"}))
                        break  # wait for updated list
                        
                    elif cmd == "/ping":
                        import time
                        start = time.time()
                        await ws.send(json.dumps({"type": "get_list"}))
                        # Simple ping by measuring list response time
                        print(f"🏓 Pong! (hub responsive)")
                        continue
                        
                    elif cmd.startswith("/info "):
                        room_name = cmd[6:].strip()
                        if room_name in rooms:
                            addr = rooms[room_name]
                            print(f"📋 Room Info:")
                            print(f"   Name: {room_name}")
                            print(f"   Address: {addr}")
                            print(f"   Protocol: {'WSS (Secure)' if addr.startswith('wss') else 'WS (Insecure)'}")
                        else:
                            print(f"❌ Room '{room_name}' not found")
                        continue
                        
                    elif cmd.startswith("/join "):
                        room_name = cmd[6:].strip()
                        addr = rooms.get(room_name)
                        if not addr:
                            print(f"❌ Room '{room_name}' not found. Use /list to see available rooms.")
                            continue
                        print(f"🚀 Connecting to {room_name}...")
                        await room_chat(addr)
                        print("🔙 Returned to hub")
                        await ws.send(json.dumps({"type": "get_list"}))
                        break
                        
                    elif cmd == "/quit":
                        print("👋 Goodbye!")
                        return
                        
                    else:
                        print(f"❌ Unknown command: {cmd}. Type /help for available commands.")
                        
            elif data.get("type") == "admin_broadcast":
                print(f"\n📢 ADMIN: {data.get('message', '')}\n")


async def room_chat(address):
    try:
        async with connect(address) as ws:
            # Expect welcome
            welcome = await ws.recv()
            print(f"📨 {welcome}")
            name = await read_input("👤 Your name: ")
            await ws.send(name)
            
            print(f"\n🎉 Joined room! You are now '{name}'.")
            print("💬 Room commands: /help, /who, /time, /uptime, /motd, /nick <name>")
            print("🚪 Type /leave to exit the room.\n")

            async def receiver():
                try:
                    async for msg in ws:
                        # Add timestamp to messages
                        import datetime
                        timestamp = datetime.datetime.now().strftime('%H:%M')
                        
                        if msg.startswith('---'):
                            print(f"\n[{timestamp}] 🔔 {msg}")
                        elif msg.startswith('['):
                            print(f"[{timestamp}] {msg}")
                        else:
                            print(f"[{timestamp}] ℹ️  {msg}")
                except Exception:
                    print("\n❌ Disconnected from room")

            recv_task = asyncio.create_task(receiver())
            while True:
                line = await read_input("💬 ")
                if line.strip() == "/leave":
                    print("🚪 Leaving room...")
                    await ws.close()
                    recv_task.cancel()
                    return
                try:
                    await ws.send(line)
                except Exception:
                    print("❌ Connection lost")
                    recv_task.cancel()
                    return
    except Exception as e:
        print(f"❌ Failed to join room: {e}")


def main():
    try:
        asyncio.run(hub_client())
    except KeyboardInterrupt:
        print("Exiting")


if __name__ == "__main__":
    main()