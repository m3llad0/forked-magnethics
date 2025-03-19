from flask import request, jsonify, Blueprint
from app.models.consultant import Consultant
from app.utils import logger
from app.config import CLERK_CLIENT
from app.middleware import postman_consultant_token_required

consultant = Blueprint("consultant", __name__)

@consultant.route("/", methods=["POST"])
def create_consultant():
    try:
        data = request.json

        required_fields = ["name", "lastname", "email"]
        if not all(field in data for field in required_fields):
            logger.error("Missing fields in body")
            return jsonify({"error": "Missing required fields"}), 400

        # email = data["email"]
        # if CLERK_CLIENT.users.get(email):
        #     logger.error("User with email already exists")
        #     return jsonify({"error": "User with email already exists"}), 400
        

        user = CLERK_CLIENT.users.create(request={
                "email_address": [data["email"]], 
                "public_metadata": {"user_type": "consultant"},
                "role": "org:superadmin",
        })
        
        consultant = Consultant.create_consultant({
            "id":user.id,
            "name":data["name"],
            "lastname":data["lastname"],
        })
        return jsonify({"message": "Created new consultant", "data": consultant.to_dict()}), 201
    except ValueError as ve:
        logger.error(str(ve))
        return jsonify({"error": str(ve)}), 400
    except Exception as e:

        logger.critical(f"Failed to create new consultant with error {e}")
        return jsonify({"error": "Internal Server Error"}), 500
    
@consultant.route("/", methods=["GET"])
@postman_consultant_token_required
def get_consultants():
    try:
        consultants = Consultant.query.all()
        return jsonify([consultant.to_dict() for consultant in consultants]), 200
    except Exception as e:
        logger.critical("Failed to get consultants", exc_info=e)
        return jsonify({"error": "Internal Server Error"}), 500
    
@consultant.route("/<id>", methods=["GET"])
@postman_consultant_token_required
def get_consultant(id):
    try:
        consultant = Consultant.query.get(id)

        if consultant is None:
            return jsonify({"error": "Consultant doesn't exist"}), 404
        return jsonify(consultant.to_dict()), 200
    except Exception as e:
        logger.critical("Failed to get consultant", exc_info=e)
        return jsonify({"error": "Internal Server Error"}), 500
    
@consultant.route("/<id>", methods=["PUT"])
@postman_consultant_token_required
def update_consultant(id):
    try:
        data = request.json
        consultant = Consultant.update_consultant(id, data)
        return jsonify({"message": "Consultant updated", "data": consultant.to_dict()}), 200
    except ValueError as ve:
        logger.error(str(ve))
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        logger.critical("Failed to update consultant", exc_info=e)
        return jsonify({"error": "Internal Server Error"}), 500

@consultant.route("/<id>", methods=["DELETE"])
@postman_consultant_token_required
def delete_consultant(id):
    try:
        CLERK_CLIENT.users.delete(id)
        Consultant.delete_consultant(id)
        return jsonify({"message": "Consultant deleted"}), 200
    except ValueError as ve:
        logger.error(str(ve))
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        logger.critical("Failed to delete consultant", exc_info=e)
        return jsonify({"error": "Internal Server Error"}), 500
    


