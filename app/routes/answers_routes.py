from flask import request, jsonify, Blueprint, current_app, g
from datetime import datetime
from app.utils import logger
from app.services import db
from app.models import EmployeeSurveyAssignment, Employee
from app.middleware import token_required 
from app.services.survey_service import SurveyService


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
    try:
        employee_id = g.user_id
        mongo_db = current_app.mongo_db
        if not mongo_db:
            return jsonify({"error": "Database not initialized"}), 500

        surveys_coll = mongo_db.get_collection("Surveys")
        answers_coll = mongo_db.get_collection("SurveyAnswers")
        
        assignments = db.session.query(EmployeeSurveyAssignment).filter_by(employee_id=employee_id).all()

        categorized = {
            "pending": [],
            "in_progress": [],
            "completed": []
        }

        from app.models.employee import Employee

        for assignment in assignments:
            sid = assignment.survey_id
            survey_doc = surveys_coll.find_one({"_id": sid})
            if not survey_doc:
                continue

            # Obtener preguntas válidas del survey
            blocks = survey_doc.get("questionBlocks") or survey_doc.get("questions", [])
            question_ids = set()
            for block in blocks:
                questions = block.get("questions", [])
                for q in questions:
                    qid = ""
                    if isinstance(q, dict):
                        qid = q.get("id", "")
                    elif isinstance(q, str):
                        qid = q
                    if isinstance(qid, str) and qid.strip():
                        question_ids.add(qid.strip())

            total_questions = len(question_ids)
            if total_questions == 0:
                logger.warning(f"Survey {sid} has no valid questions.")
                progress = 0
                any_completed = False
            else:
                filter_doc = {
                    "survey_id": sid,
                    "employee_id": employee_id,
                    "target_employee_id": assignment.target_employee_id,
                    "target_type": assignment.target_type
                }
                all_answer_docs = list(answers_coll.find(filter_doc))
                answered_ids = set()
                for ans_doc in all_answer_docs:
                    for answer in ans_doc.get("answers", []):
                        qid = ""
                        value = None
                        if isinstance(answer, dict):
                            qid = answer.get("question_id", "")
                            value = answer.get("answer", None)
                        elif isinstance(answer, str):
                            qid = answer
                            value = answer  # fallback

                        if (
                            isinstance(qid, str)
                            and qid.strip()
                            and value not in [None, "", [], {}]
                        ):
                            answered_ids.add(qid.strip())

                progress = (len(answered_ids & question_ids) / total_questions) * 100
                any_completed = any(doc.get("status") == "completed" for doc in all_answer_docs)

            # Determinar la categoría
            if any_completed:
                category = "completed"
            elif progress > 0:
                category = "in_progress"
            else:
                category = "pending"

            # Título dinámico para encuestas 360
            title = survey_doc.get("title", "Untitled Survey")
            if survey_doc.get("survey_type", "").lower() == "360" and assignment.target_employee_id:
                evaluated = db.session.get(Employee, assignment.target_employee_id)
                if evaluated:
                    title = f"{evaluated.first_name} {evaluated.last_name_paternal}"

            survey_data = {
                "id": sid,
                "title": title,
                "target_employee_id": assignment.target_employee_id,
                "subtitle": survey_doc.get("subtitle", ""),
                "progress": round(progress, 2),
                "assignmentDate": survey_doc.get("deadline", ""),
                "handInDate": survey_doc.get("handInDate", ""),
                "questions": list(question_ids)
            }
            categorized[category].append(survey_data)

        return jsonify(categorized), 200

    except Exception as e:
        logger.critical("Error fetching surveys by status", exc_info=e)
        return jsonify({"error": "Internal Server Error"}), 500


@answers.route("/<id>/<target_employee_id>", methods=["GET"])
@token_required()
def get_survey(id, target_employee_id):
    try:
        from datetime import datetime
        employee_id = g.user_id
        print(f"target_employee_id: {target_employee_id}")
        db_mongo = current_app.mongo_db
        if not db_mongo:
            return jsonify({"error": "Database not initialized"}), 500

        surveys_collection = db_mongo.get_collection("Surveys")
        survey_doc = surveys_collection.find_one({"_id": id})
        if not survey_doc:
            return jsonify({"message": "Survey not found"}), 404

        # Para encuestas 360, se espera que se pase target_employee_id como parámetro para identificar al evaluado
        if survey_doc.get("survey_type", "").lower() == "360":
            if target_employee_id:
                evaluated = db.session.get(Employee, target_employee_id)
                if evaluated:
                    survey_doc["title"] = f"{evaluated.first_name} {evaluated.last_name_paternal}"
                    survey_doc["target_employee_id"] = evaluated.id
        # Recuperar respuestas del evaluador (si existen)
        answers_coll = db_mongo.get_collection("SurveyAnswers")
        answer_doc = answers_coll.find_one({"survey_id": id, "employee_id": employee_id, "target_employee_id": target_employee_id})
        user_answers = {}
        if answer_doc:
            for ans in answer_doc.get("answers", []):
                key = ans.get("question_id")
                user_answers[key] = ans.get("answer")

        def convert_question_id(qid):
            digits = "".join(filter(str.isdigit, qid))
            try:
                return int(digits)
            except Exception:
                return 0

        blocks = survey_doc.get("questions", [])
        transformed_blocks = []
        for block in blocks:
            block_title = block.get("title", "")
            block_description = block.get("description", "")
            block_scale_options = block.get("scaleOptions", [])
            transformed_questions = []
            for q in block.get("questions", []):
                orig_id = q.get("id", "")
                raw_type = q.get("type", "").lower()
                if "selección" in raw_type or "seleccion" in raw_type:
                    q_type = "scale"
                elif "abierta" in raw_type:
                    q_type = "open"
                else:
                    q_type = "scale"
                transformed_question = {
                    "id": orig_id,
                    "type": q_type,
                    "text": q.get("text", ""),
                    "answer": user_answers.get(orig_id, None)
                }
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

        if "created_at" in survey_doc:
            created_at = survey_doc["created_at"]
            if isinstance(created_at, dict) and "$date" in created_at:
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
            "questionBlocks": transformed_blocks
        }
        return jsonify(survey_data), 200

    except Exception as e:
        logger.critical("Error getting survey", exc_info=e)
        return jsonify({"error": "Internal Server Error"}), 500

@answers.route("/<survey_id>/<client_id>", methods=["GET"])
def get_answers(survey_id, client_id):
    try:
        mongo_db = current_app.mongo_db

        if not mongo_db:
            return jsonify({"error": "Database not initialized"}), 500
        answer_service = SurveyService(db=db, mongo_db=mongo_db)

        answers = answer_service.get_excel(survey_id, client_id)
        return current_app.response_class(
            answers,
           mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename=results_{survey_id}.xlsx"}
        )
    except Exception as e:
        logger.critical("Error getting answers", exc_info=e)
        return jsonify({"error": "Internal Server Error"}), 500
        
