from fastapi import FastAPI, HTTPException, status
from database import init_db, get_db
from schemas import PostCreate, PostUpdate, PostResponse, CommentCreate, CommentUpdate, CommentResponse
from crud import (
    create_post, read_post, read_all_posts, update_post, delete_post,
    create_comment, read_comment, read_comments_for_post, update_comment, delete_comment,
)

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


@app.post("/posts/{post_id}/comments", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
def create_new_comment(post_id: int, comment: CommentCreate):
    """Create a comment for a post."""
    with get_db() as conn:
        post = read_post(conn, post_id)
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Post with id {post_id} not found"
            )
        created_comment = create_comment(conn, post_id, comment)
        return created_comment.to_dict()


@app.get("/posts/{post_id}/comments", response_model=list[CommentResponse])
def get_comments(post_id: int):
    """Get all comments for a post."""
    with get_db() as conn:
        post = read_post(conn, post_id)
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Post with id {post_id} not found"
            )
        comments = read_comments_for_post(conn, post_id)
        return [c.to_dict() for c in comments]


@app.put("/posts/{post_id}/comments/{comment_id}", response_model=CommentResponse)
def update_comment_endpoint(post_id: int, comment_id: int, comment: CommentUpdate):
    """Update a comment by ID."""
    with get_db() as conn:
        post = read_post(conn, post_id)
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Post with id {post_id} not found"
            )
        existing_comment = read_comment(conn, comment_id)
        if not existing_comment or existing_comment.post_id != post_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Comment with id {comment_id} not found"
            )
        updated_comment = update_comment(conn, comment_id, comment)
        return updated_comment.to_dict()


@app.delete("/posts/{post_id}/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_comment_endpoint(post_id: int, comment_id: int):
    """Delete a comment by ID."""
    with get_db() as conn:
        post = read_post(conn, post_id)
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Post with id {post_id} not found"
            )
        existing_comment = read_comment(conn, comment_id)
        if not existing_comment or existing_comment.post_id != post_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Comment with id {comment_id} not found"
            )
        delete_comment(conn, comment_id)
        return None
