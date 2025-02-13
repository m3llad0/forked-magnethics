from pymongo.collection import Collection
from datetime import datetime


class Survey:
    def __init__(self, id, title, subtitle, description, deadline, handInDate, question_ids, scale_options, stage_collection: Collection, survey_collection: Collection):
        self.survey_id = id
        self.title = title
        self.subtitle = subtitle
        self.description = description
        self.deadline = deadline
        self.handInDate = handInDate
        self.start_time = 0  # Default value
        self.total_time_spent = 0  # Default value
        self.question_ids = question_ids  # List of question IDs
        self.scale_options = scale_options  # Custom scale options provided by the user
        self.stage_collection = stage_collection  # MongoDB collection for stages
        self.survey_collection = survey_collection  # MongoDB collection for surveys
        self.question_blocks = []  # This will be constructed later

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

    def to_dict(self):
        return {
            "_id": self.survey_id,
            "title": self.title,
            "subtitle": self.subtitle,
            "description": self.description,
            "startTime": self.start_time,
            "totalTimeSpent": self.total_time_spent,
            "deadline": self.deadline,
            "handInDate": self.handInDate,
            "questionBlocks": self.question_blocks
        }

    def insert_survey(self):
        if not self.question_blocks:
            raise ValueError("Question blocks have not been populated. Run fetch_questions first.")

        survey_data = self.to_dict()
        result = self.survey_collection.insert_one(survey_data)
        return result.inserted_id