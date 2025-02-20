# app/routes/survey_routes.py

from flask import request, jsonify, Blueprint, current_app
from bson.objectid import ObjectId
from app.utils import logger
from app.services import db

# Modelos SQL
from app.models.client import Client
from app.models.product import Product
from app.models.employee import Employee
from app.models.employee_survey_assignment import EmployeeSurveyAssignment

# Clase Survey para Mongo
from app.models.survey import Survey  # la clase con fetch_questions(), insert_survey()

# ML model o lógica para 360
from app.ml.assign_360_evaluators import assign_360_evaluators_spectral  # ejemplo

survey = Blueprint("survey", __name__)

@survey.route("/", methods=["POST"])
def create_survey():
    """
    Crea una encuesta en MongoDB (stages, scale_options, etc.)
    y asigna empleados en la tabla employee_survey_assignments.
    """
    try:
        data = request.json
        required_fields = [
            "id", "title", "subtitle", "description",
            "client_id", "product_id", "deadline", "handInDate",
            "scale_id", "question_ids"
        ]
        if not data or not all(f in data for f in required_fields):
            logger.error("Missing fields in body")
            return jsonify({"error": "Missing required fields"}), 400

        # 1. Validar DB
        mongo_db = current_app.mongo_db
        if not mongo_db:
            return jsonify({"error": "MongoDB not initialized"}), 500
        if not db:
            return jsonify({"error": "SQL DB not initialized"}), 500

        # 2. Validar Client y Product en SQL
        client = db.session.get(Client, data["client_id"])
        if not client:
            return jsonify({"error": "Client not found"}), 404

        product = db.session.get(Product, data["product_id"])
        if not product:
            return jsonify({"error": "Product not found"}), 400

        # Determinar survey_type
        p_name = product.name.lower()
        if "enex" in p_name:
            survey_type = "Enex"
        elif "360" in p_name:
            survey_type = "360"
        else:
            return jsonify({"error": "Product must contain 'ENEX' or '360'"}), 400

        # 3. Scale options en Mongo
        scale_options_coll = mongo_db.get_collection("ScaleOptions")
        scale_doc = scale_options_coll.find_one({"_id": ObjectId(data["scale_id"])})
        if not scale_doc:
            return jsonify({"error": "Invalid scale options"}), 400
        scale_options = scale_doc.get("scaleOptions", [])

        # 4. Crear Survey en Mongo
        stages_coll = mongo_db.get_collection("Stages")
        surveys_coll = mongo_db.get_collection("Surveys")

        new_survey = Survey(
            id=data["id"],
            title=data["title"],
            subtitle=data["subtitle"],
            description=data["description"],
            client_id=client.id,
            deadline=data["deadline"],
            handInDate=data["handInDate"],
            question_ids=data["question_ids"],
            scale_options=scale_options,
            stage_collection=stages_coll,
            survey_collection=surveys_coll
        )
        new_survey.fetch_questions()
        inserted_id = new_survey.insert_survey()
        logger.info(f"Survey inserted in Mongo with _id={inserted_id}")

        # 5. Asignar encuestas en SQL
        employees = db.session.query(Employee).filter_by(client_id=client.id).all()
        if not employees:
            logger.warning(f"No employees found for client {client.id}; skipping assignment.")
        else:
            if survey_type.lower() == "enex":
                # ENEX => evaluamos la compañía => target_type="company", target_employee_id=None
                for emp in employees:
                    EmployeeSurveyAssignment.create_assignment({
                        "employee_id": emp.id,
                        "survey_id": data["id"],
                        "survey_type": survey_type,
                        "target_employee_id": None,
                        "target_type": "company"
                    })

            elif survey_type.lower() == "360":

                evaluator_map = assign_360_evaluators_spectral(employees)
                
                for target_emp_id, respondent_list in evaluator_map.items():
                    for resp_id in respondent_list:
                        EmployeeSurveyAssignment.create_assignment({
                            "employee_id": resp_id,            # Quien responde
                            "survey_id": data["id"],          # La encuesta
                            "survey_type": survey_type,
                            "target_employee_id": target_emp_id,  # El evaluado
                            "target_type": "employee"
                        })

        db.session.commit()

        return jsonify({"message": "Created new survey", "survey_id": data["id"]}), 201

    except Exception as e:
        logger.critical("Error creating survey", exc_info=e)
        db.session.rollback()
        return jsonify({"error": "Internal Server Error"}), 500
