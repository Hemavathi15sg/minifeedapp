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
from schemas import PostCreate, PostUpdate
from crud import create_post, read_post, read_all_posts, update_post, delete_post


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
    """Initialize test database with posts table."""
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
    
    conn.commit()
    conn.close()


def clear_test_db():
    """Clear all data from test database."""
    if os.path.exists(TEST_DB):
        conn = sqlite3.connect(TEST_DB)
        cursor = conn.cursor()
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
