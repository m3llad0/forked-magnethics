from flask import request, jsonify, Blueprint
from app.models import Client
from app.utils import logger


client = Blueprint("client", __name__)

@client.route("/", methods = ["POST"])
def create_client():
    try:
        data = request.json

        required_fields = ["id","company_name","business_name", "group_name", "holding_group","country", "primary_contact", "contact_email","contact_phone"]

        if not all(field in data for field in required_fields):
            logger.error("Missing fields in body")
            return jsonify({"error": "Missing required fields"}), 400
        
        client = Client.create_client(data)
        logger.info(f"Created new client {data['company_name']}")

        return jsonify({"message": "Created new employee"}), 200
    except Exception as e:
        logger.error({"error": str(e)})
        return jsonify({"error": "Internal Server Error"}), 500

@client.route("/", methods = ["GET"])
def get_all_clients():
    try:
        clients = Client.query.all()

        return jsonify({"data": [client.to_dict() for client in clients]})
    except Exception as e:
        logger.critical("Failed to gather clients", exc_info=e)                
        return jsonify({"error": "Internal Server Error"}), 500

@client.route("/<id>", methods=["GET"])
def get_one_client(id):
    try:
        client = Client.query.get(id)

        if client is None:
            return jsonify({"error": "Client doesn't exist"}), 404

        return jsonify({"data": client.to_dict()}), 200
    except Exception as e:
        logger.critical("Failed to gather client", exc_info=e)                
        return jsonify({"error": "Internal Server Error"}), 500

@client.route("/<id>", methods=["PUT"])
def update_client(id):
    try:
        data = request.json

        if not data:
            return jsonify({"message": "Missing data"}), 400
        
        updated_client = Client.update_client(client_id = id, data=data)

        if updated_client is None:
            return jsonify({"error": "Client not found"})

        
        return jsonify({"message": "Client updated", "data": updated_client.to_dict()})
    except Exception as e:
        logger.critical("Failed to update client", exc_info=e)
        return jsonify({"error": "Internal Server Error"}), 500

@client.route("/<id>", methods = ["DELETE"])
def delete_employee(id):
    try:
        result = Client.delete_client(id)

        if not result:
            return jsonify({"error": "Employee doesnt exist"}), 404
        
        return jsonify({"message": "Employee deleted"})
    except Exception as e:
        logger.critical("Error deleting client", xc_info=e)
        return jsonify({"error": "Internal Server Error"}), 500
