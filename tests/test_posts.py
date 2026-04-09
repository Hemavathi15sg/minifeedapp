import pytest
import sqlite3
import os
from datetime import datetime
from contextlib import contextmanager
from fastapi.testclient import TestClient

# Import the app and db utilities
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from main import app
from models import Post
from schemas import PostCreate, PostUpdate, CommentCreate, CommentUpdate
from crud import (
    create_post, read_post, read_all_posts, update_post, delete_post,
    create_comment, read_comment, read_comments_for_post, update_comment, delete_comment,
)


# Test database setup
TEST_DB = "test_posts.db"


@contextmanager
def get_test_db():
    """Context manager for test database connections."""
    conn = sqlite3.connect(TEST_DB)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_test_db():
    """Initialize test database with posts and comments tables."""
    conn = sqlite3.connect(TEST_DB)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            caption TEXT NOT NULL,
            image_url TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER NOT NULL,
            body TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE
        )
    """)
    
    conn.commit()
    conn.close()


def clear_test_db():
    """Clear all data from test database."""
    if os.path.exists(TEST_DB):
        conn = sqlite3.connect(TEST_DB)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM comments")
        cursor.execute("DELETE FROM posts")
        conn.commit()
        conn.close()


def drop_test_db():
    """Drop test database."""
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)


@pytest.fixture(autouse=True)
def setup_teardown():
    """Setup and teardown for each test."""
    # Setup
    init_test_db()
    clear_test_db()
    
    # Patch the database module to use test database
    import database
    original_db_url = database.DATABASE_URL
    database.DATABASE_URL = TEST_DB
    
    yield
    
    # Teardown
    database.DATABASE_URL = original_db_url
    clear_test_db()


@pytest.fixture
def client():
    """Return FastAPI TestClient."""
    return TestClient(app)


class TestCreatePost:
    """Tests for POST /posts endpoint."""
    
    def test_create_post_success(self, client):
        """Test creating a post successfully."""
        payload = {
            "caption": "My first post",
            "image_url": "https://example.com/image.jpg"
        }
        response = client.post("/posts", json=payload)
        
        assert response.status_code == 201
        data = response.json()
        assert data["caption"] == "My first post"
        assert data["image_url"] == "https://example.com/image.jpg"
        assert data["id"] is not None
        assert data["created_at"] is not None
    
    def test_create_post_with_empty_caption(self, client):
        """Test creating a post with empty caption fails."""
        payload = {
            "caption": "",
            "image_url": "https://example.com/image.jpg"
        }
        response = client.post("/posts", json=payload)
        
        assert response.status_code == 422
    
    def test_create_post_with_empty_image_url(self, client):
        """Test creating a post with empty image_url fails."""
        payload = {
            "caption": "My post",
            "image_url": ""
        }
        response = client.post("/posts", json=payload)
        
        assert response.status_code == 422
    
    def test_create_post_missing_caption(self, client):
        """Test creating a post without caption fails."""
        payload = {
            "image_url": "https://example.com/image.jpg"
        }
        response = client.post("/posts", json=payload)
        
        assert response.status_code == 422
    
    def test_create_post_missing_image_url(self, client):
        """Test creating a post without image_url fails."""
        payload = {
            "caption": "My post"
        }
        response = client.post("/posts", json=payload)
        
        assert response.status_code == 422
    
    def test_create_multiple_posts(self, client):
        """Test creating multiple posts."""
        payloads = [
            {"caption": "Post 1", "image_url": "https://example.com/1.jpg"},
            {"caption": "Post 2", "image_url": "https://example.com/2.jpg"},
            {"caption": "Post 3", "image_url": "https://example.com/3.jpg"}
        ]
        
        for payload in payloads:
            response = client.post("/posts", json=payload)
            assert response.status_code == 201
        
        # Verify all posts were created
        with get_test_db() as conn:
            posts = read_all_posts(conn)
            assert len(posts) == 3


class TestReadPost:
    """Tests for GET /posts/{id} endpoint."""
    
    def test_read_post_success(self, client):
        """Test reading a post by ID successfully."""
        # Create a post first
        with get_test_db() as conn:
            post_data = PostCreate(
                caption="Test post",
                image_url="https://example.com/test.jpg"
            )
            created = create_post(conn, post_data)
            post_id = created.id
        
        # Read the post
        response = client.get(f"/posts/{post_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == post_id
        assert data["caption"] == "Test post"
        assert data["image_url"] == "https://example.com/test.jpg"
    
    def test_read_post_not_found(self, client):
        """Test reading a non-existent post."""
        response = client.get("/posts/999")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    def test_read_post_invalid_id(self, client):
        """Test reading a post with invalid ID format."""
        response = client.get("/posts/abc")
        
        assert response.status_code == 422


class TestReadAllPosts:
    """Tests for GET /posts endpoint."""
    
    def test_read_all_posts_empty(self, client):
        """Test reading all posts when database is empty."""
        response = client.get("/posts")
        
        assert response.status_code == 200
        data = response.json()
        assert data == []
    
    def test_read_all_posts_success(self, client):
        """Test reading all posts successfully."""
        # Create some posts
        payloads = [
            {"caption": "Post 1", "image_url": "https://example.com/1.jpg"},
            {"caption": "Post 2", "image_url": "https://example.com/2.jpg"},
            {"caption": "Post 3", "image_url": "https://example.com/3.jpg"}
        ]
        
        for payload in payloads:
            client.post("/posts", json=payload)
        
        # Read all posts
        response = client.get("/posts")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        
        # Verify posts are in descending order by created_at
        for i in range(len(data) - 1):
            assert data[i]["created_at"] >= data[i+1]["created_at"]
    
    def test_read_all_posts_response_format(self, client):
        """Test that all posts have required fields."""
        # Create a post
        payload = {"caption": "Test", "image_url": "https://example.com/test.jpg"}
        client.post("/posts", json=payload)
        
        response = client.get("/posts")
        data = response.json()
        
        assert len(data) == 1
        post = data[0]
        assert "id" in post
        assert "caption" in post
        assert "image_url" in post
        assert "created_at" in post


class TestUpdatePost:
    """Tests for PUT /posts/{id} endpoint."""
    
    def test_update_post_caption(self, client):
        """Test updating only the caption of a post."""
        # Create a post
        with get_test_db() as conn:
            post_data = PostCreate(
                caption="Original caption",
                image_url="https://example.com/original.jpg"
            )
            created = create_post(conn, post_data)
            post_id = created.id
        
        # Update caption
        payload = {"caption": "Updated caption"}
        response = client.put(f"/posts/{post_id}", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == post_id
        assert data["caption"] == "Updated caption"
        assert data["image_url"] == "https://example.com/original.jpg"
    
    def test_update_post_image_url(self, client):
        """Test updating only the image_url of a post."""
        # Create a post
        with get_test_db() as conn:
            post_data = PostCreate(
                caption="Test caption",
                image_url="https://example.com/original.jpg"
            )
            created = create_post(conn, post_data)
            post_id = created.id
        
        # Update image_url
        payload = {"image_url": "https://example.com/updated.jpg"}
        response = client.put(f"/posts/{post_id}", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == post_id
        assert data["caption"] == "Test caption"
        assert data["image_url"] == "https://example.com/updated.jpg"
    
    def test_update_post_both_fields(self, client):
        """Test updating both caption and image_url."""
        # Create a post
        with get_test_db() as conn:
            post_data = PostCreate(
                caption="Original caption",
                image_url="https://example.com/original.jpg"
            )
            created = create_post(conn, post_data)
            post_id = created.id
        
        # Update both fields
        payload = {
            "caption": "Updated caption",
            "image_url": "https://example.com/updated.jpg"
        }
        response = client.put(f"/posts/{post_id}", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["caption"] == "Updated caption"
        assert data["image_url"] == "https://example.com/updated.jpg"
    
    def test_update_post_not_found(self, client):
        """Test updating a non-existent post."""
        payload = {"caption": "Updated"}
        response = client.put("/posts/999", json=payload)
        
        assert response.status_code == 404
    
    def test_update_post_empty_caption(self, client):
        """Test updating caption to empty string is allowed."""
        # Create a post
        with get_test_db() as conn:
            post_data = PostCreate(
                caption="Original",
                image_url="https://example.com/test.jpg"
            )
            created = create_post(conn, post_data)
            post_id = created.id
        
        # Update with empty caption (optional field)
        payload = {"caption": None}
        response = client.put(f"/posts/{post_id}", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["caption"] == "Original"  # Should remain unchanged
    
    def test_update_post_invalid_id(self, client):
        """Test updating a post with invalid ID format."""
        payload = {"caption": "Updated"}
        response = client.put("/posts/abc", json=payload)
        
        assert response.status_code == 422


class TestDeletePost:
    """Tests for DELETE /posts/{id} endpoint."""
    
    def test_delete_post_success(self, client):
        """Test deleting a post successfully."""
        # Create a post
        with get_test_db() as conn:
            post_data = PostCreate(
                caption="Test post",
                image_url="https://example.com/test.jpg"
            )
            created = create_post(conn, post_data)
            post_id = created.id
        
        # Delete the post
        response = client.delete(f"/posts/{post_id}")
        
        assert response.status_code == 204
        
        # Verify post is deleted
        with get_test_db() as conn:
            post = read_post(conn, post_id)
            assert post is None
    
    def test_delete_post_not_found(self, client):
        """Test deleting a non-existent post."""
        response = client.delete("/posts/999")
        
        assert response.status_code == 404
    
    def test_delete_post_invalid_id(self, client):
        """Test deleting a post with invalid ID format."""
        response = client.delete("/posts/abc")
        
        assert response.status_code == 422
    
    def test_delete_post_idempotency(self, client):
        """Test that deleting the same post twice returns 404 on second attempt."""
        # Create a post
        with get_test_db() as conn:
            post_data = PostCreate(
                caption="Test",
                image_url="https://example.com/test.jpg"
            )
            created = create_post(conn, post_data)
            post_id = created.id
        
        # Delete the post
        response1 = client.delete(f"/posts/{post_id}")
        assert response1.status_code == 204
        
        # Try to delete again
        response2 = client.delete(f"/posts/{post_id}")
        assert response2.status_code == 404


class TestCRUDIntegration:
    """Integration tests for CRUD operations."""
    
    def test_complete_crud_workflow(self, client):
        """Test a complete CRUD workflow."""
        # CREATE
        create_payload = {
            "caption": "Integration test post",
            "image_url": "https://example.com/integration.jpg"
        }
        create_response = client.post("/posts", json=create_payload)
        assert create_response.status_code == 201
        post_id = create_response.json()["id"]
        
        # READ (single)
        read_response = client.get(f"/posts/{post_id}")
        assert read_response.status_code == 200
        assert read_response.json()["caption"] == "Integration test post"
        
        # UPDATE
        update_payload = {"caption": "Updated integration test post"}
        update_response = client.put(f"/posts/{post_id}", json=update_payload)
        assert update_response.status_code == 200
        assert update_response.json()["caption"] == "Updated integration test post"
        
        # READ ALL
        read_all_response = client.get("/posts")
        assert read_all_response.status_code == 200
        assert len(read_all_response.json()) >= 1
        
        # DELETE
        delete_response = client.delete(f"/posts/{post_id}")
        assert delete_response.status_code == 204
        
        # Verify deletion
        read_after_delete = client.get(f"/posts/{post_id}")
        assert read_after_delete.status_code == 404
    
    def test_multiple_posts_deletion(self, client):
        """Test creating and deleting multiple posts."""
        post_ids = []
        
        # Create multiple posts
        for i in range(3):
            payload = {
                "caption": f"Post {i}",
                "image_url": f"https://example.com/{i}.jpg"
            }
            response = client.post("/posts", json=payload)
            post_ids.append(response.json()["id"])
        
        # Verify all created
        response = client.get("/posts")
        assert len(response.json()) == 3
        
        # Delete all
        for post_id in post_ids:
            response = client.delete(f"/posts/{post_id}")
            assert response.status_code == 204
        
        # Verify all deleted
        response = client.get("/posts")
        assert len(response.json()) == 0


class TestPostResponseFormat:
    """Tests for response format and data types."""
    
    def test_created_at_is_iso_format(self, client):
        """Test that created_at is returned in ISO format."""
        payload = {
            "caption": "Test",
            "image_url": "https://example.com/test.jpg"
        }
        response = client.post("/posts", json=payload)
        created_at = response.json()["created_at"]
        
        # Verify it's valid ISO format
        try:
            datetime.fromisoformat(created_at)
        except ValueError:
            pytest.fail(f"created_at is not in ISO format: {created_at}")
    
    def test_post_id_is_integer(self, client):
        """Test that post ID is returned as integer."""
        payload = {
            "caption": "Test",
            "image_url": "https://example.com/test.jpg"
        }
        response = client.post("/posts", json=payload)
        post_id = response.json()["id"]
        
        assert isinstance(post_id, int)
        assert post_id > 0
    
    def test_all_fields_present_in_response(self, client):
        """Test that all required fields are present in response."""
        payload = {
            "caption": "Test",
            "image_url": "https://example.com/test.jpg"
        }
        response = client.post("/posts", json=payload)
        data = response.json()
        
        required_fields = ["id", "caption", "image_url", "created_at"]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"


class TestCreateComment:
    """Tests for POST /posts/{post_id}/comments endpoint."""

    def _create_post(self, client):
        payload = {"caption": "Post for comments", "image_url": "https://example.com/img.jpg"}
        response = client.post("/posts", json=payload)
        return response.json()["id"]

    def test_create_comment_success(self, client):
        """Test creating a comment successfully."""
        post_id = self._create_post(client)
        response = client.post(f"/posts/{post_id}/comments", json={"body": "Nice post!"})
        assert response.status_code == 201
        data = response.json()
        assert data["body"] == "Nice post!"
        assert data["post_id"] == post_id
        assert data["id"] is not None
        assert data["created_at"] is not None

    def test_create_comment_empty_body(self, client):
        """Test creating a comment with empty body fails."""
        post_id = self._create_post(client)
        response = client.post(f"/posts/{post_id}/comments", json={"body": ""})
        assert response.status_code == 422

    def test_create_comment_missing_body(self, client):
        """Test creating a comment without body fails."""
        post_id = self._create_post(client)
        response = client.post(f"/posts/{post_id}/comments", json={})
        assert response.status_code == 422

    def test_create_comment_post_not_found(self, client):
        """Test creating a comment for a non-existent post returns 404."""
        response = client.post("/posts/999/comments", json={"body": "Hello"})
        assert response.status_code == 404


class TestReadComments:
    """Tests for GET /posts/{post_id}/comments endpoint."""

    def _create_post(self, client):
        payload = {"caption": "Post for comments", "image_url": "https://example.com/img.jpg"}
        return client.post("/posts", json=payload).json()["id"]

    def test_get_comments_empty(self, client):
        """Test getting comments when none exist."""
        post_id = self._create_post(client)
        response = client.get(f"/posts/{post_id}/comments")
        assert response.status_code == 200
        assert response.json() == []

    def test_get_comments_success(self, client):
        """Test getting comments for a post."""
        post_id = self._create_post(client)
        client.post(f"/posts/{post_id}/comments", json={"body": "First comment"})
        client.post(f"/posts/{post_id}/comments", json={"body": "Second comment"})
        response = client.get(f"/posts/{post_id}/comments")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["body"] == "First comment"
        assert data[1]["body"] == "Second comment"

    def test_get_comments_post_not_found(self, client):
        """Test getting comments for a non-existent post returns 404."""
        response = client.get("/posts/999/comments")
        assert response.status_code == 404

    def test_comment_response_fields(self, client):
        """Test that comment response has all required fields."""
        post_id = self._create_post(client)
        client.post(f"/posts/{post_id}/comments", json={"body": "A comment"})
        response = client.get(f"/posts/{post_id}/comments")
        comment = response.json()[0]
        for field in ["id", "post_id", "body", "created_at"]:
            assert field in comment, f"Missing field: {field}"


class TestUpdateComment:
    """Tests for PUT /posts/{post_id}/comments/{comment_id} endpoint."""

    def _create_post_and_comment(self, client):
        post_id = client.post("/posts", json={"caption": "p", "image_url": "https://example.com/i.jpg"}).json()["id"]
        comment_id = client.post(f"/posts/{post_id}/comments", json={"body": "Original"}).json()["id"]
        return post_id, comment_id

    def test_update_comment_success(self, client):
        """Test updating a comment successfully."""
        post_id, comment_id = self._create_post_and_comment(client)
        response = client.put(f"/posts/{post_id}/comments/{comment_id}", json={"body": "Updated"})
        assert response.status_code == 200
        assert response.json()["body"] == "Updated"

    def test_update_comment_not_found(self, client):
        """Test updating a non-existent comment returns 404."""
        post_id = client.post("/posts", json={"caption": "p", "image_url": "https://example.com/i.jpg"}).json()["id"]
        response = client.put(f"/posts/{post_id}/comments/999", json={"body": "x"})
        assert response.status_code == 404

    def test_update_comment_post_not_found(self, client):
        """Test updating a comment on a non-existent post returns 404."""
        response = client.put("/posts/999/comments/1", json={"body": "x"})
        assert response.status_code == 404

    def test_update_comment_null_body_keeps_original(self, client):
        """Test that null body update keeps original value."""
        post_id, comment_id = self._create_post_and_comment(client)
        response = client.put(f"/posts/{post_id}/comments/{comment_id}", json={"body": None})
        assert response.status_code == 200
        assert response.json()["body"] == "Original"


class TestDeleteComment:
    """Tests for DELETE /posts/{post_id}/comments/{comment_id} endpoint."""

    def _create_post_and_comment(self, client):
        post_id = client.post("/posts", json={"caption": "p", "image_url": "https://example.com/i.jpg"}).json()["id"]
        comment_id = client.post(f"/posts/{post_id}/comments", json={"body": "To delete"}).json()["id"]
        return post_id, comment_id

    def test_delete_comment_success(self, client):
        """Test deleting a comment successfully."""
        post_id, comment_id = self._create_post_and_comment(client)
        response = client.delete(f"/posts/{post_id}/comments/{comment_id}")
        assert response.status_code == 204
        # Verify it's gone
        comments = client.get(f"/posts/{post_id}/comments").json()
        assert all(c["id"] != comment_id for c in comments)

    def test_delete_comment_not_found(self, client):
        """Test deleting a non-existent comment returns 404."""
        post_id = client.post("/posts", json={"caption": "p", "image_url": "https://example.com/i.jpg"}).json()["id"]
        response = client.delete(f"/posts/{post_id}/comments/999")
        assert response.status_code == 404

    def test_delete_comment_post_not_found(self, client):
        """Test deleting a comment on a non-existent post returns 404."""
        response = client.delete("/posts/999/comments/1")
        assert response.status_code == 404

    def test_delete_comment_idempotency(self, client):
        """Test that deleting the same comment twice returns 404 on second attempt."""
        post_id, comment_id = self._create_post_and_comment(client)
        client.delete(f"/posts/{post_id}/comments/{comment_id}")
        response = client.delete(f"/posts/{post_id}/comments/{comment_id}")
        assert response.status_code == 404

