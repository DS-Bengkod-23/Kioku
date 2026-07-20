from app.models.user import User


def test_health_check_returns_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_database_fixture_is_migrated_and_clean(db_session):
    assert db_session.query(User).count() == 0
