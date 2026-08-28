from __future__ import annotations

import re
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from booking import create_viewing_booking
from inventory import inventory_service
from llm_agent import run_agent
from memory import (
    get_user_profile,
    initialize_storage,
    save_lead,
    save_session_message,
)


app = FastAPI(
    title="Cars AI Assistant",
    description="Grounded conversational used-car inventory assistant",
    version="1.0.0",
)


initialize_storage()


class ChatRequest(BaseModel):
    user_id: str = Field(min_length=1)
    user_name: str = Field(min_length=2)
    session_id: str = Field(min_length=1)
    message: str = Field(min_length=1)


class SearchRequest(BaseModel):
    make: Optional[str] = None
    model: Optional[str] = None
    keywords: Optional[str] = None
    min_year: Optional[int] = None
    max_year: Optional[int] = None
    max_price: Optional[int] = None
    limit: int = Field(default=5, ge=1, le=5)


class BookingRequest(BaseModel):
    user_id: str = Field(min_length=1)
    listing_id: int = Field(ge=1)
    viewing_datetime: str = Field(min_length=1)


def extract_budget(message: str) -> Optional[int]:
    patterns = [
        r"(?:under|below|budget|max(?:imum)?|aed)\s*([\d,]+)",
        r"([\d,]+)\s*aed",
    ]

    for pattern in patterns:
        match = re.search(pattern, message.lower())

        if match:
            try:
                return int(match.group(1).replace(",", ""))
            except ValueError:
                return None

    return None


def extract_listing_id(message: str) -> Optional[int]:
    match = re.search(
        r"(?:listing|vehicle|car)\s*#?\s*(\d+)",
        message.lower(),
    )

    if match:
        return int(match.group(1))

    return None


def is_lead_message(message: str) -> bool:
    lead_keywords = [
        "looking for",
        "i need",
        "i want",
        "my budget",
        "under aed",
        "below aed",
        "low mileage",
        "family car",
        "daily car",
        "suv",
        "sedan",
        "hatchback",
        "coupe",
        "convertible",
        "pickup",
        "white",
        "black",
        "silver",
        "grey",
        "gray",
        "warranty",
        "gcc",
    ]

    text = message.lower()
    budget = extract_budget(message)

    return budget is not None or any(
        keyword in text for keyword in lead_keywords
    )


def save_automatic_lead(request: ChatRequest):
    if not is_lead_message(request.message):
        return

    budget = extract_budget(request.message)
    listing_id = extract_listing_id(request.message)

    save_lead(
        user_id=request.user_id,
        name=request.user_name,
        budget_aed=budget,
        needs=request.message,
        listing_id=listing_id,
    )


@app.get("/health")
def health():
    return {
        "status": "ok",
        "inventory_count": len(inventory_service.df),
    }


@app.post("/chat")
def chat(request: ChatRequest):
    save_automatic_lead(request)

    result = run_agent(
        user_id=request.user_id,
        user_name=request.user_name,
        session_id=request.session_id,
        user_message=request.message,
    )

    save_session_message(
        session_id=request.session_id,
        role="user",
        content=request.message,
    )

    save_session_message(
        session_id=request.session_id,
        role="assistant",
        content=result["reply"],
    )

    return result


@app.post("/inventory/search")
def search_inventory(request: SearchRequest):
    results = inventory_service.search(
        make=request.make,
        model=request.model,
        keywords=request.keywords,
        min_year=request.min_year,
        max_year=request.max_year,
        max_price=request.max_price,
        limit=request.limit,
    )

    return {
        "result_count": len(results),
        "results": results,
    }


@app.get("/inventory/{listing_id}")
def get_listing(listing_id: int):
    listing = inventory_service.get_listing(listing_id)

    if listing is None:
        raise HTTPException(
            status_code=404,
            detail="Listing not found.",
        )

    return listing


@app.get("/users/{user_id}")
def get_profile(user_id: str):
    profile = get_user_profile(user_id)

    if profile is None:
        return {
            "user_id": user_id,
            "message": "No saved profile found.",
        }

    return profile


@app.post("/bookings")
def book_viewing(request: BookingRequest):
    result = create_viewing_booking(
        user_id=request.user_id,
        listing_id=request.listing_id,
        viewing_datetime_text=request.viewing_datetime,
    )

    if not result.get("success", False):
        raise HTTPException(
            status_code=400,
            detail=result.get(
                "error",
                "Booking could not be completed.",
            ),
        )

    return result