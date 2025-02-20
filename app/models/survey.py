from pymongo.collection import Collection
from bson.objectid import ObjectId

class Survey:
    def __init__(self, id, title, subtitle, description, client_id, deadline, handInDate, question_ids, scale_options, stage_collection: Collection, survey_collection: Collection):
        self.survey_id = id
        self.title = title
        self.subtitle = subtitle
        self.description = description
        self.client_id = client_id
        self.deadline = deadline
        self.handInDate = handInDate
        self.question_ids = question_ids
        self.scale_options = scale_options
        self.stage_collection = stage_collection
        self.survey_collection = survey_collection
        self.question_blocks = []

    def fetch_questions(self):
        # Query the stages collection to fetch relevant questions
        pipeline = [
            {"$unwind": "$test_item"},
            {"$unwind": "$test_item.questions"},
            {"$match": {"test_item.questions.id": {"$in": self.question_ids}}}
        ]
        results = self.stage_collection.aggregate(pipeline)

        grouped_questions = {}

        for result in results:
            block_title = result["test_item"]["name"]  # Use test_item name as block title
            block_description = result["test_item"]["description"]
            question = result["test_item"]["questions"]

            if block_title not in grouped_questions:
                grouped_questions[block_title] = {
                    "title": block_title,
                    "description": block_description,
                    "scaleOptions": self.scale_options,
                    "questions": []
                }

            grouped_questions[block_title]["questions"].append({
                "id": question["id"],
                "text": question["text"],
                "type": question["type"],
                "answer": 0  # Default answer value
            })

        self.question_blocks = list(grouped_questions.values())

    def insert_survey(self):
        if not self.question_blocks:
            # raise ValueError("Question blocks have not been populated. Run fetch_questions first.")
            self.fetch_questions()  
        return self.survey_collection.insert_one(self.to_dict()).inserted_id

    def to_dict(self):
        return {
            "_id": self.survey_id,
            "title": self.title,
            "subtitle": self.subtitle,
            "description": self.description,
            "deadline": self.deadline,
            "handInDate": self.handInDate,
            "questionBlocks": self.question_blocks
        }
