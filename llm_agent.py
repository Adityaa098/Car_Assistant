from __future__ import annotations

import json
import os
from typing import Any

from dotenv import load_dotenv
from litellm import completion

from booking import create_viewing_booking
from inventory import inventory_service
from memory import (
    get_last_results,
    get_session,
    get_user_profile,
    save_user_profile,
    set_last_results,
)

load_dotenv()

MODEL = "gemini/gemini-3.6-flash"

MAX_LLM_CALLS = 2
MAX_SEARCH_RESULTS = 5
MAX_HISTORY_MESSAGES = 6


SYSTEM_PROMPT = """
You are a helpful used-car marketplace assistant.

You help users with:
- Searching the supplied vehicle inventory.
- Asking about vehicle details.
- Comparing returned listings.
- Remembering current-session context.
- Remembering persistent user preferences.
- Booking vehicle viewings.

INVENTORY GROUNDING:
- The supplied inventory is the only source of vehicle information.
- Never invent a listing, make, model, year, price, mileage, warranty,
  specification, feature, dealer, or location.
- If a detail is absent from a tool result, say it is not stated.
- Never confuse a monthly payment with a cash/listed price.
- Always mention Listing_ID when referring to a vehicle.
- Do not say that a vehicle is available unless it appeared in a tool result.
- Do not mention any vehicle unless its Listing_ID exists in the latest
  relevant tool result.

SEARCH:
- Use search_inventory for inventory searches.
- Use get_listing for one specific listing.
- Use get_last_results for:
  "the first one", "the second one", "that car", "that BMW", or "it".
- Use only one search_inventory call for one user message.
- Do not repeat the same search.
- If there are no search results, clearly say no matching vehicle was found.

MEMORY:
- Use get_user_profile when the user asks what they wanted previously.
- Save preferences when the user clearly states their name, budget, make,
  model, body type, colour, year, or required features.
- Use current-session results for references to previous search results.

LEADS:
- Lead saving is handled by the FastAPI backend before this LLM call.
- Do not attempt to save leads through a tool.
- Do not ask the user to say "qualified lead."
- When the user gives a budget or clear vehicle requirements, acknowledge
  their needs naturally.

BOOKINGS:
- Viewings are available Monday to Saturday.
- Viewing hours are 08:00 to 20:00.
- Sunday and out-of-hours bookings must be rejected.
- A valid Listing_ID and ISO datetime are required.
- Use book_viewing for booking requests.
- Never claim a booking succeeded unless book_viewing returns success.

GUARDRAILS:
- Politely refuse programming, homework, history, essay, and unrelated requests.
- Do not discuss, mention, compare, or promote competing used-car platforms.
- Redirect the user to vehicle-related assistance.

RESULT CONSISTENCY:
- When presenting search results, use only the latest search_inventory result.
- Every Listing_ID mentioned in your text must appear in the corresponding
  returned tool result.
- Do not state an exact result count unless it matches result_count from the tool.
- If a tool returns an error, report the error naturally and do not invent
  a successful outcome.

RESPONSE STYLE:
- Be concise and natural.
- Base factual claims only on tool results.
- State clearly when information is not present in a listing.
"""


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_inventory",
            "description": (
                "Search the supplied inventory using exact make/model/year/"
                "price filters and description keywords."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "make": {
                        "type": "string",
                        "description": "Vehicle make, such as BMW or Ford.",
                    },
                    "model": {
                        "type": "string",
                        "description": "Vehicle model, such as X1 or Explorer.",
                    },
                    "keywords": {
                        "type": "string",
                        "description": (
                            "Comma-separated description terms such as "
                            "white, SUV, warranty, GCC, sunroof, electric, "
                            "or 4WD."
                        ),
                    },
                    "min_year": {
                        "type": "integer",
                    },
                    "max_year": {
                        "type": "integer",
                    },
                    "max_price": {
                        "type": "integer",
                        "description": (
                            "Maximum listed cash price in AED. Do not use "
                            "monthly payment as cash price."
                        ),
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum 5 results.",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_listing",
            "description": "Retrieve a complete listing by Listing_ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "listing_id": {
                        "type": "integer",
                    },
                },
                "required": ["listing_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_last_results",
            "description": (
                "Retrieve previous results from the current session. "
                "Use for references such as 'first one' or 'that car'."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_user_profile",
            "description": (
                "Retrieve the persistent profile and preferences for "
                "the current user."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "save_user_profile",
            "description": "Save persistent user preferences.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                    },
                    "budget_aed": {
                        "type": "integer",
                    },
                    "preferences": {
                        "type": "object",
                    },
                    "liked_listing_ids": {
                        "type": "array",
                        "items": {
                            "type": "integer",
                        },
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "book_viewing",
            "description": (
                "Book a vehicle viewing after validating the listing and "
                "date/time."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "listing_id": {
                        "type": "integer",
                    },
                    "viewing_datetime": {
                        "type": "string",
                        "description": (
                            "ISO datetime, for example "
                            "2026-08-28T17:00:00."
                        ),
                    },
                },
                "required": [
                    "listing_id",
                    "viewing_datetime",
                ],
            },
        },
    },
]


def remove_nan_values(value: Any) -> Any:
    """
    Recursively replace NaN values with None before JSON serialization.
    """
    if isinstance(value, dict):
        return {
            key: remove_nan_values(item)
            for key, item in value.items()
        }

    if isinstance(value, list):
        return [
            remove_nan_values(item)
            for item in value
        ]

    if value is None:
        return None

    try:
        if value != value:
            return None
    except Exception:
        pass

    return value


def parse_tool_arguments(raw_arguments: Any) -> dict[str, Any]:
    if not raw_arguments:
        return {}

    if isinstance(raw_arguments, dict):
        return raw_arguments

    try:
        parsed = json.loads(raw_arguments)

        if isinstance(parsed, dict):
            return parsed

        return {}
    except (TypeError, json.JSONDecodeError):
        return {}


def clean_search_arguments(
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """
    Enforce safe limits and remove malformed search values.
    """
    cleaned: dict[str, Any] = {}

    for key in [
        "make",
        "model",
        "keywords",
        "min_year",
        "max_year",
        "max_price",
    ]:
        value = arguments.get(key)

        if value is not None and value != "":
            cleaned[key] = value

    try:
        limit = int(
            arguments.get(
                "limit",
                MAX_SEARCH_RESULTS,
            )
        )
    except (TypeError, ValueError):
        limit = MAX_SEARCH_RESULTS

    cleaned["limit"] = max(
        1,
        min(limit, MAX_SEARCH_RESULTS),
    )

    return cleaned


def execute_tool(
    tool_name: str,
    arguments: dict[str, Any],
    user_id: str,
    user_name: str,
    session_id: str,
) -> dict[str, Any]:
    session = get_session(session_id)

    if tool_name == "search_inventory":
        search_arguments = clean_search_arguments(arguments)

        results = inventory_service.search(
            make=search_arguments.get("make"),
            model=search_arguments.get("model"),
            keywords=search_arguments.get("keywords"),
            min_year=search_arguments.get("min_year"),
            max_year=search_arguments.get("max_year"),
            max_price=search_arguments.get("max_price"),
            limit=search_arguments["limit"],
        )

        safe_results = remove_nan_values(results)

        set_last_results(
            session_id=session_id,
            results=safe_results,
        )

        if safe_results:
            session["selected_listing_id"] = safe_results[0].get(
                "listing_id"
            )

        return {
            "result_count": len(safe_results),
            "results": safe_results,
        }

    if tool_name == "get_listing":
        listing_id = arguments.get("listing_id")

        if listing_id is None:
            return {
                "error": "A listing ID is required.",
            }

        try:
            listing_id = int(listing_id)
        except (TypeError, ValueError):
            return {
                "error": "Listing ID must be an integer.",
            }

        listing = inventory_service.get_listing(listing_id)

        if listing is None:
            return {
                "error": (
                    f"Listing #{listing_id} was not found "
                    "in the supplied inventory."
                ),
            }

        safe_listing = remove_nan_values(listing)

        session["selected_listing_id"] = listing_id

        return {
            "listing": safe_listing,
        }

    if tool_name == "get_last_results":
        return remove_nan_values(
            get_last_results(session_id)
        )

    if tool_name == "get_user_profile":
        return remove_nan_values({
            "profile": get_user_profile(user_id),
        })

    if tool_name == "save_user_profile":
        save_user_profile(
            user_id=user_id,
            name=user_name,
            budget_aed=arguments.get("budget_aed"),
            preferences=arguments.get("preferences"),
            liked_listing_ids=arguments.get(
                "liked_listing_ids"
            ),
        )

        return {
            "status": "profile saved",
        }

    if tool_name == "book_viewing":
        listing_id = arguments.get("listing_id")
        viewing_datetime = arguments.get(
            "viewing_datetime"
        )

        if listing_id is None or not viewing_datetime:
            return {
                "error": (
                    "Both listing_id and viewing_datetime "
                    "are required."
                ),
            }

        try:
            listing_id = int(listing_id)
        except (TypeError, ValueError):
            return {
                "error": "Listing ID must be an integer.",
            }

        return remove_nan_values(
            create_viewing_booking(
                user_id=user_id,
                listing_id=listing_id,
                viewing_datetime_text=viewing_datetime,
            )
        )

    return {
        "error": f"Unknown tool: {tool_name}",
    }


def build_messages(
    session_id: str,
    user_name: str,
    user_message: str,
) -> list[dict[str, Any]]:
    session = get_session(session_id)

    messages: list[dict[str, Any]] = [
        {
            "role": "system",
            "content": (
                f"{SYSTEM_PROMPT}\n\n"
                f"CURRENT USER NAME: {user_name}\n"
                "Treat this name as user-provided identity context. "
                "Do not ask for it again."
            ),
        }
    ]


    for message in session.get("messages", [])[
        -MAX_HISTORY_MESSAGES:
    ]:
        if message.get("role") in {
            "user",
            "assistant",
        }:
            messages.append({
                "role": message["role"],
                "content": message.get("content", ""),
            })

    messages.append({
        "role": "user",
        "content": user_message,
    })

    return messages


def build_assistant_message(
    assistant_message: Any,
) -> dict[str, Any]:
    """
    Convert the LiteLLM response into a normal OpenAI-compatible message.
    """
    payload: dict[str, Any] = {
        "role": "assistant",
        "content": assistant_message.content or "",
    }

    tool_calls = assistant_message.tool_calls or []

    if tool_calls:
        payload["tool_calls"] = [
            {
                "id": tool_call.id,
                "type": "function",
                "function": {
                    "name": tool_call.function.name,
                    "arguments": (
                        tool_call.function.arguments
                        or "{}"
                    ),
                },
            }
            for tool_call in tool_calls
        ]

    return payload


def run_agent(
    user_id: str,
    user_name: str,
    session_id: str,
    user_message: str,
) -> dict[str, Any]:
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        return {
            "reply": (
                "Gemini is not configured. Add GEMINI_API_KEY "
                "to your .env file."
            ),
            "cars": [],
            "show_cars": False,
        }

    messages = build_messages(
        session_id=session_id,
        user_name=user_name,
        user_message=user_message,
    )

    
    current_cars: list[dict[str, Any]] = []

    llm_calls = 0

    try:
        while llm_calls < MAX_LLM_CALLS:
            llm_calls += 1

            response = completion(
                model=MODEL,
                api_key=api_key,
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
                temperature=0,
                max_tokens=500,
            )

            assistant_message = response.choices[0].message
            tool_calls = assistant_message.tool_calls or []

            
            if not tool_calls:
                return {
                    "reply": (
                        assistant_message.content
                        or "I could not generate a response."
                    ),
                    "cars": current_cars,
                    "show_cars": bool(current_cars),
                }

           
            tool_call = tool_calls[0]
            tool_name = tool_call.function.name

            arguments = parse_tool_arguments(
                tool_call.function.arguments
            )

            if tool_name == "search_inventory":
                arguments = clean_search_arguments(arguments)

            result = execute_tool(
                tool_name=tool_name,
                arguments=arguments,
                user_id=user_id,
                user_name=user_name,
                session_id=session_id,
            )

            safe_result = remove_nan_values(result)

            if tool_name == "search_inventory":
                current_cars = safe_result.get(
                    "results",
                    [],
                )

            elif tool_name == "get_listing":
                listing = safe_result.get("listing")

                if listing:
                    current_cars = [listing]

            messages.append(
                build_assistant_message(assistant_message)
            )

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(
                    safe_result,
                    default=str,
                    allow_nan=False,
                ),
            })

        if current_cars:
            return {
                "reply": (
                    "I found matching vehicles in the inventory. "
                    "Please select a listing to see more details."
                ),
                "cars": current_cars,
                "show_cars": True,
            }

        return {
            "reply": (
                "I could not complete that request within the "
                "available request limit."
            ),
            "cars": [],
            "show_cars": False,
        }

    except Exception as error:
        error_text = str(error)
        lowered_error = error_text.lower()

        print(
            f"LLM error: {type(error).__name__}: {error}"
        )

        if (
            "429" in error_text
            or "quota" in lowered_error
            or "resource_exhausted" in lowered_error
            or "rate limit" in lowered_error
        ):
            return {
                "reply": (
                    "The free AI-provider quota is temporarily exhausted. "
                    "Please try again later."
                ),
                "cars": [],
                "show_cars": False,
            }

        if (
            "model not found" in lowered_error
            or "not found" in lowered_error
            or "invalid model" in lowered_error
        ):
            return {
                "reply": (
                    "The configured Gemini model was not found. "
                    "Please check the MODEL value in llm_agent.py."
                ),
                "cars": [],
                "show_cars": False,
            }

        return {
            "reply": (
                "I could not complete that request right now. "
                "Please try again."
            ),
            "cars": [],
            "show_cars": False,
        }