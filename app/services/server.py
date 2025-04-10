from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_pymongo import PyMongo
from app.config import get_config

class FlaskServer:
    def __init__(self, name, db_sql: SQLAlchemy = None, db_mongo: PyMongo = None, env: str = None) -> None:
        """
        Initializes the FlaskServer class with the necessary dependencies.
        
        :param name: The name of the Flask application.
        :param db_sql: (Optional) SQLAlchemy instance for relational database.
        :param db_mongo: (Optional) PyMongo instance for MongoDB.
        :param env: The environment to load configurations (e.g., 'development', 'production').
        """
        self.app_name = name
        self.db_sql = db_sql
        self.db_mongo = db_mongo
        self.env = get_config(env)
        self.blueprints = []  # List to hold blueprint instances

    def create_app(self):
        """
        Creates and configures the Flask application.
        
        :return: Configured Flask application instance.
        """
        app = Flask(self.app_name)

        # Load environment-specific configurations
        app.config.from_object(self.env)

        # Initialize SQLAlchemy if provided
        if self.db_sql:
            self.db_sql.init_app(app)

        # Initialize PyMongo if provided
        if self.db_mongo:
            self.db_mongo.init_app(app)

        # Register blueprints
        self._register_blueprints(app)

        # Setup error handling
        self._setup_error_handlers(app)

        return app

    def add_blueprint(self, blueprint, url_prefix=None):
        """
        Adds a blueprint to the Flask application with an optional URL prefix.

        :param blueprint: The blueprint to register.
        :param url_prefix: (Optional) The URL prefix for the blueprint.
        """
        self.blueprints.append((blueprint, url_prefix))

    def _register_blueprints(self, app):
        """
        Registers all added blueprints to the Flask application with their URL prefixes.

        :param app: The Flask application instance.
        """
        for blueprint, url_prefix in self.blueprints:
            app.register_blueprint(blueprint, url_prefix=url_prefix)

    def _setup_error_handlers(self, app):
        """
        Sets up custom error handlers for the application.
        """
        @app.errorhandler(404)
        def not_found_error(error):
            return {"error": "Resource not found"}, 404

        @app.errorhandler(500)
        def internal_error(error):
            return {"error": "An internal error occurred"}, 500
