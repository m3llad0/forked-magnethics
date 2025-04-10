from pymongo.collection import Collection
from bson.objectid import ObjectId

class Stages:
    def __init__(self, stage_id, producto, stage_name, description, test_items, collection: Collection):
        self.id = stage_id
        self.producto = producto
        self.stage_name = stage_name
        self.description = description
        self.test_items = test_items
        self.collection = collection

    def to_dict(self):
        return {
            "_id": self.id,
            "producto": self.producto,
            "name": self.stage_name,
            "description": self.description,
            "test_item": self.test_items
        }
    
    def insert_stage(self):
        result = self.collection.insert_one(self.to_dict())
        return result.inserted_id

    def get_one(self, stage_id):
        """
        Retrieve the stage document from the database.
        If the stage_id is a valid ObjectId string, it is converted accordingly.
        """
        query_id = ObjectId(stage_id) if ObjectId.is_valid(str(stage_id)) else stage_id
        return self.collection.find_one({"_id": query_id}) or {}

    def get_all(self):
        return list(self.collection.find())

    def delete_one(self, stage_id):
        query_id = ObjectId(stage_id) if ObjectId.is_valid(str(stage_id)) else stage_id
        result = self.collection.delete_one({"_id": query_id})
        return result.deleted_count

    def update(self, stage_id, updates):
        query_id = ObjectId(stage_id) if ObjectId.is_valid(str(stage_id)) else stage_id
        result = self.collection.update_one({"_id": query_id}, {"$set": updates})
        return result.modified_count

    def _fetch_test_items(self):
        """
        Helper method to ensure we have the latest test_item data.
        If self.test_items is empty or None, fetch the stage document from the DB.
        """
        if self.test_items:
            return self.test_items
        stage = self.get_one(self.id)
        return stage.get("test_item", [])

    def get_test_item_by_id(self, test_item_id):
        """
        Given a test item id, search through the Stage's many test_items and return a
        dictionary containing that test_item's 'id' and 'name'.
        
        For example, if test_item_id is "CPE_001" and a matching test item is found, 
        the method returns:
            {"id": "CPE_001", "name": "Pensamiento Crítico"}
        
        If no match is found, it returns an empty dictionary.
        """
        test_items = self._fetch_test_items()
        for item in test_items:
            if item.get("id") == test_item_id:
                return {"id": item.get("id"), "name": item.get("name")}
        return {}

    def get_questions_by_test_item_id(self, test_item_id):
        """
        Given a test item id, search through the Stage's test_items for the matching one,
        and return a list of dictionaries for each question in that test item.
        Each dictionary contains the question's 'id' and 'text'.
        
        For example, if test_item "CPE_001" is found, the method might return:
            [
                {"id": "CPE_001_1", "text": "Aborda los problemas complejos de manera sistemática, ..."},
                {"id": "CPE_001_2", "text": "Identifica y cuestiona supuestos de los argumentos ..."},
                ...
            ]
        
        If no matching test item is found, an empty list is returned.
        """
        test_items = self._fetch_test_items()
        for item in test_items:
            if item.get("id") == test_item_id:
                return [{"id": q.get("id"), "text": q.get("text")} for q in item.get("questions", [])]
        return []
