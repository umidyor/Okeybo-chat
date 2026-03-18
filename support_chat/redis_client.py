import redis.asyncio as redis

redis_client = redis.Redis(
    host="127.0.0.1",
    port=6379,
    decode_responses=True,
    max_connections=200,
    socket_keepalive=True,
    socket_connect_timeout=5,
    retry_on_timeout=True,
)