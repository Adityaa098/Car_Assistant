from __future__ import annotations

from datetime import datetime
from typing import Any

from inventory import inventory_service
from memory import save_booking


def validate_viewing_datetime(
    viewing_datetime_text: str,
) -> tuple[bool, str, datetime | None]:
    try:
        viewing_datetime = datetime.fromisoformat(
            viewing_datetime_text.strip()
        )
    except (TypeError, ValueError):
        return (
            False,
            "Use ISO format, for example 2026-08-28T17:00:00.",
            None,
        )

    if viewing_datetime.tzinfo is not None:
        return (
            False,
            (
                "Please provide local Dubai time without a timezone. "
                "Example: 2026-08-28T17:00:00."
            ),
            None,
        )

    # datetime.weekday(): Monday=0, Sunday=6.
    if viewing_datetime.weekday() == 6:
        return (
            False,
            "Viewings are unavailable on Sunday.",
            None,
        )

    if not 8 <= viewing_datetime.hour < 20:
        return (
            False,
            "Viewing hours are Monday to Saturday, 08:00 to 20:00.",
            None,
        )

    return (
        True,
        "Viewing time is valid.",
        viewing_datetime,
    )


def create_viewing_booking(
    user_id: str,
    listing_id: int,
    viewing_datetime_text: str,
) -> dict[str, Any]:
    user_id = user_id.strip()

    if not user_id:
        return {
            "success": False,
            "error": "A user ID is required to book a viewing.",
        }

    if listing_id < 1:
        return {
            "success": False,
            "error": "A valid listing ID is required.",
        }

    listing = inventory_service.get_listing(listing_id)

    if listing is None:
        return {
            "success": False,
            "error": f"Listing #{listing_id} was not found.",
        }

    valid, message, viewing_datetime = validate_viewing_datetime(
        viewing_datetime_text
    )

    if not valid or viewing_datetime is None:
        return {
            "success": False,
            "error": message,
        }

    booking_id = save_booking(
        user_id=user_id,
        listing_id=listing_id,
        viewing_datetime=viewing_datetime.isoformat(),
    )

    return {
        "success": True,
        "booking_id": booking_id,
        "user_id": user_id,
        "listing_id": listing_id,
        "vehicle": (
            f"{listing['year']} "
            f"{listing['make']} "
            f"{listing['model']}"
        ),
        "viewing_datetime": viewing_datetime.isoformat(),
        "message": "Viewing booked successfully.",
    }