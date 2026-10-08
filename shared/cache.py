"""
Заглушка Cache. В runtime подменяется на shared.mocks.MockCache.
"""

class Cache:
    def __init__(self):
        self._store = {}

    async def connect(self): pass
    async def disconnect(self): pass


cache = Cache()
