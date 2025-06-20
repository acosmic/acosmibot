# tests/test_database_connection.py
import pytest
from database import Database

@pytest.fixture
def db():
    db = Database(use_test_db=True)
    yield db
    db.close_connection()

def test_database_connection(db):
    assert db.mydb.is_connected(), "Database connection failed"