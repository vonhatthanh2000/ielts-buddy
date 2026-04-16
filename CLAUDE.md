# AI coding guidelines

Repository-specific guardrails for this FastAPI + Supabase IELTS assistant backend.
Prefer practical consistency with existing modules over abstract patterns.

---

## Current project map

- `main.py`: app bootstrap, CORS config, router registration, health check.
- `api/`: HTTP routers and request auth dependency (`deps.py`).
- `schemas/`: Pydantic request/response models shared across routers.
- `services/`: business logic (`auth_service`, `user_service`, `sentence_service`).
- `agents/`: Phidata/OpenAI prompt definitions and agent wiring.
- `supabase/`: Supabase client singleton and DB access setup.

---

## Architecture rules

- Keep a clean one-way flow: API -> services -> external systems (agent/DB) -> API response.
- Keep routers thin. Validation and HTTP status mapping belong in `api/`.
- Keep orchestration in `services/`. This includes parse, transform, and persistence logic.
- Keep prompts and model setup in `agents/`, not in routers/services.
- Keep shared contracts in `schemas/` and return schema-compatible data.

---

## Layer responsibilities

### 1) `api/` (transport layer)

Do:
- Parse request bodies and path params with schema types.
- Use `Depends(...)` for auth (`get_current_user_id`) and Supabase client wiring.
- Raise `HTTPException` with meaningful status codes/messages.

Do not:
- Perform direct DB table operations.
- Build prompt text or call agent instances.
- Embed reusable business logic.

### 2) `services/` (business layer)

Do:
- Encapsulate auth utilities (hash/verify/decode/create token).
- Encapsulate user persistence helpers and normalization.
- Encapsulate sentence correction pipeline: run agent -> parse JSON -> save sentence/mistakes.

Do not:
- Define FastAPI routes.
- Depend on FastAPI request/response objects.

### 3) `agents/` (AI layer)

Do:
- Define `description`, `instructions`, and `expected_output`.
- Return strict JSON-only output consumable by services.
- Keep instruction text concise and deterministic.

Do not:
- Access Supabase or any DB client.
- Raise HTTP-specific errors.
- Implement persistence/orchestration logic.

### 4) `supabase/` (infrastructure layer)

Do:
- Expose a singleton `get_supabase()` client for dependency injection.
- Keep environment resolution (`SUPABASE_URL`, service key aliasing) centralized.

Do not:
- Mix feature logic into client initialization.

---

## Feature flows in this repository

### Auth flow (`/v1/auth`)

1. API validates input and normalizes username.
2. Service hashes/verifies password and issues JWT session token.
3. User service reads/writes `users` in Supabase.
4. API returns `LoginResponse`/errors.

### User flow (`/v1/users`)

1. API extracts bearer token via `get_current_user_id`.
2. User service fetches user rows by id/username.
3. API maps missing rows to `404`.

### Sentence correction flow (`/v1/sentence/correct`)

1. API validates request and auth.
2. Sentence service calls `sentence_correct_agent`.
3. Service parses agent JSON and computes `has_mistakes`.
4. Service persists sentence and mistake rows in Supabase.
5. API returns `SentenceCorrectResponse`.

Note: not every feature requires an agent call (auth/user routes currently do not).

---

## Data and contract rules

- Agent output must be valid JSON with no surrounding prose.
- Service layer must tolerate malformed agent output and provide safe fallback values.
- API responses should always be serializable by schema models (`model_validate` where applicable).
- Normalize usernames as lowercase before lookup/insert.
- JWT payload must include a string `sub` (user id).

---

## Error handling rules

- `api/`: map known failures to correct HTTP codes (`400`, `401`, `404`, `409`, `500`).
- `services/`: raise domain/runtime errors with actionable messages.
- `agents/`: never assume model output is perfect; service must validate and sanitize.
- Avoid leaking sensitive secrets or full internal traces in API error details.

---

## Code style and maintenance

- Use type hints for public functions and key helpers.
- Keep functions focused and small; extract helpers for repeated logic.
- Reuse existing modules before creating new abstractions.
- Favor explicit names: `get_user_by_username`, `create_session_token`, `correct_sentence`.
- Add concise comments only where non-obvious behavior exists.

---

## Anti-patterns (forbidden)

- Calling agent directly from `api/`.
- Running Supabase queries directly from routers.
- Duplicating token parsing logic outside `api/deps.py` + `services/auth_service.py`.
- Returning non-JSON agent output and parsing it in routers.
- Mixing prompt definitions into service files.

---

## Final rule

If unsure:
- keep boundaries strict,
- keep outputs structured,
- keep orchestration in `services/`,
- keep transport concerns in `api/`.
