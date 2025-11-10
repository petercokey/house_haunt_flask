import pytest
from app import create_app, db
from app.models import User
from werkzeug.security import generate_password_hash

@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["WTF_CSRF_ENABLED"] = False

    with app.app_context():
        db.create_all()

        # Create a test user
        user = User(
            username="testuser",
            email="test@test.com",
            password=generate_password_hash("password"),
            role="haunter",
            credits=5
        )
        db.session.add(user)
        db.session.commit()

        yield app.test_client()

        db.drop_all()


def test_signup_and_login(client):
    # Signup new user
    res = client.post("/api/signup", json={
        "username": "newuser",
        "email": "new@test.com",
        "password": "pass123",
        "role": "haunter"
    })
    assert res.status_code == 201

    # Login with created user
    res = client.post("/api/login", json={
        "email": "new@test.com",
        "password": "pass123"
    })
    assert res.status_code == 200
    assert b"Login successful" in res.data
