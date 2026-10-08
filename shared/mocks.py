"""
Моки инфраструктуры для запуска без PostgreSQL/Redis/Kafka.
Используются в runtime через подмену глобальных объектов.
"""
import asyncio
import json
import sqlite3
import threading
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional


# =====================================================
# MockDatabase — SQLite в памяти
# =====================================================

class MockDatabase:
    def __init__(self, path: str = ":memory:"):
        self.path = path
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self):
        cur = self._conn.cursor()
        cur.executescript("""
            CREATE TABLE IF NOT EXISTS trips (
                trip_id TEXT PRIMARY KEY,
                user_id TEXT,
                flight_number TEXT,
                flight_status TEXT,
                city TEXT,
                alternatives TEXT,
                status TEXT,
                created_at TEXT,
                flight_data TEXT
            );
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trip_id TEXT,
                rating INTEGER,
                comment TEXT,
                created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trip_id TEXT,
                message TEXT,
                channel TEXT,
                created_at TEXT
            );
        """)
        self._conn.commit()

    async def connect(self): pass
    async def disconnect(self): pass

    async def save_trip(self, trip_id: str, data: dict):
        with self._lock:
            self._conn.execute("""
                INSERT OR REPLACE INTO trips
                (trip_id, user_id, flight_number, flight_status, city, alternatives, status, created_at, flight_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                trip_id,
                data.get("user_id"),
                data.get("flight", {}).get("flight"),
                data.get("flight", {}).get("status"),
                data.get("city"),
                json.dumps(data.get("alternatives", {}), ensure_ascii=False),
                data.get("status"),
                datetime.now().isoformat(),
                json.dumps(data.get("flight", {}), ensure_ascii=False),
            ))
            self._conn.commit()

    async def get_trip(self, trip_id: str) -> Optional[dict]:
        with self._lock:
            row = self._conn.execute("SELECT * FROM trips WHERE trip_id = ?", (trip_id,)).fetchone()
            if not row:
                return None
            flight_data = json.loads(row["flight_data"] or "{}")
            return {
                "trip_id": row["trip_id"],
                "user_id": row["user_id"],
                "flight": flight_data if flight_data else {"flight": row["flight_number"], "status": row["flight_status"]},
                "city": row["city"],
                "alternatives": json.loads(row["alternatives"] or "{}"),
                "status": row["status"],
                "created_at": row["created_at"],
            }

    async def get_all_trips(self) -> List[dict]:
        with self._lock:
            rows = self._conn.execute("SELECT * FROM trips ORDER BY created_at DESC").fetchall()
            result = []
            for r in rows:
                flight_data = json.loads(r["flight_data"] or "{}")
                result.append({
                    "trip_id": r["trip_id"],
                    "user_id": r["user_id"],
                    "flight": flight_data if flight_data else {"flight": r["flight_number"], "status": r["flight_status"]},
                    "city": r["city"],
                    "alternatives": json.loads(r["alternatives"] or "{}"),
                    "status": r["status"],
                    "created_at": r["created_at"],
                })
            return result

    async def save_feedback(self, trip_id: str, rating: int, comment: str):
        with self._lock:
            self._conn.execute(
                "INSERT INTO feedback (trip_id, rating, comment, created_at) VALUES (?, ?, ?, ?)",
                (trip_id, rating, comment, datetime.now().isoformat()),
            )
            self._conn.commit()

    async def save_notification(self, trip_id: str, message: str, channel: str):
        with self._lock:
            self._conn.execute(
                "INSERT INTO notifications (trip_id, message, channel, created_at) VALUES (?, ?, ?, ?)",
                (trip_id, message, channel, datetime.now().isoformat()),
            )
            self._conn.commit()

    async def get_stats(self) -> dict:
        with self._lock:
            total = self._conn.execute("SELECT COUNT(*) FROM trips").fetchone()[0]
            cancelled = self._conn.execute("SELECT COUNT(*) FROM trips WHERE flight_status='CANCELLED'").fetchone()[0]
            delayed = self._conn.execute("SELECT COUNT(*) FROM trips WHERE flight_status='DELAYED'").fetchone()[0]
            avg = self._conn.execute("SELECT AVG(rating) FROM feedback").fetchone()[0] or 0
            notif = self._conn.execute("SELECT COUNT(*) FROM notifications").fetchone()[0]
            return {
                "total_trips": total,
                "cancelled": cancelled,
                "delayed": delayed,
                "on_time": total - cancelled - delayed,
                "avg_rating": round(float(avg), 2),
                "notifications_sent": notif,
            }


# =====================================================
# MockCache — in-memory с TTL
# =====================================================

class MockCache:
    def __init__(self):
        self._store: Dict[str, tuple] = {}

    async def connect(self): pass
    async def disconnect(self): pass

    async def get(self, key: str) -> Optional[Any]:
        if key in self._store:
            value, expiry = self._store[key]
            if expiry is None or datetime.now() < expiry:
                return value
            del self._store[key]
        return None

    async def set(self, key: str, value: Any, ttl: int = 300):
        expiry = datetime.now() + timedelta(seconds=ttl) if ttl > 0 else None
        self._store[key] = (value, expiry)

    async def delete(self, key: str):
        self._store.pop(key, None)


# =====================================================
# MockKafka — in-memory очередь
# =====================================================

class MockKafka:
    def __init__(self):
        self.topics: Dict[str, asyncio.Queue] = {}
        self.subscribers: Dict[str, List[Callable]] = {}

    async def start_producer(self): pass
    async def stop_all(self): pass

    def _ensure_topic(self, topic: str):
        if topic not in self.topics:
            self.topics[topic] = asyncio.Queue()
            self.subscribers[topic] = []

    async def publish(self, topic: str, message: dict):
        self._ensure_topic(topic)
        await self.topics[topic].put(message)
        for cb in self.subscribers[topic]:
            try:
                await cb(message)
            except Exception as e:
                print(f"[MockKafka] handler error in {topic}: {e}")

    async def subscribe(self, topic: str, group_id: str, handler: Callable):
        self._ensure_topic(topic)
        self.subscribers[topic].append(handler)
