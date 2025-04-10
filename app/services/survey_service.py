from datetime import datetime
from bson.objectid import ObjectId
from app.models import Event, Product, Employee, Client, Survey, Stages
from flask import current_app
from app.utils import logger
import pandas as pd


class SurveyService:
    REQUIRED_FIELDS = [
        "_id", "title", "subtitle", "description",
        "client_id", "product_id", "deadline", "handInDate",
        "scale_ids", "stage_ids", "survey_type"  # survey_type determines the rules.
    ]

    def __init__(self, mongo_db, db):
        self.mongo_db = mongo_db
        self.db = db

    def create_survey(self, data):
        """
        Creates a new survey in MongoDB with flexible behavior based on survey type.
        
        For a 360 survey:
            - A single scale option is applied uniformly to all stages.
        
        For an ENEX survey:
            - Two scale points are applied for each stage (each evaluating a different aspect).
              If only one scale point is provided, that same scale will be used for both aspects.
        
        The function expects the user to provide:
          - A list (or a single value) of scale IDs in 'scale_ids'
          - A list of stage IDs in 'stage_ids'
          - Additionally, a boolean field 'sindicalizados' indicating if la encuesta está dirigida a sindicalizados.
        
        The Survey model's fetch_questions() method should retrieve all questions based on these stage IDs.
        """
        # Validate required fields
        if not data or not all(field in data for field in self.REQUIRED_FIELDS):
            raise ValueError("Missing required fields")

        survey_type = data["survey_type"].lower()

        # Extraer el nuevo campo booleano para sindicalizados; por defecto False.
        sindicalizados = data.get("sindicalizados", False)

        # Validate related SQL entities.
        client_obj = self.db.session.get(Client, data["client_id"])
        if not client_obj:
            raise ValueError("Client not found")
        product_obj = self.db.session.get(Product, data["product_id"])
        if not product_obj:
            raise ValueError("Product not found")

        mongo_db = self.mongo_db
        scale_options_coll = mongo_db.get_collection("ScaleOptions")

        # Support a single scale ID or a list of them.
        scale_ids = data.get("scale_ids")
        if not scale_ids:
            raise ValueError("Missing scale_ids")
        if isinstance(scale_ids, list):
            scale_ids_list = scale_ids
        else:
            scale_ids_list = [scale_ids]

        # Fetch scale options for each provided ID.
        scale_options_list = []
        for sid in scale_ids_list:
            doc = scale_options_coll.find_one({"_id": ObjectId(sid)})
            if not doc:
                raise ValueError(f"Invalid scale option for id {sid}")
            scale_options_list.append(doc.get("scaleOptions", []))

        # Adjust scale options based on survey type.
        if survey_type == "360":
            # For 360, we use a single scale option.
            if len(scale_options_list) == 1:
                final_scale_options = scale_options_list[0]
            else:
                final_scale_options = scale_options_list[0]
        elif survey_type == "enex":
            # For ENEX, we need two scale points per stage.
            if len(scale_options_list) == 1:
                final_scale_options = {"aspect1": scale_options_list[0], "aspect2": scale_options_list[0]}
            elif len(scale_options_list) >= 2:
                final_scale_options = {"aspect1": scale_options_list[0], "aspect2": scale_options_list[1]}
            else:
                raise ValueError("No scale options provided for ENEX survey")
        else:
            raise ValueError("Unsupported survey type")

        # Create a Survey instance.
        stages_coll = mongo_db.get_collection("Stages")
        surveys_coll = mongo_db.get_collection("Surveys")
        survey_obj = Survey(
            _id=data["_id"],
            title=data["title"],
            subtitle=data["subtitle"],
            description=data["description"],
            client_id=client_obj.id,
            deadline=data["deadline"],
            handInDate=data["handInDate"],
            stage_ids=data["stage_ids"],
            scale_options=final_scale_options,
            stage_collection=stages_coll,
            survey_collection=surveys_coll,
            product_id=data["product_id"],
            survey_type=survey_type,
            sindicalizados=sindicalizados  # Nuevo campo agregado
        )
        
        # Fetch all questions from the provided stage IDs.
        survey_obj.fetch_questions()
        inserted_id = survey_obj.insert_survey()
        logger.info(f"Survey inserted with _id={inserted_id}")
        return survey_obj._id

    def get_results(self, survey_id: str, client_id: str):
        try:
            closed_list = []
            open_list = []

            # Get collections
            surveys_coll = self.mongo_db.get_collection("Surveys")
            stages_coll = self.mongo_db.get_collection("Stages")

            # Try both collections in case of inconsistency
            answers_coll = self.mongo_db.get_collection("SurveyAnswers")
            answers_docs = list(answers_coll.find({"survey_id": survey_id, "status": "completed"}))
            if not answers_docs:
                logger.warning("No completed documents found in SurveyAnswers, trying Answers...")
                answers_coll = self.mongo_db.get_collection("Answers")
                answers_docs = list(answers_coll.find({"survey_id": survey_id, "status": "completed"}))

            if not answers_docs:
                logger.warning("No completed documents found with status. Retrying without status filter...")
                answers_docs = list(answers_coll.find({"survey_id": survey_id}))

            logger.info(f"Found {len(answers_docs)} answers for survey {survey_id}")

            if not answers_docs:
                logger.error("No answer documents found even after fallback.")
                return closed_list, open_list

            # Sample doc debug
            logger.debug(f"Sample answer: {answers_docs[0]}")

            # Retrieve client info
            client = self.db.session.query(Client).filter_by(id=client_id)
            if not client:
                raise Exception("Client not found")
            # Retrieve employee info
            employees = self.db.session.query(Employee).filter_by(client_id=client_id).all()
            if not employees:
                raise Exception("No employees found for the client")

            employee_dict = {
                emp.id: f"{emp.first_name} {emp.last_name_paternal} {emp.last_name_maternal}" for emp in employees
            }

            # Get survey info
            survey_doc = surveys_coll.find_one({"_id": survey_id})
            if not survey_doc:
                raise Exception("Survey not found")
            event_id = 1  # Placeholder or real call to Event().get_event(survey_id)

            # Build question mapping from all stages
            question_mapping = {}
            all_stages = stages_coll.find({})
            for stage_doc in all_stages:
                for test_item in stage_doc.get("test_item", []):
                    competence_id = test_item.get("id", "")
                    competence_name = test_item.get("name", "")
                    for question in test_item.get("questions", []):
                        q_id = question.get("id", "")
                        question_mapping[q_id] = {
                            "competence_id": competence_id,
                            "competence_name": competence_name,
                            "reactive_id": q_id,
                            "reactive_name": question.get("text", "")
                        }

            logger.info(f"Total questions indexed: {len(question_mapping)}")

            # Process answers
            for doc in answers_docs:
                evaluated_id = doc.get("target_employee_id")
                evaluated_name = employee_dict.get(evaluated_id, "Unknown")
                target_type = doc.get("target_type", "employee")

                for ans in doc.get("answers", []):
                    question_id = ans.get("question_id")
                    raw_ans = ans.get("answer")

                    details = question_mapping.get(question_id)
                    if not details:
                        logger.warning(f"Question ID {question_id} not found in mapping.")
                        details = {
                            "competence_id": "N/A",
                            "competence_name": "N/A",
                            "reactive_id": question_id,
                            "reactive_name": "N/A"
                        }

                    row_common = {
                        "RFC CLIENTE": client.company_rfc,
                        "CLIENTE": client.company_name,
                        "ID EVENTO": event_id,
                        "ID EMPLEADO EVALUADO": evaluated_id,
                        "NOMBRE": evaluated_name,
                        "ID COMPETENCIA": details["competence_id"],
                        "NOMBRE COMPETENCIA": details["competence_name"],
                        "ID REACTIVO": details["reactive_id"],
                        "NOMBRE REACTIVO": details["reactive_name"],
                        "TIPO USUARIO": target_type
                    }

                    try:
                        if isinstance(raw_ans, dict) and "$numberInt" in raw_ans:
                            value = int(raw_ans["$numberInt"])
                        else:
                            value = int(raw_ans)
                        row_common["PONDERACIÓN DE LA RESPUESTA"] = value
                        closed_list.append(row_common)
                    except Exception:
                        open_list.append({
                            "RFC CLIENTE": client.company_rfc,
                            "CLIENTE": client.company_name,
                            "ID EVENTO": event_id,
                            "ID EMPLEADO EVALUADO": evaluated_id,
                            "NOMBRE": evaluated_name,
                            "ID COMPETENCIA": details["competence_id"],
                            "NOMBRE COMPETENCIA": details["competence_name"],
                            "ID REACTIVO": details["reactive_id"],
                            "NOMBRE REACTIVO": details["reactive_name"],
                            "TIPO USUARIO": target_type,
                            "TEXTO LIBRE": raw_ans
                        })


            return closed_list, open_list

        except Exception as e:
            logger.error(f"Error in get_results: {e}")
            raise e


    def get_excel(self, survey_id: str, client_id: str):
            """
            Creates an Excel file (in-memory) with two sheets based on survey results.
            
            This function:
            - Calls get_results() to retrieve raw closed and open answer data.
            - Creates two Pandas DataFrames (one for closed answers and one for open answers).
            - Writes these DataFrames to an in-memory Excel file with two sheets:
                    "Closed Questions" and "Open Questions".
            
            Returns:
                BytesIO: An in-memory bytes buffer containing the Excel file.
            """
            try:
                import io
                import pandas as pd

                # Retrieve raw results data.
                closed_list, open_list = self.get_results(survey_id, client_id)

                logger.info(closed_list)
                # Create DataFrames in this function.
                closed_df = pd.DataFrame(closed_list, columns=[
                    "RFC CLIENTE",
                    "CLIENTE",
                    "ID EVENTO",
                    "ID EMPLEADO EVALUADO",
                    "NOMBRE",
                    "ID COMPETENCIA",
                    "NOMBRE COMPETENCIA",
                    "ID REACTIVO",
                    "NOMBRE REACTIVO",
                    "TIPO USUARIO",
                    "PONDERACIÓN DE LA RESPUESTA"
                ])
                open_df = pd.DataFrame(open_list, columns=[
                    "RFC CLIENTE",
                    "CLIENTE",
                    "ID EVENTO",
                    "ID EMPLEADO EVALUADO",
                    "NOMBRE",
                    "ID COMPETENCIA",
                    "NOMBRE COMPETENCIA",
                    "ID REACTIVO",
                    "NOMBRE REACTIVO",
                    "TIPO USUARIO",
                    "TEXTO LIBRE"
                ])
                # Create an in-memory Excel file with two sheets.
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine="openpyxl") as writer:
                    closed_df.to_excel(writer, sheet_name="Closed Questions", index=False)
                    open_df.to_excel(writer, sheet_name="Open Questions", index=False)
                output.seek(0)
                return output

            except Exception as e:
                logger.error(f"Error in get_excel: {e}")
                raise e
