from datetime import datetime
from bson.objectid import ObjectId
from app.models.client import Client
from app.models.product import Product
from app.models.survey import Survey  # Mongo-based Survey model
from flask import current_app
from app.utils import logger

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
