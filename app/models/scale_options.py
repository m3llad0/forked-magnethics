from pymongo.collection import Collection
from bson.objectid import ObjectId
from typing import List, Dict

class ScaleOptions:
    def __init__(self, scale_options: List[Dict[str, str]], scale_options_collection: Collection):
        self.scale_options = scale_options
        self.scale_options_collection = scale_options_collection
    

    def insert_scale_options(self):
        if not self.scale_options:
            return ValueError("No scale options provided")
        
        result = self.scale_options_collection.insert_one(self.to_dict())

        return result.inserted_id

    def get_scale_options(self, id):
        object_id = ObjectId(id)
        scale_options = self.scale_options_collection.find_one({"_id": object_id})

        return scale_options["scaleOptions"]
    def to_dict(self):
        return {
            "scaleOptions": self.scale_options
        }
        