from flask import request, jsonify, Blueprint
from app.models.employee import Employee
from app.utils import logger

bp = Blueprint("employee", __name__)

@bp.route("/", methods=["POST"])
def create_employee():
    try:
        data = request.json

        required_fields = ["id", "employee_number", "first_name", "last_name_paternal",
                           "last_name_maternal", "position", "hire_date", "email", "phone_number"]
        if not all(field in data for field in required_fields):
            logger.error("Missing fields in body")
            return jsonify({"error": "Missing required fields"}), 400

        employee = Employee.create_employee(data)
        logger.info(f"Created new employee with id {data['id']}")
        return jsonify({"message": "Created new employee", "data": employee.to_dict()}), 201
    except ValueError as ve:
        logger.error(str(ve))
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        logger.critical(f"Failed to create new employee with error {e}")
        return jsonify({"error": "Internal Server Error"}), 500

@bp.route("/", methods=["GET"])
def get_employees():
    try:
         
        # token = request.headers.get("Authorization")
        # Verify token and get user client id to get all the employees of one client
        # Check the user role

        # if role == "CONSULTANT":
        #     employees = Employee.query.all()
        #     return jsonify({"data": employees}), 200

        # if role = "CLIENT":
        #     id = 0
        #     employees = Employee.query.get(id)
        #     return jsonify({"data": employees}), 200

        employees = Employee.query.all()
        return jsonify({"data": [employee.to_dict() for employee in employees]}), 200
    except Exception as e:
        logger.critical("Failed to get employees", exc_info=e)
        return jsonify({"error": "Internal Server Error"}), 500


@bp.route("/<id>", methods=["GET"])
def get_employee(id):
    try:

        employee = Employee.get_employee(id)

        if employee is None:
            return jsonify({"error": "Employee doesn't exist"}), 404
        return jsonify({"data": employee.to_dict()}), 200
    except Exception as e:
        logger.critical("Failed to get employee", exc_info=e)
        return jsonify({"error": "Internal Server Error"}), 500


@bp.route("/<id>", methods=["PUT"])
def update_employee(id):
    try:

        data = request.json
        if not data:
            return jsonify({"message": "Missing data"}), 400

        updated_employee = Employee.update_employee(employee_id=id, data=data)

        if updated_employee is None:
            return jsonify({"error": "Employee doesn't exist"}), 404

        return jsonify({"message": "Employee updated!", "data": updated_employee.to_dict()}), 200
    except Exception as e:
        logger.critical("Failed to update employee", exc_info=e)
        return jsonify({"error": "Internal Server Error"}), 500


@bp.route("/<id>", methods=["DELETE"])
def delete_employee(id):
    try:
        result = Employee.delete_employee(id)
        if not result:
            return jsonify({"error": "Employee doesn't exist"}), 404
        return jsonify({"message": "Employee deleted successfully"}), 200
    except Exception as e:
        logger.critical("Error deleting an employee", exc_info=e)
        return jsonify({"error": "Internal Server Error"}), 500