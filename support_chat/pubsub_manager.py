import asyncio
from .redis_client import redis_client


class PubSubManager:
    def __init__(self):
        self._subscribers: dict[str, set[asyncio.Queue]] = {}
        self._pubsub = None
        self._task = None
        self._lock = None

    def _get_lock(self):
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock

    async def subscribe(self, channel: str) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue()
        async with self._get_lock():
            if self._pubsub is None:
                self._pubsub = redis_client.pubsub()
                await self._pubsub.subscribe(channel)
                self._subscribers[channel] = set()
                self._subscribers[channel].add(queue)
                self._task = asyncio.ensure_future(self._listen())
                print(f"[PUBSUB] started, subscribed to {channel}")
                return queue

            if channel not in self._subscribers:
                self._subscribers[channel] = set()
                await self._pubsub.subscribe(channel)
                print(f"[PUBSUB] subscribed to {channel}")

            self._subscribers[channel].add(queue)
            print(f"[PUBSUB] queue added to {channel}, total: {len(self._subscribers[channel])}")
        return queue

    async def unsubscribe(self, channel: str, queue: asyncio.Queue):
        async with self._get_lock():
            if channel not in self._subscribers:
                return
            self._subscribers[channel].discard(queue)
            if not self._subscribers[channel]:
                del self._subscribers[channel]
                if self._pubsub:
                    await self._pubsub.unsubscribe(channel)
                    print(f"[PUBSUB] unsubscribed from {channel}")

    async def _listen(self):
        print("[PUBSUB] _listen started")
        try:
            async for message in self._pubsub.listen():
                print(f"[PUBSUB] raw message: {message}")
                if message["type"] == "message":
                    channel = message["channel"]
                    queues = list(self._subscribers.get(channel, []))
                    print(f"[PUBSUB] dispatching to {len(queues)} queues on {channel}")
                    for q in queues:
                        await q.put(message["data"])
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"[PUBSUB] _listen error: {e}")


pubsub_manager = PubSubManager()