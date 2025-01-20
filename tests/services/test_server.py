import pytest
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_pymongo import PyMongo
from app.services.server import FlaskServer
from app.config import get_config


@pytest.fixture
def db_sql():
    return SQLAlchemy()


@pytest.fixture
def db_mongo():
    return PyMongo()


def test_config_loading():
    """
    Test that the correct configuration is loaded based on the environment.
    """

    test_config = get_config("testing")
    assert test_config.SQLALCHEMY_DATABASE_URI == "mysql+pymysql://username:password@localhost/testdb"
    assert test_config.MONGO_URI == "mongodb://localhost:27017/testdb"


def test_flask_server_initialization(db_sql, db_mongo):
    """
    Test that the FlaskServer class initializes correctly with given parameters.
    """
    server = FlaskServer("test_app", db_sql=db_sql, db_mongo=db_mongo, env="testing")
    assert server.app_name == "test_app"
    assert server.db_sql == db_sql
    assert server.db_mongo == db_mongo
    assert server.env.SQLALCHEMY_DATABASE_URI == "mysql+pymysql://username:password@localhost/testdb"
    assert server.env.MONGO_URI == "mongodb://localhost:27017/testdb"


def test_create_app(db_sql, db_mongo):
    """
    Test that the `create_app` method initializes a Flask app with the correct configurations.
    """
    server = FlaskServer("test_app", db_sql=db_sql, db_mongo=db_mongo, env="testing")
    app = server.create_app()

    # Verify app instance and configurations
    assert isinstance(app, Flask)
    assert app.config["SQLALCHEMY_DATABASE_URI"] == "mysql+pymysql://username:password@localhost/testdb"
    assert app.config["MONGO_URI"] == "mongodb://localhost:27017/testdb"


def test_error_handlers():
    """
    Test that custom error handlers are set up correctly.
    """
    server = FlaskServer("test_app", env="testing")
    app = server.create_app()

    @app.route("/error")
    def trigger_error():
        raise Exception("Test error")

    client = app.test_client()

    # Test 404 error handler
    response = client.get("/nonexistent")
    assert response.status_code == 404
    assert response.json == {"error": "Resource not found"}

    # Test 500 error handler
    response = client.get("/error")
    assert response.status_code == 500
    assert response.json == {"error": "An internal error occurred"}
