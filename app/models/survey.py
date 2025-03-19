from pymongo.collection import Collection
from bson.objectid import ObjectId
from app.utils import logger
from datetime import datetime

class Survey:
    def __init__(self, _id, title, subtitle, description, client_id, deadline,
                 handInDate, stage_ids, scale_options, stage_collection, survey_collection,
                 product_id, survey_type, sindicalizados):
        """
        Initializes a Survey instance.

        :param stage_ids: List of stage IDs to fetch questions.
        :param scale_options: Scale options configuration.
        :param stage_collection: MongoDB collection for stages.
        :param survey_collection: MongoDB collection for surveys.
        :param survey_type: String indicating survey type ("360", "enex", etc.).
        :param sindicalizados: Boolean indicating if la encuesta es para sindicalizados.
        """
        self._id = _id
        self.title = title
        self.subtitle = subtitle
        self.description = description
        self.client_id = client_id
        self.deadline = deadline
        self.handInDate = handInDate
        self.stage_ids = stage_ids
        self.scale_options = scale_options
        self.stage_collection = stage_collection
        self.survey_collection = survey_collection
        self.product_id = product_id
        self.survey_type = survey_type
        self.sindicalizados = sindicalizados  # Nuevo campo
        self.questions = []  # Se completará con fetch_questions()

    def fetch_questions(self):
        """
        Obtiene las preguntas agrupadas por bloque desde cada etapa (documentos de la colección "Stages").
        Se espera que cada documento de etapa tenga un campo "test_item" (lista de bloques),
        donde cada bloque incluye:
            - "name": que se usará como title del bloque.
            - "instruction": que se usará como description del bloque.
            - "questions": lista de preguntas.
        
        Para encuestas ENEX:
        - Si el stage_id comienza con "EP1", se asigna el scale point de "aspect1".
        - Si comienza con "EP2", se asigna el scale point de "aspect2".
        Para encuestas 360 se asigna directamente la lista de opciones.
        """
        blocks = []
        for stage_id in self.stage_ids:
            try:
                stage = self.stage_collection.find_one({"_id": stage_id})
                if stage:
                    test_items = stage.get("test_item", [])
                    for item in test_items:
                        block = {
                            "title": item.get("name", ""),
                            "description": item.get("instruction", ""),
                            "questions": item.get("questions", [])
                        }
                        # Asignar el scale point según el tipo de encuesta y la etapa.
                        if self.survey_type == "enex":
                            if stage_id.startswith("EP1"):
                                block["scaleOptions"] = self.scale_options.get("aspect1", [])
                            elif stage_id.startswith("EP2"):
                                block["scaleOptions"] = self.scale_options.get("aspect2", [])
                            else:
                                block["scaleOptions"] = []
                        else:
                            block["scaleOptions"] = self.scale_options
                        blocks.append(block)
                else:
                    logger.warning(f"Stage with id {stage_id} not found")
            except Exception as e:
                logger.error(f"Error fetching stage {stage_id}: {e}")
        self.questions = blocks


    def insert_survey(self):
        """
        Inserts the survey document into the MongoDB collection.
        """
        survey_doc = {
            "_id": self._id,
            "title": self.title,
            "subtitle": self.subtitle,
            "description": self.description,
            "client_id": self.client_id,
            "deadline": self.deadline,
            "handInDate": self.handInDate,
            "stage_ids": self.stage_ids,
            "scale_options": self.scale_options,
            "questions": self.questions,
            "product_id": self.product_id,
            "survey_type": self.survey_type,
            "sindicalizados": self.sindicalizados,  # Nuevo campo incluido
            "created_at": datetime.utcnow()
        }
        result = self.survey_collection.insert_one(survey_doc)
        return result.inserted_id
