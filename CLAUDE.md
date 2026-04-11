# 🧠 Project Guidelines: IELTS Assistant Backend

This document defines the rules and structure that all AI-generated code MUST follow.

---

# 📦 Project Structure

The backend follows a layered architecture:

app/
├── api/ # HTTP layer (FastAPI routes)
├── agents/ # Phidata AI agents
├── services/ # Business logic layer
├── db/ # Database models and connection
└── main.py # Application entry point

---

# 🧩 Layer Responsibilities

## 1. api/ (API Layer)

Purpose:

- Handle HTTP requests and responses
- Validate input using Pydantic
- Return structured JSON responses

Rules:

- ❌ DO NOT write business logic here
- ❌ DO NOT call database directly
- ❌ DO NOT implement AI logic here
- ✅ ONLY call service layer functions

---

## 2. services/ (Business Logic Layer)

Purpose:

- Orchestrate application logic
- Call AI agents
- Process and transform data
- Save/retrieve data from database

Rules:

- ✅ This is the ONLY layer that:
  - calls agents
  - interacts with database
- ❌ DO NOT define FastAPI routes
- ❌ DO NOT define agent prompts here

---

## 3. agents/ (AI Layer)

Purpose:

- Define AI behavior using Phidata agents
- Handle prompt design (description, instructions, expected_output)

Rules:

- ❌ DO NOT access database
- ❌ DO NOT import FastAPI
- ❌ DO NOT contain business logic
- ✅ ONLY:
  - receive input
  - return structured output

---

## 4. db/ (Data Layer)

Purpose:

- Define database schema
- Manage database connection

Files:

- models.py → SQLAlchemy models
- connection.py → DB session setup

Rules:

- ❌ DO NOT include business logic
- ❌ DO NOT call AI agents

---

## 5. main.py (Entry Point)

Purpose:

- Initialize FastAPI app
- Register API routers

Rules:

- ❌ DO NOT include business logic
- ❌ DO NOT call agents directly

---

# 🔄 Data Flow (STRICT)

All features MUST follow this flow:

API → Service → Agent → Service → DB → API Response

---

# 🧠 AI Agent Rules (Phidata)

Each agent MUST include:

- description
- instructions (list of strings)
- expected_output (strict JSON format)

Rules:

- Output MUST be valid JSON
- No extra text outside JSON
- Must be API-friendly

---

# 🧾 Database Rules

## sentences table:

- original (TEXT, NOT NULL)
- corrected (TEXT, NOT NULL)
- natural (TEXT, NOT NULL)
- has_mistakes (BOOLEAN)

## sentence_mistakes table:

- type (grammar | word_choice | fluency)
- original
- fix
- explanation

Rules:

- ❌ DO NOT store mistakes as JSON in sentences table
- ✅ Use separate table for normalization

---

# ⚠️ Error Handling Rules

- API layer must return HTTPException on failure
- Service layer should handle parsing/logic errors
- Agent layer should NEVER crash the system

---

# 🧼 Code Style Rules

- Use clear function names
- Keep functions small and focused
- Use type hints where possible
- Avoid duplication

---

# 🚫 Anti-Patterns (STRICTLY FORBIDDEN)

- ❌ Calling agent directly inside API
- ❌ Writing SQL inside API files
- ❌ Mixing AI logic with database logic
- ❌ Returning unstructured text from agents

---

# ✅ Example Flow (Sentence Correction)

1. API receives request
2. API calls sentence_service.correct_sentence()
3. Service calls correction_agent
4. Service parses output
5. Service saves to DB
6. API returns response

---

# 🎯 Goal

Build a scalable IELTS assistant backend with:

- clean architecture
- reusable AI agents
- structured data
- future support for personalization (vector DB)

---

# 🔥 Final Rule

If unsure:
→ Keep layers separated
→ Keep output structured
→ Keep logic inside services
