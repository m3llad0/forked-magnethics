from flask import request, jsonify, Blueprint, current_app
from app.models import Stages
from app.utils import logger
import app

stage = Blueprint("stage", __name__)

@stage.route("/", methods=["POST"])
def create_stage():
    try:
        stage_data = request.json

        required_fields = ["_id", "stage_name", "description", "test_items"]

        if not all(field in stage_data for field in required_fields):
            logger.error("Missing fields in body")
            return jsonify({"error": "Missing required fields"}), 400
        
        db = current_app.mongo_db
        if db:
            stages = db.get_collection("Stages")
        stage = Stages(
            stage_data["_id"],
            stage_data["producto"],
            stage_data["stage_name"],
            stage_data["description"],
            stage_data["test_items"],
            collection=stages
        )
        stage.insert_stage()

        return jsonify({"message": "Created new stage!", "data": stage.to_dict()}), 201

    except Exception as e:
        logger.critical("Error creating stage", exc_info=e)
        return jsonify({"error": "Internal Server Error"}), 500


@stage.route("/", methods=["GET"])
def get_stages():
    try:
        db = current_app.mongo_db
        if not db:
            return jsonify({"error": "Database not initialized"}), 500

        # Access the 'Stages' collection
        stages_collection = db.get_collection("Stages")

        # Fetch all documents from the collection
        stages_cursor = stages_collection.find()

        # Convert cursor to a list of dictionaries
        response = [stage for stage in stages_cursor]

        if not response:
            return jsonify({"message": "No data found"}), 404

        return jsonify(response), 200
    except Exception as e:
        logger.critical("Error getting stages", exc_info=e)
        return jsonify({"error": "Internal Server Error"}), 500


@stage.route("/<id>", methods=["GET"])
def get_stage(id):
    try:
        db = current_app.mongo_db
        if db:
            stages = db.get_collection("Stages")

        stage = Stages(collection=stages)

        response = stage.get_one(id)

        if not response:
            return jsonify({"message": "No data found"}), 404

        return jsonify(response)
    except Exception as e:
        logger.critical("Error getting stage", exc_info=e)
        return jsonify({"error": "Internal Server Error"}), 500


@stage.route("/<id>", methods=["PUT"])
def update_stage(id):
    try:
        update_data = request.json
        
        if not update_data:
            logger.error("No update data provided")
            return jsonify({"error": "No update data provided"}), 400

        db = current_app.mongo_db
        if db:
            stages = db.get_collection("Stages")

        stage = Stages(collection=stages)
        
        modified_count = stage.update(id, update_data)
        
        if modified_count == 0:
            return jsonify({"message": "No data updated. Stage may not exist."}), 404
        
        return jsonify({"message": "Stage updated successfully."}), 200
    except Exception as e:
        logger.critical("Error updating stage", exc_info=e)
        return jsonify({"error": "Internal Server Error"}), 500


@stage.route("/<id>", methods=["DELETE"])
def delete_stage(id):
    try:
        db = current_app.mongo_db
        if db:
            stages = db.get_collection("Stages")

        stage = Stages(collection=stages)

        deleted_count = stage.delete_one(id)

        if deleted_count == 0:
            return jsonify({"message": "No data deleted. Stage may not exist."}), 404

        return jsonify({"message": "Stage deleted successfully."}), 200
    except Exception as e:
        logger.critical("Error deleting stage", exc_info=e)
        return jsonify({"error": "Internal Server Error"}), 500
