from flask import request, jsonify, Blueprint
from app.models import Client
from app.utils import logger
from app.config import CLERK_CLIENT
from app.middleware import postman_consultant_token_required

client = Blueprint("client", __name__)

@client.route("/", methods = ["POST"])
@postman_consultant_token_required
def create_client():
    try:
        data = request.json

        required_fields = [
            "company_name", "business_name", "group_name", 
            "holding_group", "country", "primary_contact", 
            "contact_email", "contact_phone"
        ]
        if not all(field in data for field in required_fields):
            logger.error("Missing required fields in body")
            return jsonify({"error": "Missing required fields"}), 400

        # Create the organization in Clerk.
        # Per the Clerk documentation, email_address must be passed as a list.
        org_response = CLERK_CLIENT.organizations.create(request={
            "name": data["company_name"],
            "email_address": [data["contact_email"]],
        })


        if not org_response.id:
            logger.error("No organization ID returned from Clerk")
            return jsonify({"error": "Failed to create organization in Clerk"}), 500

        new_client = Client.create_client({
            "id": org_response.id,
            "company_name": data["company_name"],
            "business_name": data["business_name"],
            "group_name": data["group_name"],
            "holding_group": data["holding_group"],
            "country": data["country"],
            "primary_contact": data["primary_contact"],
            "contact_email": data["contact_email"],
            "contact_phone": data["contact_phone"]
        })

        logger.info(f"Created new client {data['company_name']} with ID {org_response.id}")
        return jsonify({"message": "Client created", "data": new_client.to_dict()}), 201

    except Exception as e:
        logger.error({"error": str(e)})
        return jsonify({"error": "Internal Server Error"}), 500


@client.route("/", methods=["GET"])
@postman_consultant_token_required
def get_all_clients():
    try:
        clients = Client.query.all()
        return jsonify([client.to_dict() for client in clients]), 200
    except Exception as e:
        logger.critical("Failed to gather clients", exc_info=e)
        return jsonify({"error": "Internal Server Error"}), 500

@client.route("/<id>", methods=["GET"])
@postman_consultant_token_required
def get_one_client(id):
    try:
        client_obj = Client.query.get(id)
        if client_obj is None:
            return jsonify({"error": "Client doesn't exist"}), 404
        return jsonify(client_obj.to_dict()), 200
    except Exception as e:
        logger.critical("Failed to gather client", exc_info=e)
        return jsonify({"error": "Internal Server Error"}), 500


@client.route("/<id>", methods=["PUT"])
@postman_consultant_token_required
def update_client(id):
    try:
        data = request.json
        if not data:
            return jsonify({"message": "Missing data"}), 400
        updated_client = Client.update_client(client_id=id, data=data)
        if updated_client is None:
            return jsonify({"error": "Client not found"}), 404
        return jsonify({"message": "Client updated", "data": updated_client.to_dict()}), 200
    except Exception as e:
        logger.critical("Failed to update client", exc_info=e)
        return jsonify({"error": "Internal Server Error"}), 500


@client.route("/<id>", methods=["DELETE"])
@postman_consultant_token_required
def delete_client(id):
    try:
        result = Client.delete_client(id)
        if not result:
            return jsonify({"error": "Client doesn't exist"}), 404
        return jsonify({"message": "Client deleted"}), 200
    except Exception as e:
        logger.critical("Error deleting client", exc_info=e)
        return jsonify({"error": "Internal Server Error"}), 500
