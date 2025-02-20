from app.services.server import FlaskServer
from app.services import db, db_sql, Database
from app.utils import logger
from flask_cors import CORS
from sqlalchemy import inspect
from flask import current_app
import app.models
from app.routes import stage, bp, survey, answers, scale_options, client, event, product

# Initialize the FlaskServer instance
server = FlaskServer(
    name="magnethics",
    db_sql=db,
    db_mongo=None,
    env="development"
)

server.add_blueprint(bp, url_prefix="/employee")
server.add_blueprint(stage, url_prefix="/stage")
server.add_blueprint(survey, url_prefix="/survey")
server.add_blueprint(answers, url_prefix="/answer")
server.add_blueprint(scale_options, url_prefix="/scale-options")
server.add_blueprint(client, url_prefix="/client")
server.add_blueprint(event, url_prefix="/event")
server.add_blueprint(product, url_prefix="/product")

# Create the Flask app
app = server.create_app()
CORS(app)

# Initialize MongoDB connection
mongo_db = None
try:
    db_sql.test_connection(app)
    with app.app_context():
        mongo_db = Database(url=app.config["MONGO_URI"], databaseName="Magnethics")
        mongo_db.connect()
        # Attach `mongo_db` to the Flask app context
        current_app.mongo_db = mongo_db
        db.create_all()
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        logger.info(f"Tables in the database: {tables}")
except Exception as e:
    logger.error("Failed to initialize database. Check your configuration.")
    raise e