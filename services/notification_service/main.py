"""Точка входа Notification Service"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from services.trip_service.dispatcher import dispatcher

app = FastAPI()

class SearchRequest(BaseModel):
    city_from: str
    city_to: str
    date: str | None = None

class BookRequest(BaseModel):
    user_id: str
    flight_iata: str
    passengers: int = Field(ge=1, le=9)

@app.post("/api/search-flights")
async def search_flights(req: SearchRequest):
    flights = await dispatcher.search_flights(req.city_from, req.city_to, req.date)
    return {"flights": flights}

@app.post("/api/book-trip")
async def book_trip(req: BookRequest):
    result = await dispatcher.book_trip(req.user_id, req.flight_iata, req.passengers)
    if result.get("status") not in ["BOOKED", "BOOKED_WITH_HOTELS"]:
        raise HTTPException(status_code=400, detail=result.get("message", "Ошибка бронирования"))
    return result

