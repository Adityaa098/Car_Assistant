# DriveMate AI Assistant

A FastAPI and Streamlit conversational assistant for searching used-car inventory, remembering user preferences, qualifying leads, and booking vehicle viewings.

## Features

- Gemini LLM integration through LiteLLM
- Function-calling tools for inventory search and actions
- Pandas retrieval over the supplied Excel dataset
- Short-term conversation memory
- Long-term SQLite user-profile memory
- Lead capture in a local CSV
- Viewing booking validation
- Streamlit chat interface

## Setup

Create the environment with uv:

```powershell
uv venv
.venv\Scripts\Activate.ps1
uv pip install -r requirements.txt
```

Create a `.env` file in the project root:

```env
GEMINI_API_KEY=your_google_ai_studio_api_key
```

Place the supplied dataset at:

```text
data/cars.xlsx
```

## Run the backend

```powershell
uv run uvicorn main:app --reload
```

API documentation:

```text
http://127.0.0.1:8000/docs
```

## Run the Streamlit client

Open a second terminal:

```powershell
uv run streamlit run app.py
```

The detailed 
architecture, 
implementation explanation, 
test scenarios, and screenshots 
are included in 
'README.docx' and 
'INTERFAC_SCREENSHOTS.docx'.
