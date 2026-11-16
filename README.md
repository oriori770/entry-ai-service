# Entry AI Service

AI Microservice for the **Tishrei Entry & Attendance System** (`tishreiQrCode`).

The service provides role-tailored intelligence for two primary personas:
1. **Admins & Superadmins:** Natural language business intelligence (Text-to-Aggregation over MongoDB attendance and entry records) and Human-in-the-Loop action proposals (e.g., event creation drafts).
2. **Gate Scanners (Sadarim):** Real-time ticket forensic diagnosis (identifying why a barcode was rejected or flagged) and hybrid RAG search across event policies, exceptions, and regulations.

---

## Tech Stack

* **Framework:** [FastAPI](https://fastapi.tiangolo.com/) + [Pydantic v2](https://docs.pydantic.dev/)
* **Server:** Uvicorn (ASGI)
* **LLM Orchestration:** [LiteLLM](https://docs.litellm.ai/) (Gemini 2.0 Flash / OpenAI GPT-4o-mini)
* **Database Access:** Async [Motor](https://motor.readthedocs.io/) (Read-Only queries against MongoDB)
* **RAG Engine:** Hybrid search with ChromaDB (vector embeddings) and BM25 (keyword rank)
* **Testing:** Pytest, pytest-asyncio, HTTPX

---

## Project Structure

```text
entry-ai-service/
├── app/
│   ├── main.py              # Application factory & middleware
│   ├── config.py            # Pydantic v2 settings & environment validation
│   ├── logging_config.py    # Structured Rich logging
│   └── routers/
│       └── health.py        # Service healthcheck endpoints
├── tests/
│   └── test_health.py       # Health endpoint unit tests
├── .env.example             # Template for environment variables
├── .gitignore               # Ignored files (secrets, venv, caches)
├── pytest.ini               # Pytest configuration
├── requirements.txt         # Production & development dependencies
├── run.py                   # Development entrypoint
└── README.md                # Service documentation
```

---

## Getting Started

### 1. Prerequisites
* Python 3.12+ (tested up to 3.14)
* Virtual environment (`venv`)

### 2. Setup Virtual Environment
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# Linux / macOS:
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Copy the example configuration to a local `.env` file:
```bash
cp .env.example .env
```
Update the settings in `.env` as needed (Port, MongoDB URI, Gemini / OpenAI API keys, JWT secret).

### 5. Run the Service
```bash
python run.py
```
The server will start at `http://localhost:8001`.

* **Interactive API Docs (Swagger):** `http://localhost:8001/docs`
* **Alternative API Docs (ReDoc):** `http://localhost:8001/redoc`
* **Health Check:** `http://localhost:8001/api/ai/health`

---

## Running Tests

Execute the test suite using `pytest`:
```bash
pytest
```

---

## License & Security
Internal service for the Tishrei Entry & Attendance System. All data access is strictly bounded by JWT authentication and read-only queries.
