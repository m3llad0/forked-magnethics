from flask import request, jsonify, Blueprint, current_app, g
from datetime import datetime
from app.utils import logger
from app.services import db
from app.models.employee_survey_assignment import EmployeeSurveyAssignment
from app.middleware import token_required  # Your custom token decorator

answers = Blueprint("answer", __name__)

# Route 1: Save Survey Progress
@answers.route('/<survey_id>/save', methods=['POST'])
@token_required()
def save_survey_progress(survey_id):
    """
    Saves survey progress (status = "in_progress") in 'SurveyAnswers' (Mongo).
    The employee_id is retrieved from the token (g.user_id).
    
    This function is designed to work with both ENEX and 360 surveys.
    The uniqueness of the answer document is determined by the combination
    of survey_id, employee_id, target_employee_id (if any), and target_type.
    """
    try:
        data = request.json
        if not data or "employee_answers" not in data:
            logger.error("Missing 'employee_answers' in request body")
            return jsonify({"error": "Invalid request data"}), 400

        # Retrieve employee_id from the token
        employee_id = g.user_id

        employee_answers = data["employee_answers"]

        mongo_db = current_app.mongo_db
        if not mongo_db:
            return jsonify({"error": "MongoDB not initialized"}), 500

        surveys_coll = mongo_db.get_collection("Surveys")
        answers_coll = mongo_db.get_collection("SurveyAnswers")

        # Validate survey exists in Mongo
        survey_doc = surveys_coll.find_one({"_id": survey_id})
        if not survey_doc:
            logger.error(f"Survey {survey_id} not found in Mongo")
            return jsonify({"error": "Survey not found"}), 404

        # Process each block of answers; any provided employee_id is overridden by token's id.
        for emp_ans in employee_answers:
            answers_list = emp_ans.get('answers')
            if answers_list is None:
                logger.error("Missing 'answers' in one of the employee answers")
                return jsonify({"error": "Invalid employee answer data"}), 400

            # Optional: target_employee_id (for 360 surveys) and target_type
            target_employee_id = emp_ans.get('target_employee_id')
            target_type = emp_ans.get('target_type')

            # Verify assignment in SQL using token employee_id
            query = db.session.query(EmployeeSurveyAssignment).filter_by(
                employee_id=employee_id,
                survey_id=survey_id
            )
            if target_employee_id:
                query = query.filter_by(target_employee_id=target_employee_id)
            if target_type:
                query = query.filter_by(target_type=target_type)

            assignments = query.all()
            if not assignments:
                logger.error(f"No assignment for employee={employee_id}, survey={survey_id}")
                return jsonify({
                    "error": f"Employee {employee_id} not assigned to survey {survey_id}"
                }), 403

            if len(assignments) > 1:
                logger.error(
                    f"Ambiguous assignment for employee={employee_id}, survey_id={survey_id} (multiple targets)."
                )
                return jsonify({
                    "error": "Ambiguous assignment. Multiple matches found for this employee and survey."
                }), 409

            assignment = assignments[0]
            final_target_emp = assignment.target_employee_id
            final_target_type = assignment.target_type

            # Save or update the draft in SurveyAnswers
            existing_doc = answers_coll.find_one({
                "survey_id": survey_id,
                "employee_id": employee_id,
                "target_employee_id": final_target_emp,
                "target_type": final_target_type
            })

            current_time = datetime.utcnow()
            if existing_doc:
                answers_coll.update_one(
                    {"_id": existing_doc["_id"]},
                    {
                        "$set": {
                            "answers": answers_list,
                            "status": "in_progress",
                            "last_updated": current_time
                        }
                    }
                )
                logger.info(f"Updated in_progress for survey={survey_id}, employee={employee_id}, target={final_target_emp}")
            else:
                new_doc = {
                    "survey_id": survey_id,
                    "employee_id": employee_id,
                    "target_employee_id": final_target_emp,
                    "target_type": final_target_type,
                    "answers": answers_list,
                    "status": "in_progress",
                    "created_at": current_time,
                    "last_updated": current_time
                }
                answers_coll.insert_one(new_doc)
                logger.info(f"Saved new progress for survey={survey_id}, employee={employee_id}, target={final_target_emp}")

        return jsonify({"message": "Survey progress saved successfully"}), 200

    except Exception as e:
        logger.critical(f"Error saving progress for survey {survey_id}", exc_info=e)
        return jsonify({"error": "Internal Server Error"}), 500

@answers.route('/<survey_id>/submit', methods=['POST'])
@token_required()
def submit_survey(survey_id):
    """
    Marks the survey as 'completed' in 'SurveyAnswers' (Mongo).
    The employee_id is retrieved from the token (g.user_id).

    This route handles both ENEX and 360 surveys using the assignment
    (employee_id, survey_id, target_employee_id, target_type) to uniquely update/insert.
    """
    try:
        data = request.json
        if not data or "employee_answers" not in data:
            logger.error("Missing 'employee_answers' in request body")
            return jsonify({"error": "Invalid request data"}), 400

        employee_id = g.user_id
        employee_answers = data["employee_answers"]

        mongo_db = current_app.mongo_db
        if not mongo_db:
            return jsonify({"error": "MongoDB not initialized"}), 500

        surveys_coll = mongo_db.get_collection("Surveys")
        answers_coll = mongo_db.get_collection("SurveyAnswers")

        survey_doc = surveys_coll.find_one({"_id": survey_id})
        if not survey_doc:
            logger.error(f"Survey {survey_id} not found in Mongo")
            return jsonify({"error": "Survey not found"}), 404

        for emp_ans in employee_answers:
            answers_list = emp_ans.get('answers')
            if answers_list is None:
                logger.error("Missing 'answers' in one of the employee answers")
                return jsonify({"error": "Invalid employee answer data"}), 400

            target_employee_id = emp_ans.get('target_employee_id')
            target_type = emp_ans.get('target_type')

            query = db.session.query(EmployeeSurveyAssignment).filter_by(
                employee_id=employee_id,
                survey_id=survey_id
            )
            if target_employee_id:
                query = query.filter_by(target_employee_id=target_employee_id)
            if target_type:
                query = query.filter_by(target_type=target_type)

            assignments = query.all()
            if not assignments:
                logger.error(f"No assignment for employee={employee_id}, survey={survey_id}")
                return jsonify({
                    "error": f"Employee {employee_id} not assigned to survey {survey_id}"
                }), 403

            if len(assignments) > 1:
                logger.error(
                    f"Ambiguous assignment for employee={employee_id}, survey={survey_id} (multiple targets)."
                )
                return jsonify({
                    "error": "Ambiguous assignment. Multiple matches found for this employee and survey."
                }), 409

            assignment = assignments[0]
            final_target_emp = assignment.target_employee_id
            final_target_type = assignment.target_type

            current_time = datetime.utcnow()
            filter_doc = {
                "survey_id": survey_id,
                "employee_id": employee_id,
                "target_employee_id": final_target_emp,
                "target_type": final_target_type
            }
            result = answers_coll.update_one(
                filter_doc,
                {
                    "$set": {
                        "answers": answers_list,
                        "status": "completed",
                        "last_updated": current_time
                    }
                }
            )
            if result.matched_count == 0:
                new_doc = {
                    "survey_id": survey_id,
                    "employee_id": employee_id,
                    "target_employee_id": final_target_emp,
                    "target_type": final_target_type,
                    "answers": answers_list,
                    "status": "completed",
                    "created_at": current_time,
                    "last_updated": current_time
                }
                answers_coll.insert_one(new_doc)
                logger.info(f"Created new submission for survey={survey_id}, employee={employee_id}, target={final_target_emp}")
            else:
                logger.info(f"Updated existing submission for survey={survey_id}, employee={employee_id}, target={final_target_emp}")

        return jsonify({"message": "Survey submitted successfully"}), 200

    except Exception as e:
        logger.critical(f"Error submitting survey {survey_id}", exc_info=e)
        return jsonify({"error": "Internal Server Error"}), 500

# Route 3: Get Survey Answers
@answers.route('/<survey_id>/answers', methods=['GET'])
@token_required()
def get_survey_answers(survey_id):
    """
    Retrieves survey answers from SurveyAnswers.
    The employee_id is extracted from the token (g.user_id).
    Optional filters (target_employee_id and target_type) may still be provided via query parameters.
    """
    try:
        employee_id = g.user_id
        target_employee_id = request.args.get("target_employee_id")
        target_type = request.args.get("target_type")

        mongo_db = current_app.mongo_db
        if not mongo_db:
            return jsonify({"error": "Database not initialized"}), 500

        answers_coll = mongo_db.get_collection("SurveyAnswers")
        query = {"survey_id": survey_id, "employee_id": employee_id}
        if target_employee_id:
            query["target_employee_id"] = target_employee_id
        if target_type:
            query["target_type"] = target_type

        docs = answers_coll.find(query)
        result = []
        for doc in docs:
            result.append({
                "employee_id": doc.get("employee_id"),
                "target_employee_id": doc.get("target_employee_id"),
                "target_type": doc.get("target_type"),
                "answers": doc.get("answers", []),
                "status": doc.get("status"),
                "last_updated": doc.get("last_updated")
            })

        if not result:
            logger.info(f"No answers found for survey {survey_id} and employee {employee_id}")
            return jsonify({"error": "No answers found for the given filters"}), 404

        return jsonify({"survey_id": survey_id, "answers": result}), 200

    except Exception as e:
        logger.critical(f"Error fetching answers for survey {survey_id}", exc_info=e)
        return jsonify({"error": "Internal Server Error"}), 500

# Route 4: Delete Survey Answers
@answers.route('/<survey_id>/answers', methods=['DELETE'])
@token_required()
def delete_survey_answers(survey_id):
    """
    Deletes survey answers from SurveyAnswers.
    The employee_id is extracted from the token (g.user_id).
    Optional filters (target_employee_id and target_type) may still be provided via query parameters.
    """
    try:
        employee_id = g.user_id
        target_employee_id = request.args.get("target_employee_id")
        target_type = request.args.get("target_type")

        mongo_db = current_app.mongo_db
        if not mongo_db:
            return jsonify({"error": "Database not initialized"}), 500

        answers_coll = mongo_db.get_collection("SurveyAnswers")
        query = {"survey_id": survey_id, "employee_id": employee_id}
        if target_employee_id:
            query["target_employee_id"] = target_employee_id
        if target_type:
            query["target_type"] = target_type

        result = answers_coll.delete_many(query)
        if result.deleted_count == 0:
            logger.info(f"No answers found to delete for survey {survey_id} and employee {employee_id}")
            return jsonify({"error": "No answers found to delete"}), 404

        logger.info(f"Deleted {result.deleted_count} answers for survey {survey_id}")
        return jsonify({"message": f"Deleted {result.deleted_count} answers"}), 200

    except Exception as e:
        logger.critical(f"Error deleting answers for survey {survey_id}", exc_info=e)
        return jsonify({"error": "Internal Server Error"}), 500

# Route 5: Get Surveys by Status
@answers.route('/surveys/status', methods=['GET'])
@token_required()
def get_surveys_by_status():
    """
    Categorizes surveys (pending, in_progress, completed) for the authenticated user.
    The employee_id is retrieved from the token (g.user_id).
    """
    try:
        employee_id = g.user_id

        mongo_db = current_app.mongo_db
        if not mongo_db:
            return jsonify({"error": "Database not initialized"}), 500

        surveys_coll = mongo_db.get_collection("Surveys")
        answers_coll = mongo_db.get_collection("SurveyAnswers")

        all_surveys = list(surveys_coll.find())
        if not all_surveys:
            logger.info("No surveys found")
            return jsonify({"pending": [], "in_progress": [], "completed": []}), 200

        categorized = {
            "pending": [],
            "in_progress": [],
            "completed": []
        }

        for survey_doc in all_surveys:
            sid = str(survey_doc["_id"])

            # Look for questions either in "questionBlocks" or "questions"
            blocks = survey_doc.get("questionBlocks")
            if not blocks:
                blocks = survey_doc.get("questions", [])

            all_questions = []
            for block in blocks:
                all_questions.extend(block.get("questions", []))
            total_questions = len(all_questions)

            if total_questions == 0:
                logger.warning(f"Survey {sid} has no questions defined.")
                survey_data = _build_survey_data(sid, survey_doc, 0)
                categorized["pending"].append(survey_data)
                continue

            # Fetch assignments from SQL for this survey and user
            assignments = (db.session.query(EmployeeSurveyAssignment)
                           .filter_by(employee_id=employee_id, survey_id=sid)
                           .all())
            if not assignments:
                continue

            assignment_progresses = []
            assignment_completions = []
            for assignment in assignments:
                answered_ids = set()
                filter_doc = {
                    "survey_id": sid,
                    "employee_id": employee_id,
                    "target_employee_id": assignment.target_employee_id,
                    "target_type": assignment.target_type
                }
                all_answer_docs = list(answers_coll.find(filter_doc))
                any_completed = any(doc.get("status") == "completed" for doc in all_answer_docs)

                for ans_doc in all_answer_docs:
                    for answer in ans_doc.get("answers", []):
                        if isinstance(answer, dict) and "question_id" in answer:
                            answered_ids.add(answer["question_id"])
                        else:
                            answered_ids.add(answer)
                assignment_answered_count = len(answered_ids)
                logger.debug(
                    f"Survey {sid} for assignment (target: {assignment.target_employee_id}): "
                    f"answered {assignment_answered_count} out of {total_questions}"
                )
                assignment_progress = (assignment_answered_count / total_questions * 100)
                assignment_progresses.append(assignment_progress)
                assignment_completions.append(any_completed)

            avg_progress = sum(assignment_progresses) / len(assignment_progresses)
            all_assigns_completed = all(assignment_completions)
            survey_data = _build_survey_data(sid, survey_doc, avg_progress)

            if all_assigns_completed:
                categorized["completed"].append(survey_data)
            elif 0 < avg_progress < 100:
                categorized["in_progress"].append(survey_data)
            else:
                categorized["pending"].append(survey_data)

        return jsonify(categorized), 200

    except Exception as e:
        logger.critical("Error fetching surveys by status", exc_info=e)
        return jsonify({"error": "Internal Server Error"}), 500

@answers.route("/<id>", methods=["GET"])
@token_required()
def get_survey(id):
    """
    Retrieve a survey along with the authenticated user's answers, formatted as SurveyData.

    SurveyData interface:
      - title: string
      - subtitle: string
      - description: string
      - startTime: string (ISO timestamp)
      - totalTimeSpent: number (seconds)
      - questionBlocks: array of QuestionBlock, each:
          {
            title: string,
            description: string,
            scaleOptions?: [{ label: string, value: number }],
            questions: [
              {
                id: number,
                type: "scale" | "open",
                text: string,
                options?: [{ label: string, value: number }],
                answer?: number | string | null,
                minLength?: number,
                maxLength?: number
              }
            ]
          }
    """
    try:
        from datetime import datetime
        employee_id = g.user_id
        db_mongo = current_app.mongo_db
        if not db_mongo:
            return jsonify({"error": "Database not initialized"}), 500

        surveys_collection = db_mongo.get_collection("Surveys")
        survey_doc = surveys_collection.find_one({"_id": id})
        if not survey_doc:
            return jsonify({"message": "Survey not found"}), 404

        # Retrieve the answer document for this survey and employee.
        answers_coll = db_mongo.get_collection("SurveyAnswers")
        answer_doc = answers_coll.find_one({"survey_id": id, "employee_id": employee_id})

        # Build a lookup for user answers keyed by the original question id.
        user_answers = {}
        if answer_doc:
            for ans in answer_doc.get("answers", []):
                key = ans.get("question_id")
                user_answers[key] = ans.get("answer")

        # Helper: convert a question id string (e.g. "EP1_001_1") to a number by extracting digits.
        def convert_question_id(qid):
            digits = "".join(filter(str.isdigit, qid))
            try:
                return int(digits)
            except Exception:
                return 0

        # In this document, the survey blocks are stored under "questions".
        blocks = survey_doc.get("questions", [])
        transformed_blocks = []
        for block in blocks:
            block_title = block.get("title", "")
            block_description = block.get("description", "")
            # Each block may have its own scaleOptions.
            block_scale_options = block.get("scaleOptions", [])
            transformed_questions = []
            for q in block.get("questions", []):
                orig_id = q.get("id", "")
                q_id = convert_question_id(orig_id)
                # Map type: "Selección" -> "scale", "Abierta" -> "open".
                raw_type = q.get("type", "").lower()
                if "selección" in raw_type or "seleccion" in raw_type:
                    q_type = "scale"
                elif "abierta" in raw_type:
                    q_type = "open"
                else:
                    q_type = "scale"  # default fallback
                transformed_question = {
                    "id": q_id,
                    "type": q_type,
                    "text": q.get("text", ""),
                    "answer": user_answers.get(orig_id, None)
                }
                # For scale questions, attach options (question-level if available, else block-level).
                if q_type == "scale":
                    if q.get("options") is not None:
                        transformed_question["options"] = [
                            {"label": opt.get("label", ""), "value": int(opt.get("value", 0))}
                            for opt in q.get("options", [])
                        ]
                    else:
                        transformed_question["options"] = [
                            {"label": opt.get("label", ""), "value": int(opt.get("value", 0))}
                            for opt in block_scale_options
                        ]
                # Include optional fields if present.
                if "minLength" in q:
                    transformed_question["minLength"] = q["minLength"]
                if "maxLength" in q:
                    transformed_question["maxLength"] = q["maxLength"]
                transformed_questions.append(transformed_question)
            transformed_block = {
                "title": block_title,
                "description": block_description,
                "scaleOptions": (
                    [{"label": opt.get("label", ""), "value": int(opt.get("value", 0))}
                     for opt in block_scale_options]
                    if block_scale_options else None
                ),
                "questions": transformed_questions
            }
            transformed_blocks.append(transformed_block)

        # Determine startTime.
        if "created_at" in survey_doc:
            created_at = survey_doc["created_at"]
            if isinstance(created_at, dict) and "$date" in created_at:
                # Extended JSON format.
                timestamp = int(created_at["$date"].get("$numberLong", 0)) / 1000
                start_time = datetime.fromtimestamp(timestamp).isoformat()
            elif isinstance(created_at, datetime):
                start_time = created_at.isoformat()
            else:
                start_time = datetime.utcnow().isoformat()
        else:
            start_time = datetime.utcnow().isoformat()

        survey_data = {
            "title": survey_doc.get("title", ""),
            "subtitle": survey_doc.get("subtitle", ""),
            "description": survey_doc.get("description", ""),
            # "startTime": start_time,
            # "totalTimeSpent": int(survey_doc.get("totalTimeSpent", 0)),
            "questionBlocks": transformed_blocks
        }

        return jsonify(survey_data), 200

    except Exception as e:
        logger.critical("Error getting survey", exc_info=e)
        return jsonify({"error": "Internal Server Error"}), 500

def _build_survey_data(sid, survey_doc, progress):
    """
    Helper to build a dictionary with basic survey fields.
    """
    # Check for questions under "questionBlocks" or "questions"
    blocks = survey_doc.get("questionBlocks")
    if not blocks:
        blocks = survey_doc.get("questions", [])
    all_questions = []
    for block in blocks:
        all_questions.extend(block.get("questions", []))
    return {
        "id": sid,
        "title": survey_doc.get("title", "Untitled Survey"),
        "subtitle": survey_doc.get("subtitle", ""),
        "progress": round(progress, 2),
        "assignmentDate": survey_doc.get("deadline", ""),
        "handInDate": survey_doc.get("handInDate", ""),
        "questions": all_questions
    }