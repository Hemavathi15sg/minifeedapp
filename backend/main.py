from fastapi import FastAPI, HTTPException, status
from database import init_db, get_db
from schemas import PostCreate, PostUpdate, PostResponse
from crud import create_post, read_post, read_all_posts, update_post, delete_post

app = FastAPI(title="MiniFeed API", version="1.0.0")


@app.on_event("startup")
def startup_event():
    """Initialize database on startup."""
    init_db()


@app.post("/posts", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
def create_new_post(post: PostCreate):
    """Create a new post."""
    with get_db() as conn:
        created_post = create_post(conn, post)
        return created_post.to_dict()


@app.get("/posts", response_model=list[PostResponse])
def get_all_posts():
    """Get all posts."""
    with get_db() as conn:
        posts = read_all_posts(conn)
        return [post.to_dict() for post in posts]


@app.get("/posts/{post_id}", response_model=PostResponse)
def get_post(post_id: int):
    """Get a post by ID."""
    with get_db() as conn:
        post = read_post(conn, post_id)
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Post with id {post_id} not found"
            )
        return post.to_dict()


@app.put("/posts/{post_id}", response_model=PostResponse)
def update_post_endpoint(post_id: int, post: PostUpdate):
    """Update a post by ID."""
    with get_db() as conn:
        existing_post = read_post(conn, post_id)
        if not existing_post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Post with id {post_id} not found"
            )
        
        updated_post = update_post(conn, post_id, post)
        return updated_post.to_dict()


@app.delete("/posts/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_post_endpoint(post_id: int):
    """Delete a post by ID."""
    with get_db() as conn:
        post = read_post(conn, post_id)
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Post with id {post_id} not found"
            )
        
        delete_post(conn, post_id)
        return None
