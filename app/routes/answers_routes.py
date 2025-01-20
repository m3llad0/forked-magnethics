from flask import request, jsonify, Blueprint, current_app
from datetime import datetime
from app.utils import logger

answers = Blueprint("answer", __name__)

# Route 1: Save Survey Progress
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

        # Validate that the survey exists
        survey = surveys_collection.find_one({"_id": survey_id})
        if not survey:
            logger.error(f"Survey {survey_id} not found")
            return jsonify({"error": "Survey not found"}), 404

        for employee_answer in employee_answers:
            employee_id = employee_answer.get('employee_id')
            answers = employee_answer.get('answers')

            if not employee_id or not answers:
                logger.error("Invalid employee answer data")
                return jsonify({"error": "Invalid employee answer data"}), 400

            # Check if a draft already exists
            existing_entry = answers_collection.find_one({
                "survey_id": survey_id,
                "user_id": user_id,
                "employee_id": employee_id
            })

            if existing_entry:
                # Update the existing draft
                result = answers_collection.update_one(
                    {"_id": existing_entry["_id"]},
                    {
                        "$set": {
                            "answers": answers,
                            "status": "in_progress",
                            "last_updated": datetime.utcnow()
                        }
                    }
                )
                logger.info(f"Updated progress for survey {survey_id}, employee {employee_id}")
            else:
                # Create a new draft
                new_entry = {
                    "survey_id": survey_id,
                    "user_id": user_id,
                    "employee_id": employee_id,
                    "answers": answers,
                    "status": "in_progress",
                    "created_at": datetime.utcnow(),
                    "last_updated": datetime.utcnow()
                }
                answers_collection.insert_one(new_entry)
                logger.info(f"Saved new progress for survey {survey_id}, employee {employee_id}")

        return jsonify({"message": "Survey progress saved successfully"}), 200
    except Exception as e:
        logger.critical(f"Error saving progress for survey {survey_id}", exc_info=e)
        return jsonify({"error": "Internal Server Error"}), 500


# Route 2: Submit Survey
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

        for employee_answer in employee_answers:
            employee_id = employee_answer.get('employee_id')
            answers = employee_answer.get('answers')

            if not employee_id or not answers:
                logger.error("Invalid employee answer data")
                return jsonify({"error": "Invalid employee answer data"}), 400

            # Update the draft to mark it as completed
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
                        "last_updated": datetime.utcnow()
                    }
                }
            )

            if result.matched_count == 0:
                logger.error(f"No draft found for survey {survey_id}, employee {employee_id}")
                return jsonify({
                    "error": f"No in-progress survey found for employee {employee_id}"
                }), 404

            logger.info(f"Submitted survey {survey_id} for employee {employee_id}")

        return jsonify({"message": "Survey submitted successfully"}), 200
    except Exception as e:
        logger.critical(f"Error submitting survey {survey_id}", exc_info=e)
        return jsonify({"error": "Internal Server Error"}), 500


# Route 3: Get Survey Answers
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


# Route 4: Delete Survey Answers
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

        # Fetch all surveys
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
            survey_id = str(survey["_id"])  # Ensure survey_id is a string
            total_questions = len(survey.get("test_items", []))

            # Fetch user's answers for the survey
            user_answers = list(answers_collection.find({
                "survey_id": survey_id,
                "user_id": user_id
            }))

            if not user_answers:
                logger.info(f"No answers found for survey {survey_id} and user {user_id}")
                progress_percentage = 0
            else:
                # Calculate the number of answered questions
                answered_questions = sum(
                    len(answer.get("answers", [])) for answer in user_answers
                )
                progress_percentage = (answered_questions / total_questions) * 100 if total_questions > 0 else 0

            logger.debug(f"Survey ID: {survey_id}, Progress: {progress_percentage:.2f}%")

            # Categorize survey
            survey_data = {
                "id": survey_id,
                "title": survey.get("title", "Untitled Survey"),
                "subtitle": survey.get("subtitle", "No description"),
                "progress": round(progress_percentage, 2),
                "assignmentDate": survey.get("assignmentDate", ""),
                "handInDate": survey.get("handInDate", ""),
                "questions": survey.get("test_items", [])
            }

            if 0 < progress_percentage < 100:
                categorized_surveys["in_progress"].append(survey_data)
            elif progress_percentage == 100:
                categorized_surveys["completed"].append(survey_data)
            else:
                categorized_surveys["pending"].append(survey_data)

        return jsonify(categorized_surveys), 200
    except Exception as e:
        logger.critical("Error fetching surveys by status", exc_info=e)
        return jsonify({"error": "Internal Server Error"}), 500
