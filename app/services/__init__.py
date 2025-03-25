from app.services.db_sql import SQLAlchemyDatabase
from app.services.mongo_db import Database

db_sql = SQLAlchemyDatabase()
db = db_sql.get_instance()
