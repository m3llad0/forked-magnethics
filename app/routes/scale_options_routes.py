from flask import request, jsonify, Blueprint, current_app
from app.models import ScaleOptions
from app.utils import logger

scale_options = Blueprint("scale-options", __name__)

@scale_options.route("/", methods=["POST"])
def create_options():
    try:
        scale_options_data = request.json

        required_fields = ["scale_options"]

        if not all(field in scale_options_data for field in required_fields):
            logger.error("Missing fields in body")
            return jsonify({"error": "Missing required fields"}), 400

        db = current_app.mongo_db
        if not db:
            return jsonify({"error": "Database not initialized"}), 500

        scale_options_coll = db.get_collection("ScaleOptions")
        scale_options = ScaleOptions(scale_options=scale_options_data["scale_options"], scale_options_collection=scale_options_coll)

        scale_options_id = scale_options.insert_scale_options()

        return jsonify({"message": "Created new scale options!", "scale_options_id": str(scale_options_id)}), 201
    except Exception as e:
        logger.critical("Error creating scale options", exc_info=e)
        return jsonify({"error": "Internal Server Error"}), 500

@scale_options.route("/", methods=["GET"])
def get_options():
    try:
        db = current_app.mongo_db
        if not db:
            return jsonify({"error": "Database not initialized"}), 500

        options = db.get_collection("ScaleOptions").find()

        return jsonify(options), 200
    except Exception as e:
        logger.critical("Error getting scale options", exc_info=e)
        return jsonify({"error": "Internal Server Error"}), 500
    
@scale_options.route("/<id>", methods=["GET"])
def get_option(id):
    try:
        db = current_app.mongo_db
        if not db:
            return jsonify({"error": "Database not initialized"}), 500

        scale_options = ScaleOptions(scale_options=[{"":"", "":""}], scale_options_collection=db.get_collection("ScaleOptions"))
        option = scale_options.get_scale_options(id)

        return jsonify(option), 200
    except Exception as e:
        logger.critical("Error getting scale options", exc_info=e)
        return jsonify({"error": "Internal Server Error"}), 500
    
@scale_options.route("/<id>", methods=["PUT"])
def update_option(id):
    try:
        scale_options_data = request.json

        required_fields = ["scale_options"]

        if not all(field in scale_options_data for field in required_fields):
            logger.error("Missing fields in body")
            return jsonify({"error": "Missing required fields"}), 400

        db = current_app.mongo_db
        if not db:
            return jsonify({"error": "Database not initialized"}), 500

        scale_options_coll = db.get_collection("ScaleOptions")

        scale_options_coll.update_one({"_id": id}, {"$set": {"scaleOptions": scale_options_data["scale_options"]}})

        return jsonify({"message": "Updated scale options!"}), 200
    except Exception as e:
        logger.critical("Error updating scale options", exc_info=e)
        return jsonify({"error": "Internal Server Error"}), 500
    
@scale_options.route("/<id>", methods=["DELETE"])
def delete_option(id):
    try:
        db = current_app.mongo_db
        if not db:
            return jsonify({"error": "Database not initialized"}), 500

        scale_options_coll = db.get_collection("ScaleOptions")

        scale_options_coll.delete_one({"_id": id})

        return jsonify({"message": "Deleted scale options!"}), 200
    except Exception as e:
        logger.critical("Error deleting scale options", exc_info=e)
        return jsonify({"error": "Internal Server Error"}), 500