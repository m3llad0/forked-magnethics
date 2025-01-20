from flask import request, jsonify, Blueprint, current_app
from app.models import Survey
from app.utils import logger

survey = Blueprint("survey", __name__)

@survey.route("/", methods=["POST"])
def create_survey():
    try:
        survey_data = request.json

        required_fields = ["id", "title", "subtitle", "deadline", "question_ids"]

        if not all(field in survey_data for field in required_fields):
            logger.error("Missing fields in body")
            return jsonify({"error": "Missing required fields"}), 400

        db = current_app.mongo_db
        if not db:
            return jsonify({"error": "Database not initialized"}), 500

        stages_collection = db.get_collection("Stages")
        surveys_collection = db.get_collection("Surveys")

        # Create a Survey instance
        survey = Survey(
            id=survey_data["id"],
            title=survey_data["title"],
            subtitle=survey_data["subtitle"],
            deadline=survey_data["deadline"],
            question_ids=survey_data["question_ids"],
            stage_collection=stages_collection,
            survey_collection=surveys_collection,
        )

        # Fetch questions and insert survey
        survey.fetch_questions()
        survey_id = survey.insert_survey()

        return jsonify({"message": "Created new survey!", "survey_id": str(survey_id)}), 201

    except Exception as e:
        logger.critical("Error creating survey", exc_info=e)
        return jsonify({"error": "Internal Server Error"}), 500


@survey.route("/", methods=["GET"])
def get_surveys():
    try:
        db = current_app.mongo_db
        if not db:
            return jsonify({"error": "Database not initialized"}), 500

        surveys_collection = db.get_collection("Surveys")

        # Fetch all surveys
        surveys_cursor = surveys_collection.find()
        response = [survey for survey in surveys_cursor]

        if not response:
            return jsonify({"message": "No surveys found"}), 404

        return jsonify(response), 200
    except Exception as e:
        logger.critical("Error getting surveys", exc_info=e)
        return jsonify({"error": "Internal Server Error"}), 500


@survey.route("/<id>", methods=["GET"])
def get_survey(id):
    try:
        db = current_app.mongo_db
        if not db:
            return jsonify({"error": "Database not initialized"}), 500

        surveys_collection = db.get_collection("Surveys")

        # Fetch a single survey
        survey = surveys_collection.find_one({"id": id})
        if not survey:
            return jsonify({"message": "Survey not found"}), 404

        return jsonify(survey), 200
    except Exception as e:
        logger.critical("Error getting survey", exc_info=e)
        return jsonify({"error": "Internal Server Error"}), 500


@survey.route("/<id>", methods=["PUT"])
def update_survey(id):
    try:
        update_data = request.json

        if not update_data:
            logger.error("No update data provided")
            return jsonify({"error": "No update data provided"}), 400

        db = current_app.mongo_db
        if not db:
            return jsonify({"error": "Database not initialized"}), 500

        surveys_collection = db.get_collection("Surveys")

        # Update the survey
        result = surveys_collection.update_one({"id": id}, {"$set": update_data})
        if result.modified_count == 0:
            return jsonify({"message": "No data updated. Survey may not exist."}), 404

        return jsonify({"message": "Survey updated successfully."}), 200
    except Exception as e:
        logger.critical("Error updating survey", exc_info=e)
        return jsonify({"error": "Internal Server Error"}), 500


@survey.route("/<id>", methods=["DELETE"])
def delete_survey(id):
    try:
        db = current_app.mongo_db
        if not db:
            return jsonify({"error": "Database not initialized"}), 500

        surveys_collection = db.get_collection("Surveys")

        # Delete the survey
        result = surveys_collection.delete_one({"id": id})
        if result.deleted_count == 0:
            return jsonify({"message": "No data deleted. Survey may not exist."}), 404

        return jsonify({"message": "Survey deleted successfully."}), 200
    except Exception as e:
        logger.critical("Error deleting survey", exc_info=e)
        return jsonify({"error": "Internal Server Error"}), 500
