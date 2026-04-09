from datetime import datetime
from models import Post
from schemas import PostCreate, PostUpdate


def create_post(conn, post_data: PostCreate) -> Post:
    """Create a new post in the database."""
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO posts (caption, image_url, created_at)
        VALUES (?, ?, ?)
        """,
        (post_data.caption, post_data.image_url, datetime.now().isoformat())
    )
    conn.commit()
    post_id = cursor.lastrowid
    
    cursor.execute("SELECT * FROM posts WHERE id = ?", (post_id,))
    row = cursor.fetchone()
    return Post.from_dict(dict(row))


def read_post(conn, post_id: int) -> Post:
    """Read a post by ID."""
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM posts WHERE id = ?", (post_id,))
    row = cursor.fetchone()
    
    if not row:
        return None
    return Post.from_dict(dict(row))


def read_all_posts(conn) -> list[Post]:
    """Read all posts."""
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM posts ORDER BY created_at DESC")
    rows = cursor.fetchall()
    return [Post.from_dict(dict(row)) for row in rows]


def update_post(conn, post_id: int, post_data: PostUpdate) -> Post:
    """Update a post by ID."""
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM posts WHERE id = ?", (post_id,))
    row = cursor.fetchone()
    if not row:
        return None
    
    current_post = Post.from_dict(dict(row))
    
    caption = post_data.caption if post_data.caption is not None else current_post.caption
    image_url = post_data.image_url if post_data.image_url is not None else current_post.image_url
    
    cursor.execute(
        """
        UPDATE posts
        SET caption = ?, image_url = ?
        WHERE id = ?
        """,
        (caption, image_url, post_id)
    )
    conn.commit()
    
    return read_post(conn, post_id)


def search_posts(conn, query: str) -> list[Post]:
    """Search posts by caption (case-insensitive)."""
    escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM posts WHERE LOWER(caption) LIKE LOWER(?) ESCAPE '\\' ORDER BY created_at DESC",
        (f"%{escaped}%",)
    )
    rows = cursor.fetchall()
    return [Post.from_dict(dict(row)) for row in rows]


def delete_post(conn, post_id: int) -> bool:
    """Delete a post by ID."""
    cursor = conn.cursor()
    cursor.execute("DELETE FROM posts WHERE id = ?", (post_id,))
    conn.commit()
    return cursor.rowcount > 0
