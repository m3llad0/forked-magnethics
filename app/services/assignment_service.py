from io import BytesIO
import pandas as pd
from flask import current_app
from app.models import Product, Employee, EmployeeSurveyAssignment
from app.utils import logger
from app.ml import SuggestionEngine

class AssignmentService:
    def __init__(self, db):
        self.db = db

    def determine_survey_type(self, survey_doc):
        if "survey_type" in survey_doc and survey_doc["survey_type"]:
            return survey_doc["survey_type"].lower()

        product_obj = self.db.session.get(Product, survey_doc.get("product_id"))
        if not product_obj:
            raise ValueError("Product not found")

        product_name = product_obj.name.lower()
        mapping = {"enex": "enex", "360": "360"}
        for key, survey_type in mapping.items():
            if key in product_name:
                return survey_type
        raise ValueError("Unsupported survey type")

    def generate_assignment_excel(self, survey_id, client_id):
        mongo_db = current_app.mongo_db
        surveys_coll = mongo_db.get_collection("Surveys")
        survey_doc = surveys_coll.find_one({"_id": survey_id})
        if not survey_doc:
            raise ValueError("Survey not found")

        survey_type = self.determine_survey_type(survey_doc)
        employees = self.db.session.query(Employee).filter_by(client_id=client_id).all()
        if not employees:
            raise ValueError("No employees found for the client")

        suggestions_map = {}
        if survey_type == "360":
            engine = SuggestionEngine(self.db, client_id)
            suggestions_map = engine.assign_suggestions()

        employees_dict = {e.employee_number: e for e in employees}
        rows = []

        for evaluator in employees:
            suggestions = suggestions_map.get(evaluator.employee_number, [])
            for s in suggestions:
                target_num = s["employee_number"]
                relation = s["relation"]
                evaluated = employees_dict.get(target_num)
                if not evaluated:
                    continue
                rows.append({
                    "ID EVALUADO": evaluated.employee_number,
                    "NOMBRE EVALUADO": f"{evaluator.first_name} {evaluator.last_name_paternal} {evaluator.last_name_maternal or ''}".strip(),
                    "TIPO USUARIO": relation,
                    "ID EVALUADOR": evaluator.employee_number,
                    "NOMBRE EVALUADOR": f"{evaluated.first_name} {evaluated.last_name_paternal} {evaluated.last_name_maternal or ''}".strip(),
                    "survey_id": survey_id,
                    "survey_type": survey_type
                })

        df = pd.DataFrame(rows)
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Asignaciones")
        output.seek(0)
        logger.info(f"Generated assignment Excel with {len(rows)} rows for survey {survey_id}")
        return output

    def finalize_assignment(self, df):
        assignments = []

        for idx, row in df.iterrows():
            try:
                evaluator_num = row.get("ID EVALUADOR")
                evaluated_num = row.get("ID EVALUADO")
                relation = row.get("TIPO USUARIO")
                survey_id = row.get("survey_id")
                survey_type = row.get("survey_type")

                if not all([evaluator_num, evaluated_num, survey_id]):
                    logger.error(f"Missing data in row {idx}")
                    continue

                evaluator = self.db.session.query(Employee).filter_by(employee_number=evaluator_num).first()
                evaluated = self.db.session.query(Employee).filter_by(employee_number=evaluated_num).first()

                if not evaluator or not evaluated:
                    logger.error(f"Evaluator or evaluated not found in row {idx}")
                    continue

                assignment_data = {
                    "employee_id": evaluator.id,
                    "survey_id": survey_id,
                    "survey_type": survey_type,
                    "target_employee_id": evaluated.id,
                    "target_type": relation
                }
                assignment = EmployeeSurveyAssignment.create_assignment(assignment_data)
                assignments.append(assignment.to_dict())

            except Exception as inner_e:
                logger.error(f"Error processing row {idx}: {inner_e}")

        self.db.session.commit()
        return assignments