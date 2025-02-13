# app/routes/answers_routes.py

from flask import request, jsonify, Blueprint, current_app
from datetime import datetime
from app.utils import logger
from app.models.event import Event  # Importamos Event para filtrar por survey_id

answers = Blueprint("answer", __name__)

@answers.route('/<survey_id>/save', methods=['POST'])
def save_survey_progress(survey_id):
    try:
        data = request.json
        required_fields = ['user_id', 'employee_answers']

        if not data or not all(field in data for field in required_fields):
            logger.error("Missing fields in request body")
            return jsonify({"error": "Invalid request data"}), 400

        user_id = data['user_id']
        employee_answers = data['employee_answers']

        db = current_app.mongo_db
        if not db:
            return jsonify({"error": "Database not initialized"}), 500

        surveys_collection = db.get_collection("Surveys")
        answers_collection = db.get_collection("SurveyAnswers")

        # 1) Buscar el Event con ese survey_id (string)
        event = Event.query.filter_by(survey_id=survey_id).first()
        if not event:
            logger.error(f"Event not found for survey_id={survey_id}")
            return jsonify({"error": "Event not found"}), 404

        # 2) Obtener el tipo de encuesta
        survey_type = event.survey_type

        # 3) Validar que la encuesta exista en Mongo (opcional)
        survey = surveys_collection.find_one({"_id": survey_id})
        if not survey:
            logger.error(f"Survey {survey_id} not found in Mongo")
            return jsonify({"error": "Survey not found"}), 404

        # 4) Guardar/actualizar respuestas
        for employee_answer in employee_answers:
            employee_id = employee_answer.get('employee_id')
            answers = employee_answer.get('answers')

            if not employee_id or not answers:
                logger.error("Invalid employee answer data")
                return jsonify({"error": "Invalid employee answer data"}), 400

            existing_entry = answers_collection.find_one({
                "survey_id": survey_id,
                "user_id": user_id,
                "employee_id": employee_id
            })

            if existing_entry:
                # Update existing draft
                answers_collection.update_one(
                    {"_id": existing_entry["_id"]},
                    {
                        "$set": {
                            "answers": answers,
                            "status": "in_progress",
                            "survey_type": survey_type,  # Guardar aquí
                            "last_updated": datetime.utcnow()
                        }
                    }
                )
                logger.info(f"Updated progress for survey {survey_id}, employee {employee_id}")
            else:
                # Create new draft
                new_entry = {
                    "survey_id": survey_id,
                    "user_id": user_id,
                    "employee_id": employee_id,
                    "answers": answers,
                    "status": "in_progress",
                    "survey_type": survey_type,  # Guardar aquí
                    "created_at": datetime.now(),
                    "last_updated": datetime.now()
                }
                answers_collection.insert_one(new_entry)
                logger.info(f"Saved new progress for survey {survey_id}, employee {employee_id}")

        return jsonify({"message": "Survey progress saved successfully"}), 200
    except Exception as e:
        logger.critical(f"Error saving progress for survey {survey_id}", exc_info=e)
        return jsonify({"error": "Internal Server Error"}), 500


@answers.route('/<survey_id>/submit', methods=['POST'])
def submit_survey(survey_id):
    try:
        data = request.json
        required_fields = ['user_id', 'employee_answers']

        if not data or not all(field in data for field in required_fields):
            logger.error("Missing fields in request body")
            return jsonify({"error": "Invalid request data"}), 400

        user_id = data['user_id']
        employee_answers = data['employee_answers']

        db = current_app.mongo_db
        if not db:
            return jsonify({"error": "Database not initialized"}), 500

        answers_collection = db.get_collection("SurveyAnswers")

        # 1) Obtener el Event
        event = Event.query.filter_by(survey_id=survey_id).first()
        if not event:
            logger.error(f"Event not found for survey_id={survey_id}")
            return jsonify({"error": "Event not found"}), 404

        survey_type = event.survey_type

        for employee_answer in employee_answers:
            employee_id = employee_answer.get('employee_id')
            answers = employee_answer.get('answers')

            if not employee_id or not answers:
                logger.error("Invalid employee answer data")
                return jsonify({"error": "Invalid employee answer data"}), 400

            result = answers_collection.update_one(
                {
                    "survey_id": survey_id,
                    "user_id": user_id,
                    "employee_id": employee_id
                },
                {
                    "$set": {
                        "answers": answers,
                        "status": "completed",
                        "survey_type": survey_type,  # Guardar aquí
                        "last_updated": datetime.utcnow()
                    }
                }
            )

            if result.matched_count == 0:
                # No draft found
                new_entry = {
                    "survey_id": survey_id,
                    "user_id": user_id,
                    "employee_id": employee_id,
                    "answers": answers,
                    "status": "completed",
                    "survey_type": survey_type,  # Guardar aquí
                    "created_at": datetime.now(),
                    "last_updated": datetime.now()
                }
                answers_collection.insert_one(new_entry)
                logger.info(f"Created new submission for survey {survey_id}, employee {employee_id}")
            else:
                logger.info(f"Updated existing submission for survey {survey_id}, employee {employee_id}")

        return jsonify({"message": "Survey submitted successfully"}), 200
    except Exception as e:
        logger.critical(f"Error submitting survey {survey_id}", exc_info=e)
        return jsonify({"error": "Internal Server Error"}), 500


@answers.route('/<survey_id>/answers', methods=['GET'])
def get_survey_answers(survey_id):
    try:
        user_id = request.args.get("user_id")
        employee_id = request.args.get("employee_id")

        if not user_id:
            logger.error("user_id is required for fetching answers")
            return jsonify({"error": "user_id is required"}), 400

        db = current_app.mongo_db
        if not db:
            return jsonify({"error": "Database not initialized"}), 500

        answers_collection = db.get_collection("SurveyAnswers")
        query = {"survey_id": survey_id, "user_id": user_id}
        if employee_id:
            query["employee_id"] = employee_id

        answers_cursor = answers_collection.find(query)
        answers = [
            {
                "employee_id": doc["employee_id"],
                "answers": doc["answers"],
                "status": doc["status"],
                "survey_type": doc.get("survey_type", "Unknown"),
                "last_updated": doc["last_updated"]
            }
            for doc in answers_cursor
        ]

        if not answers:
            logger.info(f"No answers found for survey {survey_id}, user {user_id}")
            return jsonify({"error": "No answers found for the given filters"}), 404

        return jsonify({"survey_id": survey_id, "answers": answers}), 200
    except Exception as e:
        logger.critical(f"Error fetching answers for survey {survey_id}", exc_info=e)
        return jsonify({"error": "Internal Server Error"}), 500


@answers.route('/<survey_id>/answers', methods=['DELETE'])
def delete_survey_answers(survey_id):
    try:
        user_id = request.args.get("user_id")
        employee_id = request.args.get("employee_id")

        db = current_app.mongo_db
        if not db:
            return jsonify({"error": "Database not initialized"}), 500

        answers_collection = db.get_collection("SurveyAnswers")
        query = {"survey_id": survey_id}
        if user_id:
            query["user_id"] = user_id
        if employee_id:
            query["employee_id"] = employee_id

        result = answers_collection.delete_many(query)
        if result.deleted_count == 0:
            logger.info(f"No answers found to delete for survey {survey_id}")
            return jsonify({"error": "No answers found to delete"}), 404

        logger.info(f"Deleted {result.deleted_count} answers for survey {survey_id}")
        return jsonify({"message": f"Deleted {result.deleted_count} answers"}), 200
    except Exception as e:
        logger.critical(f"Error deleting answers for survey {survey_id}", exc_info=e)
        return jsonify({"error": "Internal Server Error"}), 500


@answers.route('/surveys/status', methods=['GET'])
def get_surveys_by_status():
    try:
        user_id = "employee_123"

        if not user_id:
            logger.error("user_id is required for fetching surveys by status")
            return jsonify({"error": "user_id is required"}), 400

        db = current_app.mongo_db
        if not db:
            return jsonify({"error": "Database not initialized"}), 500

        surveys_collection = db.get_collection("Surveys")
        answers_collection = db.get_collection("SurveyAnswers")

        # Fetch all surveys from Mongo
        surveys = list(surveys_collection.find())
        if not surveys:
            logger.info("No surveys found")
            return jsonify({"pending": [], "in_progress": [], "completed": []}), 200

        categorized_surveys = {
            "pending": [],
            "in_progress": [],
            "completed": []
        }

        for survey in surveys:
            survey_id = str(survey["_id"])

            question_blocks = survey.get("questionBlocks", [])
            all_questions = [q for block in question_blocks for q in block.get("questions", [])]
            total_questions = len(all_questions)

            user_answers = list(answers_collection.find({
                "survey_id": survey_id,
                "user_id": user_id
            }))

            is_completed = any(a.get("status") == "completed" for a in user_answers)
            answered_questions = sum(len(a.get("answers", [])) for a in user_answers)
            progress_percentage = (answered_questions / total_questions) * 100 if total_questions else 0

            logger.debug(f"Survey ID: {survey_id}, Progress: {progress_percentage:.2f}%, Completed: {is_completed}")

            survey_data = {
                "id": survey_id,
                "title": survey.get("title", "Untitled Survey"),
                "subtitle": survey.get("subtitle", "No description"),
                "progress": round(progress_percentage, 2),
                "assignmentDate": survey.get("deadline", ""),
                "handInDate": survey.get("handInDate", ""),
                "questions": all_questions
            }

            if is_completed:
                categorized_surveys["completed"].append(survey_data)
            elif 0 < progress_percentage < 100:
                categorized_surveys["in_progress"].append(survey_data)
            else:
                categorized_surveys["pending"].append(survey_data)

        return jsonify(categorized_surveys), 200
    except Exception as e:
        logger.critical("Error fetching surveys by status", exc_info=e)
        return jsonify({"error": "Internal Server Error"}), 500