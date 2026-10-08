"""
Заглушка Kafka. В runtime подменяется на shared.mocks.MockKafka.
"""

class KafkaClient:
    def __init__(self): pass

    async def start_producer(self): pass
    async def stop_all(self): pass

    async def publish(self, topic: str, message: dict):
        raise NotImplementedError("Kafka not configured. Use mocks.")

    async def subscribe(self, topic: str, group_id: str, handler):
        raise NotImplementedError("Kafka not configured. Use mocks.")


kafka = KafkaClient()
