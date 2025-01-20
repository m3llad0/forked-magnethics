from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect
from sqlalchemy.sql import text
from app.utils import logger 
from flask import Flask


class SQLAlchemyDatabase:
    def __init__(self):
        """
        Initializes the SQLAlchemyDatabase class. This class is responsible
        for creating and managing the SQLAlchemy instance.
        """
        self.db = SQLAlchemy()

    def init_app(self, app):
        """
        Binds the SQLAlchemy instance to the given Flask app.

        :param app: Flask application instance.
        """
        self.db.init_app(app)

    def create_tables(self, app: Flask):
        """
        Creates all tables defined in the SQLAlchemy models and logs the created tables.

        :param app: Flask application instance.
        """
        try:
            with app.app_context():
                self.db.create_all()  # Create all tables
                logger.info("Tables created successfully!")

                # Inspect and log the created tables
                inspector = inspect(self.db.engine)
                tables = inspector.get_table_names()
                if tables:
                    logger.info(f"Created tables: {tables}")
                else:
                    logger.warning("No tables were created. Check your models and configuration.")
        except Exception as e:
            logger.error(f"Failed to create tables: {e}")
            

    def drop_tables(self, app: Flask):
        """
        Drops all tables defined in the SQLAlchemy models.

        :param app: Flask application instance.
        """
        try:
            with app.app_context():
                self.db.drop_all()
                logger.info("Tables dropped")
        except Exception as e:
            logger.error(f"Failed to drop tables {e}")

    def get_instance(self):
        """
        Returns the SQLAlchemy instance for direct use.

        :return: SQLAlchemy instance.
        """
        return self.db

    def test_connection(self, app: Flask):
        """
        Tests the connection to the database by executing a simple query.

        :param app: Flask application instance.
        :raises Exception: If the connection test fails.
        """
        with app.app_context():
            try:
                self.db.session.execute(text("SELECT 1"))
                logger.info("Database connection successful.")
            except Exception as e:
                logger.error(f"Database connection failed: {e}")
                raise e
            