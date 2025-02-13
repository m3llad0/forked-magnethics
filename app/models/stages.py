from pymongo.collection import Collection

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
        stage = self.collection.find_one({"_id": stage_id})

        if stage:
            return stage
    
    def get_all(self):
        stages = self.collection.find()

        if stages:
            return stages
        
    def delete_one(self, stage_id):

        result = self.collection.delete_one({"id": stage_id})

        return result.deleted_count
    
    def update(self, stage_id, updates):
        result = self.collection.update_one({"id": stage_id}, {"$set": updates})
        return result.modified_count