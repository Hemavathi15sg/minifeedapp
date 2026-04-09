---
description: FastAPI backend API for MiniFeed social feed application
applyTo: 'backend/**/*.py|api|endpoint|crud|database|schema'
---

# MiniFeed API Instructions

## Project Context
MiniFeed is a minimal social feed backend built with **FastAPI** and **SQLite**. This API handles post CRUD operations with a clean separation of concerns.

## Technology Stack (MANDATORY)
- **Framework**: FastAPI (not Flask, Django, FastAPI Starlette extensions)
- **Database**: SQLite only (posts.db)
- **Python**: 3.10+
- **Dependencies**: fastapi, uvicorn, pydantic (see requirements.txt)
- **Code Style**: Synchronous only (no async database operations)

## Folder Structure (STRICT)
```
backend/
├── main.py          # FastAPI app + endpoints
├── database.py      # SQLite connection & init
├── models.py        # Post dataclass (DB representation)
├── schemas.py       # Pydantic models (request/response)
├── crud.py          # CRUD operations
└── requirements.txt # Dependencies
```
**Do NOT create additional folders or files** beyond this structure.

## Database Requirements
- **Name**: `posts.db` (SQLite, not PostgreSQL/MongoDB)
- **Table**: `posts` with columns:
  - `id` (int, primary key, auto-increment)
  - `caption` (string, not null)
  - `image_url` (string, not null)
  - `created_at` (timestamp, default CURRENT_TIMESTAMP)

## API Endpoint Rules
### Base Path: `/posts`
- `POST /posts` → Create post (201 Created, no request body validation beyond Pydantic)
- `GET /posts` → List all posts (no pagination)
- `GET /posts/{id}` → Get single post by ID
- `PUT /posts/{id}` → Update post (partial updates allowed)
- `DELETE /posts/{id}` → Delete post (204 No Content)

**Error Handling**: Return 404 if post not found, include descriptive error messages.

## Code Organization Rules

### database.py
- Use `sqlite3.connect()` with `row_factory = sqlite3.Row`
- Provide `init_db()` function to create posts table
- Implement `get_db()` context manager for connections
- Initialize DB on app startup with `@app.on_event("startup")`

### models.py
- Use `@dataclass` for Post (not SQLAlchemy ORM)
- Include `from_dict()` classmethod for row conversion
- Include `to_dict()` method for serialization

### schemas.py
- Use `BaseModel` from Pydantic for PostCreate, PostUpdate, PostResponse
- Add field validation with `Field(..., min_length=1, description="...")`
- PostUpdate should have optional fields (allow partial updates)

### crud.py
- Implement all 4 operations: `create_post()`, `read_post()`, `read_all_posts()`, `update_post()`, `delete_post()`
- Each function takes `conn` as first parameter (no dependency injection)
- Return Post instances (convert via models.Post.from_dict())
- Use raw SQL only (no ORM)

### main.py
- Initialize `FastAPI(title="MiniFeed API", version="1.0.0")`
- All endpoints must use Pydantic schemas for request/response
- Use FastAPI status codes: `status.HTTP_201_CREATED`, `status.HTTP_404_NOT_FOUND`, etc.
- All database interactions use `with get_db() as conn:` context manager

## What NOT to Implement
- ❌ Authentication / user management
- ❌ Pagination, sorting, or filtering
- ❌ Likes, comments, or engagement features
- ❌ Async code (use synchronous DB calls)
- ❌ ORM frameworks (SQLAlchemy, Tortoise)
- ❌ Custom folder structures
- ❌ API documentation generation (Swagger auto-docs OK)
- ❌ Input validation beyond Pydantic Field definitions

## Code Example Patterns

**CORRECT - Database context usage:**
```python
with get_db() as conn:
    post = read_post(conn, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Not found")
    return post.to_dict()
```

**CORRECT - Pydantic schema with validation:**
```python
class PostCreate(BaseModel):
    caption: str = Field(..., min_length=1)
    image_url: str = Field(..., min_length=1)
```

**INCORRECT - Async DB (don't do):**
```python
async def get_posts():
    async with get_session() as session:  # ❌ NO ASYNC
```

## Testing & Verification
Run locally with:
```bash
pip install -r requirements.txt
uvicorn main:app --reload
```
API will be available at `http://localhost:8000`
Swagger docs at `http://localhost:8000/docs`

## Key Principles
1. **Simplicity First**: No complex business logic beyond CRUD
2. **Clean Separation**: Each file has one responsibility
3. **Deterministic Output**: Same input always produces same output
4. **Minimal Code**: Remove all unnecessary comments/features
5. **Strict Structure**: No deviations from folder layout