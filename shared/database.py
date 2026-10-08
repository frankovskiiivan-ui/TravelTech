"""
Заглушка DB. В runtime подменяется на shared.mocks.MockDatabase.
"""

class Database:
    def __init__(self):
        self.pool = None

    async def connect(self): pass
    async def disconnect(self): pass

    async def save_trip(self, trip_id: str, data: dict):
        raise NotImplementedError("Database not configured. Use mocks.")

    async def get_trip(self, trip_id: str):
        raise NotImplementedError("Database not configured. Use mocks.")

    async def get_all_trips(self):
        raise NotImplementedError("Database not configured. Use mocks.")

    async def save_feedback(self, trip_id: str, rating: int, comment: str):
        raise NotImplementedError("Database not configured. Use mocks.")

    async def save_notification(self, trip_id: str, message: str, channel: str):
        raise NotImplementedError("Database not configured. Use mocks.")

    async def get_stats(self):
        raise NotImplementedError("Database not configured. Use mocks.")


db = Database()
