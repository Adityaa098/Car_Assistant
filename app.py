from __future__ import annotations

import re
import uuid

import requests
import streamlit as st


API_URL = "http://127.0.0.1:8000"


st.set_page_config(
    page_title="DriveMate",
    page_icon="dubizzle_page.png",
    layout="wide",
)


st.markdown(
    """
    <style>
    .stApp {
        background:
            radial-gradient(
                circle at 85% 8%,
                rgba(255, 90, 95, 0.13),
                transparent 26%
            ),
            radial-gradient(
                circle at 10% 90%,
                rgba(255, 155, 106, 0.06),
                transparent 24%
            ),
            linear-gradient(135deg, #0b0d12 0%, #151821 100%);
    }

    /* Push main content toward the left corner */
    .block-container {
        padding-top: 3rem;
        padding-left: 2rem;
        padding-right: 2rem;
    }

    [data-testid="stSidebar"] {
        background:
            radial-gradient(
                circle at 50% 0%,
                rgba(255, 90, 95, 0.08),
                transparent 28%
            ),
            linear-gradient(180deg, #242631 0%, #191b23 100%);
        border-right: 1px solid #343743;
    }

    /* Pull the logo up: remove the sidebar's default top padding */
    [data-testid="stSidebarUserContent"] {
        padding-top: 0.4rem;
    }

    [data-testid="stSidebar"] .block-container {
        padding-top: 0.4rem;
    }

    [data-testid="stSidebar"],
    [data-testid="stSidebarContent"],
    [data-testid="stSidebarUserContent"],
    [data-testid="stSidebar"] > div,
    [data-testid="stSidebar"] > div:first-child {
        overflow: hidden !important;
    }

    [data-testid="stSidebar"] *::-webkit-scrollbar {
        display: none;
    }

    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {
        color: #ffffff;
    }

    [data-testid="stSidebar"] .stImage {
        display: flex;
        justify-content: center;
        margin-top: 0;
        margin-bottom: 0.4rem;
        padding-bottom: 0.4rem;
        border-bottom: 1px solid rgba(255, 255, 255, 0.12);
    }

    /* Compact sidebar so everything fits without scrolling */
    [data-testid="stSidebar"] h2 {
        font-size: 1.1rem;
        margin-top: 0.15rem;
        margin-bottom: 0.3rem;
    }

    [data-testid="stSidebar"] .stMarkdown p {
        margin-bottom: 0.15rem;
        font-size: 0.86rem;
    }

    [data-testid="stSidebar"] [data-testid="stCode"],
    [data-testid="stSidebar"] pre {
        padding: 0.3rem 0.55rem !important;
        margin-bottom: 0.25rem !important;
    }

    [data-testid="stSidebar"] [data-testid="stCode"] code,
    [data-testid="stSidebar"] pre code {
        font-size: 0.76rem !important;
        line-height: 1.2 !important;
    }

    [data-testid="stSidebar"] .stButton {
        margin-top: 0.2rem;
        margin-bottom: 0.2rem;
    }

    [data-testid="stSidebar"] hr {
        margin-top: 0.45rem;
        margin-bottom: 0.45rem;
    }

    [data-testid="stSidebar"] img {
        mix-blend-mode: screen;
        filter: brightness(1.12) contrast(1.08);
        border-radius: 10px;
    }

    .assistant-name {
        color: #ffffff;
        font-size: 4.2rem;
        font-weight: 850;
        line-height: 1.02;
        letter-spacing: -2px;
        margin-top: 0.4rem;
        margin-bottom: 0.65rem;
    }

    .assistant-name span {
        color: #ff6268;
    }

    .assistant-description {
        color: #aeb4c4;
        font-size: 1.08rem;
        line-height: 1.65;
        max-width: 780px;
        margin-bottom: 1.5rem;
    }

    .accent-line {
        width: 78px;
        height: 5px;
        border-radius: 999px;
        background: linear-gradient(90deg, #ff4f5e, #ff9b6a);
        margin-bottom: 1.25rem;
        box-shadow: 0 0 18px rgba(255, 90, 95, 0.32);
    }

    .feature-card {
        min-height: 100px;
        padding: 1rem;
        border-radius: 17px;
        background: rgba(255, 255, 255, 0.055);
        border: 2px solid rgba(255, 255, 255, 0.105);
        transition:
            transform 0.2s ease,
            border-color 0.2s ease,
            background 0.2s ease;
    }

    .feature-card:hover {
        transform: translateY(-4px);
        border-color: rgba(255, 90, 95, 0.70);
        background: rgba(255, 90, 95, 0.08);
    }

    .feature-title {
        color: #ffffff;
        font-size: 1rem;
        font-weight: 750;
        margin-bottom: 0.4rem;
    }

    .feature-text {
        color: #aeb4c4;
        font-size: 0.84rem;
        line-height: 1.5;
    }

    [data-testid="stChatInput"] {
        border-radius: 19px;
        background: rgba(32, 35, 46, 0.94);
        box-shadow: 0 12px 32px rgba(0, 0, 0, 0.34);
        backdrop-filter: blur(12px);
    }

    [data-testid="stChatInput"]:focus-within {
        border-color: #ff5a5f;
        box-shadow:
            0 0 0 2px rgba(255, 90, 95, 0.18),
            0 12px 32px rgba(0, 0, 0, 0.34);
    }

    [data-testid="stChatMessage"] {
        border-radius: 10px;
        margin-bottom: 0.8rem;
    }

    .stButton > button {
        border-radius: 12px;
        border: 1px solid #626777;
        transition: all 0.2s ease;
    }

    .stButton > button:hover {
        color: #ffffff;
        border-color: #ff5a5f;
        background: rgba(255, 90, 95, 0.12);
        transform: translateY(-1px);
    }

    [data-testid="stExpander"] {
        border-radius: 16px;
        border: 1px solid #3d4250;
        background: rgba(255, 255, 255, 0.04);
        margin-bottom: 0.85rem;
        transition: border-color 0.2s ease;
    }

    [data-testid="stExpander"]:hover {
        border-color: rgba(255, 90, 95, 0.58);
    }

    .availability-card {
        padding: 0.8rem 1rem;
        border-radius: 15px;
        background: rgba(255, 255, 255, 0.055);
        border-left: 4px solid #ff5a5f;
        color: #d9dce5;
        line-height: 1.6;
        box-shadow: 0 8px 22px rgba(0, 0, 0, 0.16);
    }

    @media (max-width: 768px) {
        .assistant-name {
            font-size: 2.8rem;
            letter-spacing: -1px;
        }

        .assistant-description {
            font-size: 0.95rem;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def initialize_state() -> None:
    if "user_name" not in st.session_state:
        st.session_state.user_name = ""

    if "user_id" not in st.session_state:
        st.session_state.user_id = ""

    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())

    if "identity_step" not in st.session_state:
        st.session_state.identity_step = "name"

    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": (
                    "Welcome to dubizzle DriveMate! "
                    "Before we begin, what is your name?"
                ),
            }
        ]


def reset_session() -> None:
    """
    Starts a new conversation session.

    This resets frontend/session state only.
    It does not delete the user's SQLite profile.
    """
    st.session_state.user_name = ""
    st.session_state.user_id = ""
    st.session_state.session_id = str(uuid.uuid4())
    st.session_state.identity_step = "name"
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": (
                "Welcome to dubizzle DriveMate! "
                "Before we begin, what is your name?"
            ),
        }
    ]


def display_cars(cars: list[dict]) -> None:
    for car in cars:
        listing_id = car.get("listing_id", "")
        year = car.get("year", "")
        make = str(car.get("make", "")).title()
        model = str(car.get("model", "")).title()
        trim = str(car.get("trim", "")).title()

        with st.expander(
            f" Listing #{listing_id} — "
            f"{year} {make} {model} {trim}"
        ):
            title = car.get("title", "")

            if title:
                st.write(title)

            price = car.get("price_aed")

            if price is None:
                price = car.get("listed_price_aed")

            mileage = car.get("mileage_km")

            col1, col2 = st.columns(2)

            with col1:
                if price is None:
                    st.write("**Listed price:** Not stated")
                else:
                    st.write(f"**Listed price:** AED {int(price):,}")

            with col2:
                if mileage is None:
                    st.write("**Mileage:** Not stated")
                else:
                    st.write(f"**Mileage:** {int(mileage):,} km")

            description = car.get("description", "")

            if description:
                st.caption(description[:900])

            photo_url = car.get("photo_url")

            if photo_url is None:
                photo_url = car.get("photourl")

            if photo_url:
                try:
                    st.image(photo_url, use_container_width=True)
                except Exception:
                    st.caption("Image could not be loaded.")


def handle_identity_message(message: str) -> dict:
    message = message.strip()

    if st.session_state.identity_step == "name":
        if len(message) < 2:
            return {
                "reply": "Please enter a valid name with at least two characters.",
                "cars": [],
                "show_cars": False,
            }

        st.session_state.user_name = message
        st.session_state.identity_step = "user_id"

        return {
            "reply": (
                f"Nice to meet you, {message}! "
                "Please enter your user ID so I can remember your preferences "
                "across sessions."
            ),
            "cars": [],
            "show_cars": False,
        }

    if st.session_state.identity_step == "user_id":
        if not re.fullmatch(r"[a-zA-Z0-9_-]{3,40}", message):
            return {
                "reply": (
                    "Please enter a user ID containing 3–40 characters. "
                    "Use only letters, numbers, hyphens, or underscores."
                ),
                "cars": [],
                "show_cars": False,
            }

        st.session_state.user_id = message
        st.session_state.identity_step = "ready"

        return {
            "reply": (
                f"Thanks, {st.session_state.user_name}! "
                "How can I help you find a car today?"
            ),
            "cars": [],
            "show_cars": False,
        }

    return {
        "reply": "How can I help you with the car inventory?",
        "cars": [],
        "show_cars": False,
    }


def send_message(message: str) -> dict:
    user_name = st.session_state.user_name.strip()
    user_id = st.session_state.user_id.strip()

    if not user_name:
        raise ValueError("Please enter your name in the chat first.")

    if not user_id:
        raise ValueError("Please enter your user ID in the chat first.")

    if not re.fullmatch(r"[a-zA-Z0-9_-]{3,40}", user_id):
        raise ValueError(
            "User ID must be 3–40 characters and contain only letters, "
            "numbers, hyphens, or underscores."
        )

    payload = {
        "user_id": user_id,
        "user_name": user_name,
        "session_id": st.session_state.session_id,
        "message": message,
    }

    response = requests.post(
        f"{API_URL}/chat",
        json=payload,
        timeout=90,
    )

    response.raise_for_status()

    return response.json()


initialize_state()


with st.sidebar:
    st.image(
        "dubizzle_logo.jpg",
        width=150,
    )

    st.header("User and session")

    st.write("Name:")
    st.code(
        st.session_state.user_name
        if st.session_state.user_name
        else "Not provided"
    )

    st.write("User ID:")
    st.code(
        st.session_state.user_id
        if st.session_state.user_id
        else "Not provided"
    )

    st.write("Session ID:")
    st.code(st.session_state.session_id[:12])

    if st.button(
        " Start new session",
        use_container_width=True,
    ):
        reset_session()
        st.rerun()

    st.divider()

    st.write("Viewing and Test drive availability:")

    st.markdown(
        """
        <div class="availability-card">
            <b>Monday–Saturday</b><br>
            🕗 08:00–20:00
        </div>
        """,
        unsafe_allow_html=True,
    )


st.markdown(
    """
    <div class="assistant-name">
        <span>DriveMate</span>
    </div>
    """,
    unsafe_allow_html=True,
)


st.markdown(
    '<div class="accent-line"></div>',
    unsafe_allow_html=True,
)


st.markdown(
    """
    <div class="assistant-description">
        Your personal dubizzle car companion for discovering,
        comparing, and viewing your next vehicle.
    </div>
    """,
    unsafe_allow_html=True,
)


feature_col1, feature_col2, feature_col3 = st.columns(3)


with feature_col1:
    st.markdown(
        """
        <div class="feature-card">
            <div class="feature-title">Smart Search</div>
            <div class="feature-text">
                Find cars by make, budget, year, mileage, and more.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


with feature_col2:
    st.markdown(
        """
        <div class="feature-card">
            <div class="feature-title">Follow-Up Conversations</div>
            <div class="feature-text">
                Ask follow-up questions and refine your preferences.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


with feature_col3:
    st.markdown(
        """
        <div class="feature-card">
            <div class="feature-title">Easy Viewings</div>
            <div class="feature-text">
                Get assistance with arranging your vehicle viewing.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

        if (
            message["role"] == "assistant"
            and message.get("show_cars")
            and message.get("cars")
        ):
            display_cars(message["cars"])


prompt = st.chat_input(
    "Example: Show me BMW cars under AED 200,000"
)


if prompt:
    st.session_state.messages.append(
        {
            "role": "user",
            "content": prompt,
        }
    )

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        try:
            if st.session_state.identity_step != "ready":
                data = handle_identity_message(prompt)
            else:
                with st.spinner(
                    "Understanding your request and searching..."
                ):
                    data = send_message(prompt)

            st.markdown(data.get("reply", ""))

            if data.get("show_cars") and data.get("cars"):
                display_cars(data["cars"])

        except ValueError as error:
            data = {
                "reply": str(error),
                "cars": [],
                "show_cars": False,
            }

            st.error(str(error))
            st.markdown(data["reply"])

        except requests.RequestException as error:
            data = {
                "reply": (
                    "I could not connect to the FastAPI backend. "
                    "Please confirm the backend is running."
                ),
                "cars": [],
                "show_cars": False,
            }

            st.error(str(error))
            st.markdown(data["reply"])

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": data.get("reply", ""),
            "cars": data.get("cars", []),
            "show_cars": data.get("show_cars", False),
        }
    )