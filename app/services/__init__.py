from app.services.db_sql import SQLAlchemyDatabase
from app.services.mongo_db import Database
# from app.services.survey_service import SurveyService
# from app.services.assignment_service import AssignmentService

db_sql = SQLAlchemyDatabase()
db = db_sql.get_instance()
