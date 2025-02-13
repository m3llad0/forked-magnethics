# app/routes/event_routes.py

from flask import request, jsonify, Blueprint
from datetime import datetime
from app.models.event import Event
from app.utils import logger

event = Blueprint("event", __name__)

@event.route("/", methods=["POST"])
def create_event():
    try:
        data = request.json
        
        # Ajustamos required_fields
        required_fields = [
            "id", 
            "begin_date", 
            "end_date",
            "survey_id",    # Este es el ID de la encuesta en Mongo
            "client_id",
            "survey_type"   # e.g. "360" o "Enex"
        ]

        if not all(field in data for field in required_fields):
            logger.error("Missing fields in body")
            return jsonify({"error": "Missing required fields"}), 400

        event = Event.create_event(data)
        logger.info(
            f"Created new event {data['id']} with survey_id={data['survey_id']} and type={data['survey_type']}"
        )

        return jsonify({
            "message": "Created new event", 
            "data": event.to_dict()
        }), 201
    except Exception as e:
        logger.error({"error": str(e)})
        return jsonify({"error": "Internal Server Error"}), 500

@event.route("/", methods=["GET"])
def get_all_events():
    try:
        events = Event.query.all()
        return jsonify({"data": [event.to_dict() for event in events]}), 200
    except Exception as e:
        logger.critical("Failed to gather events", exc_info=e)
        return jsonify({"error": "Internal Server Error"}), 500

@event.route("/<id>", methods=["GET"])
def get_one_event(id):
    try:
        event = Event.query.get(id)
        if event is None:
            return jsonify({"error": "Event doesn't exist"}), 404
        return jsonify({"data": event.to_dict()}), 200
    except Exception as e:
        logger.critical("Failed to gather event", exc_info=e)
        return jsonify({"error": "Internal Server Error"}), 500

@event.route("/<id>", methods=["PUT"])
def update_event(id):
    try:
        data = request.json
        if not data:
            return jsonify({"message": "Missing data"}), 400
        
        updated_event = Event.update_event(event_id=id, data=data)
        if updated_event is None:
            return jsonify({"error": "Event not found"}), 404
        
        return jsonify({
            "message": "Event updated", 
            "data": updated_event.to_dict()
        }), 200
    except Exception as e:
        logger.critical("Failed to update event", exc_info=e)
        return jsonify({"error": "Internal Server Error"}), 500

@event.route("/<id>", methods=["DELETE"])
def delete_event(id):
    try:
        result = Event.delete_event(id)
        if not result:
            return jsonify({"error": "Event doesn't exist"}), 404
        return jsonify({"message": "Event deleted"}), 200
    except Exception as e:
        logger.critical("Error deleting event", exc_info=e)
        return jsonify({"error": "Internal Server Error"}), 500
