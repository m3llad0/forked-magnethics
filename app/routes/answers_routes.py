from flask import request, jsonify, Blueprint, current_app
from datetime import datetime
from app.utils import logger
from app.services import db
from app.models.employee_survey_assignment import EmployeeSurveyAssignment

answers = Blueprint("answer", __name__)

# Route 1: Save Survey Progress
@answers.route('/<survey_id>/save', methods=['POST'])
def save_survey_progress(survey_id):
    """
    Guarda el progreso de respuestas (status = "in_progress") en 'SurveyAnswers' (Mongo),
    asumiendo que el "employee_id" es el identificador de quien responde.
    """
    try:
        data = request.json

        # Solo requerimos un array "employee_answers"
        if not data or "employee_answers" not in data:
            logger.error("Missing 'employee_answers' in body")
            return jsonify({"error": "Invalid request data"}), 400

        employee_answers = data["employee_answers"]

        mongo_db = current_app.mongo_db
        if not mongo_db:
            return jsonify({"error": "MongoDB not initialized"}), 500

        surveys_coll = mongo_db.get_collection("Surveys")
        answers_coll = mongo_db.get_collection("SurveyAnswers")

        # Validar la encuesta en Mongo
        survey_doc = surveys_coll.find_one({"_id": survey_id})
        if not survey_doc:
            logger.error(f"Survey {survey_id} not found in Mongo")
            return jsonify({"error": "Survey not found"}), 404

        # Procesar cada bloque de respuestas
        for emp_ans in employee_answers:
            employee_id = emp_ans.get('employee_id')       # Quien responde
            answers = emp_ans.get('answers')               # Lista/objeto de respuestas

            if not employee_id or answers is None:
                logger.error("Missing 'employee_id' or 'answers'")
                return jsonify({"error": "Invalid employee answer data"}), 400

            # target_employee_id (solo en 360)
            target_employee_id = emp_ans.get('target_employee_id')  
            # target_type = "employee" o "company"
            target_type = emp_ans.get('target_type')

            # 1) Verificar asignación en SQL
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

            # Extraemos la info del target desde la asignación
            assignment = assignments[0]
            final_target_emp = assignment.target_employee_id
            final_target_type = assignment.target_type

            # 2) Guardar/actualizar en SurveyAnswers
            existing_doc = answers_coll.find_one({
                "survey_id": survey_id,
                "employee_id": employee_id,
                "target_employee_id": final_target_emp,
                "target_type": final_target_type
            })

            if existing_doc:
                # Update draft
                answers_coll.update_one(
                    {"_id": existing_doc["_id"]},
                    {
                        "$set": {
                            "answers": answers,
                            "status": "in_progress",
                            "last_updated": datetime.utcnow()
                        }
                    }
                )
                logger.info(f"Updated in_progress for survey={survey_id}, employee={employee_id}, target={final_target_emp}")
            else:
                # Create new draft
                new_doc = {
                    "survey_id": survey_id,
                    "employee_id": employee_id,
                    "target_employee_id": final_target_emp,
                    "target_type": final_target_type,
                    "answers": answers,
                    "status": "in_progress",
                    "created_at": datetime.now(),
                    "last_updated": datetime.now()
                }
                answers_coll.insert_one(new_doc)
                logger.info(f"Saved new progress for survey={survey_id}, employee={employee_id}, target={final_target_emp}")

        return jsonify({"message": "Survey progress saved successfully"}), 200

    except Exception as e:
        logger.critical(f"Error saving progress for survey {survey_id}", exc_info=e)
        return jsonify({"error": "Internal Server Error"}), 500

@answers.route('/<survey_id>/submit', methods=['POST'])
def submit_survey(survey_id):
    """
    Marca la encuesta como 'completed' en 'SurveyAnswers' (Mongo),
    asumiendo que 'employee_id' es el ID de quien responde.
    """
    try:
        data = request.json

        if not data or "employee_answers" not in data:
            logger.error("Missing 'employee_answers' in body")
            return jsonify({"error": "Invalid request data"}), 400

        employee_answers = data["employee_answers"]

        mongo_db = current_app.mongo_db
        if not mongo_db:
            return jsonify({"error": "MongoDB not initialized"}), 500

        surveys_coll = mongo_db.get_collection("Surveys")
        answers_coll = mongo_db.get_collection("SurveyAnswers")

        # Validar la encuesta en Mongo
        survey_doc = surveys_coll.find_one({"_id": survey_id})
        if not survey_doc:
            logger.error(f"Survey {survey_id} not found in Mongo")
            return jsonify({"error": "Survey not found"}), 404

        for emp_ans in employee_answers:
            employee_id = emp_ans.get('employee_id')
            answers = emp_ans.get('answers')
            target_employee_id = emp_ans.get('target_employee_id')
            target_type = emp_ans.get('target_type')

            if not employee_id or answers is None:
                logger.error("Missing 'employee_id' or 'answers'")
                return jsonify({"error": "Invalid employee answer data"}), 400

            # 1) Verificar asignación en SQL
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

            # 2) Actualizar/crear doc => 'completed'
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
                        "answers": answers,
                        "status": "completed",
                        "last_updated": datetime.utcnow()
                    }
                }
            )

            if result.matched_count == 0:
                # Crear doc
                new_doc = {
                    "survey_id": survey_id,
                    "employee_id": employee_id,
                    "target_employee_id": final_target_emp,
                    "target_type": final_target_type,
                    "answers": answers,
                    "status": "completed",
                    "created_at": datetime.now(),
                    "last_updated": datetime.now()
                }
                answers_coll.insert_one(new_doc)
                logger.info(f"Created new submission for survey={survey_id}, employee={employee_id}, target={final_target_emp}")
            else:
                logger.info(f"Updated existing submission for survey={survey_id}, employee={employee_id}, target={final_target_emp}")

        return jsonify({"message": "Survey submitted successfully"}), 200

    except Exception as e:
        logger.critical(f"Error submitting survey {survey_id}", exc_info=e)
        return jsonify({"error": "Internal Server Error"}), 500

@answers.route('/<survey_id>/answers', methods=['GET'])
def get_survey_answers(survey_id):
    """
    Obtiene las respuestas en SurveyAnswers, 
    filtrando por user_id (requerido) y opcionalmente employee_id, target_employee_id, target_type.
    """
    try:
        user_id = request.args.get("user_id")
        employee_id = request.args.get("employee_id")
        target_employee_id = request.args.get("target_employee_id")
        target_type = request.args.get("target_type")

        if not user_id:
            logger.error("user_id is required for fetching answers")
            return jsonify({"error": "user_id is required"}), 400

        mongo_db = current_app.mongo_db
        if not mongo_db:
            return jsonify({"error": "Database not initialized"}), 500

        answers_coll = mongo_db.get_collection("SurveyAnswers")

        query = {"survey_id": survey_id, "user_id": user_id}
        if employee_id:
            query["employee_id"] = employee_id
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
            logger.info(f"No answers found for survey {survey_id}, user {user_id}")
            return jsonify({"error": "No answers found for the given filters"}), 404

        return jsonify({"survey_id": survey_id, "answers": result}), 200

    except Exception as e:
        logger.critical(f"Error fetching answers for survey {survey_id}", exc_info=e)
        return jsonify({"error": "Internal Server Error"}), 500

@answers.route('/<survey_id>/answers', methods=['DELETE'])
def delete_survey_answers(survey_id):
    """
    Elimina respuestas en SurveyAnswers, 
    filtrando por user_id, employee_id, target_employee_id, target_type.
    """
    try:
        user_id = request.args.get("user_id")
        employee_id = request.args.get("employee_id")
        target_employee_id = request.args.get("target_employee_id")
        target_type = request.args.get("target_type")

        mongo_db = current_app.mongo_db
        if not mongo_db:
            return jsonify({"error": "Database not initialized"}), 500

        answers_coll = mongo_db.get_collection("SurveyAnswers")

        query = {"survey_id": survey_id}
        if user_id:
            query["user_id"] = user_id
        if employee_id:
            query["employee_id"] = employee_id
        if target_employee_id:
            query["target_employee_id"] = target_employee_id
        if target_type:
            query["target_type"] = target_type

        result = answers_coll.delete_many(query)
        if result.deleted_count == 0:
            logger.info(f"No answers found to delete for survey {survey_id}")
            return jsonify({"error": "No answers found to delete"}), 404

        logger.info(f"Deleted {result.deleted_count} answers for survey {survey_id}")
        return jsonify({"message": f"Deleted {result.deleted_count} answers"}), 200

    except Exception as e:
        logger.critical(f"Error deleting answers for survey {survey_id}", exc_info=e)
        return jsonify({"error": "Internal Server Error"}), 500

@answers.route('/surveys/status/<user_id>', methods=['GET'])
def get_surveys_by_status(user_id):
    """
    Categorización de encuestas (pending, in_progress, completed),
    manejando múltiples asignaciones para un mismo user_id en 360.
    """
    try:
        if not user_id:
            logger.error("user_id is required for fetching surveys by status")
            return jsonify({"error": "user_id is required"}), 400

        mongo_db = current_app.mongo_db
        if not mongo_db:
            return jsonify({"error": "Database not initialized"}), 500

        # Colecciones de Mongo
        surveys_coll = mongo_db.get_collection("Surveys")
        answers_coll = mongo_db.get_collection("SurveyAnswers")

        all_surveys = list(surveys_coll.find())
        if not all_surveys:
            logger.info("No surveys found")
            return jsonify({"pending": [], "in_progress": [], "completed": []}), 200

        # Diccionario final
        categorized = {
            "pending": [],
            "in_progress": [],
            "completed": []
        }

        for survey_doc in all_surveys:
            sid = str(survey_doc["_id"])

            # 1) Extraer total de preguntas
            question_blocks = survey_doc.get("questionBlocks", [])
            all_questions = []
            for block in question_blocks:
                all_questions.extend(block.get("questions", []))
            total_questions = len(all_questions)

            if total_questions == 0:
                # Si no hay preguntas, la consideramos completada o pending?
                # Aquí se decide la lógica; haré "pending" por default
                survey_data = _build_survey_data(sid, survey_doc, 0)
                categorized["pending"].append(survey_data)
                continue

            # 2) Consultar asignaciones en SQL: (employee_id=user_id, survey_id=sid)
            #    Importar tu modelo y session
            assignments = (db.session.query(EmployeeSurveyAssignment)
                                  .filter_by(employee_id=user_id, survey_id=sid)
                                  .all())

            if not assignments:
                # user no tiene asignación => "pending"
                survey_data = _build_survey_data(sid, survey_doc, 0)
                categorized["pending"].append(survey_data)
                continue

            # Vamos a calcular el avance de cada asignación
            assignment_progresses = []
            assignment_completions = []

            for assignment in assignments:
                # Recopilar question IDs respondidas sin duplicar
                answered_ids = set()

                # Buscar en SurveyAnswers
                filter_doc = {
                    "survey_id": sid,
                    "employee_id": user_id,
                    "target_employee_id": assignment.target_employee_id,
                    "target_type": assignment.target_type
                }
                all_answer_docs = list(answers_coll.find(filter_doc))

                # Verificar si hay un doc con status = "completed"
                any_completed = any(d.get("status") == "completed" for d in all_answer_docs)

                # Unir todas las question_id respondidas
                for ans_doc in all_answer_docs:
                    for q in ans_doc.get("answers", []):
                        qid = q.get("question_id")
                        if qid:
                            answered_ids.add(qid)

                assignment_answered_count = len(answered_ids)
                # Calcular avance para ESTA asignación
                assignment_progress = (assignment_answered_count / total_questions * 100) if total_questions else 0

                assignment_progresses.append(assignment_progress)
                assignment_completions.append(any_completed)

            # Ahora, cómo consolidamos?
            # Opción A: el avance global = "promedio" de las asignaciones
            # Opción B: el avance global = "mínimo" (es la parte más atrasada)
            # Opción C: "completed" sólo si TODAS están completadas
            # Te muestro la Opción A (promedio) + se require que TODAS completadas para considerarse completed.

            avg_progress = sum(assignment_progresses) / len(assignment_progresses)

            # "is_completed" si TODAS las asignaciones estan completadas
            all_assigns_completed = all(assignment_completions)

            # Armar un dict con info
            logger.debug(f"Survey={sid}, user_id={user_id}, progress={avg_progress:.2f}, all_completed={all_assigns_completed}")

            survey_data = _build_survey_data(sid, survey_doc, avg_progress)

            if all_assigns_completed:
                categorized["completed"].append(survey_data)
            elif avg_progress > 0 and avg_progress < 100:
                categorized["in_progress"].append(survey_data)
            else:
                categorized["pending"].append(survey_data)

        return jsonify(categorized), 200

    except Exception as e:
        logger.critical("Error fetching surveys by status", exc_info=e)
        return jsonify({"error": "Internal Server Error"}), 500


def _build_survey_data(sid, survey_doc, progress):
    """
    Helper para generar un diccionario con los campos básicos de la encuesta.
    """
    question_blocks = survey_doc.get("questionBlocks", [])
    all_questions = []
    for block in question_blocks:
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