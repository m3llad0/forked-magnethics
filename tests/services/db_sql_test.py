import pytest
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from app.services.db_sql import SQLAlchemyDatabase


@pytest.fixture
def app():
    """
    Flask application fixture for testing.
    """
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"  # Use an in-memory SQLite DB for testing
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    return app


@pytest.fixture
def db_instance():
    """
    Fixture for SQLAlchemyDatabase instance.
    """
    return SQLAlchemyDatabase()


def test_init_app(app, db_instance):
    """
    Test that the SQLAlchemy instance is initialized with the Flask app.
    """
    db_instance.init_app(app)
    with app.app_context():
        assert isinstance(db_instance.db, SQLAlchemy)


def test_create_tables(app, db_instance, caplog):
    """
    Test the creation of tables.
    """
    # Define a mock model
    class User(db_instance.db.Model):
        id = db_instance.db.Column(db_instance.db.Integer, primary_key=True)
        name = db_instance.db.Column(db_instance.db.String(50))

    db_instance.init_app(app)
    db_instance.create_tables(app)

    with app.app_context():
        inspector = db_instance.db.inspect(db_instance.db.engine)
        tables = inspector.get_table_names()
        assert "user" in tables

    # Verify logging
    assert "Tables created successfully!" in caplog.text
    assert "Created tables: ['user']" in caplog.text


def test_drop_tables(app, db_instance, caplog):
    """
    Test the dropping of tables.
    """
    # Define a mock model
    class User(db_instance.db.Model):
        id = db_instance.db.Column(db_instance.db.Integer, primary_key=True)
        name = db_instance.db.Column(db_instance.db.String(50))

    db_instance.init_app(app)
    db_instance.create_tables(app)
    db_instance.drop_tables(app)

    with app.app_context():
        inspector = db_instance.db.inspect(db_instance.db.engine)
        tables = inspector.get_table_names()
        assert "user" not in tables

    # Verify logging
    assert "Tables dropped" in caplog.text


def test_test_connection(app, db_instance, caplog):
    """
    Test the database connection.
    """
    db_instance.init_app(app)
    db_instance.test_connection(app)

    # Verify successful connection logging
    assert "Database connection successful." in caplog.text


def test_test_connection_failure(app, db_instance, caplog):
    """
    Test database connection failure.
    """
    # Use an invalid database URI
    app.config["SQLALCHEMY_DATABASE_URI"] = "mysql+pymysql://invalid:invalid@localhost:3306/nonexistentdb"
    db_instance.init_app(app)

    with pytest.raises(Exception):
        db_instance.test_connection(app)

    # Verify failure logging
    assert "Database connection failed" in caplog.text
