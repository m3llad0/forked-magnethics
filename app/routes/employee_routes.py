from flask import request, jsonify, Blueprint, g
from app.models import Employee, Client
from app.services import db
from app.utils import logger
from app.config import CLERK_CLIENT
from app.middleware import postman_consultant_token_required, token_required
import pandas as pd
import time

bp = Blueprint("employee", __name__)

@bp.route("/", methods=["POST"])
@postman_consultant_token_required
def create_employee():
    try:
        data = request.json

        required_fields = ["employee_number", "first_name","last_name_paternal",
                           "last_name_maternal","employee_type","birth_date","sex",
                           "country","region","city","herichary_level","position",
                           "area","department","hire_date","email","phone_number",
                           "floor","direct_supervisor_id","functional_supervisor_id"
                           ]
        if not all(field in data for field in required_fields):
            logger.error("Missing required fields in body")
            return jsonify({"error": "Missing required fields"}), 400

        
        user = CLERK_CLIENT.users.create(request={
                "email_address": [data["email"]],
                "public_metadata": {
                    "user_type": "employee",
                }
            })

        org = CLERK_CLIENT.organization_memberships.create(
                organization_id=data["client_id"],
                user_id=user.id,
                role="org:member"
            )
        
        if user is None or org is None:
            logger.error("Failed to create new employee in Clerk")
            return jsonify({"error": "Failed to create new employee"}), 400

        # Log the created IDs using f-string
        logger.info(f"Created Clerk user id: {user.id}, organization membership id: {org.id}")

        # Create the local Employee record using the Clerk user id.
        data["id"] = user.id  # Add the Clerk user ID as the employee's ID
        employee = Employee.create_employee(**data)

        logger.info(f"Created new employee with id {employee.id}")
        return jsonify({"message": "Created new employee", "data": employee.to_dict()}), 201
    except ValueError as ve:
        logger.error(str(ve))
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        # CLERK_CLIENT.organization_memberships.delete(org.id)
        CLERK_CLIENT.users.delete(user.id)
        logger.critical(f"Failed to create new employee with error {e}")
        return jsonify({"error": "Internal Server Error"}), 500

@bp.route("/", methods=["GET"])
@postman_consultant_token_required
def get_employees():
    try:
        employees = Employee.query.all()
        return jsonify({"data": [employee.to_dict() for employee in employees]}), 200
    except Exception as e:
        logger.critical("Failed to get employees", exc_info=e)
        return jsonify({"error": "Internal Server Error"}), 500

@bp.route("/<id>", methods=["GET"])
@postman_consultant_token_required
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
@postman_consultant_token_required
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
@postman_consultant_token_required
def delete_employee(id):
    try:
        result = Employee.delete_employee(id)
        if not result:
            return jsonify({"error": "Employee doesn't exist"}), 404
        return jsonify({"message": "Employee deleted successfully"}), 200
    except Exception as e:
        logger.critical("Error deleting an employee", exc_info=e)
        return jsonify({"error": "Internal Server Error"}), 500

@bp.route("/info", methods=["GET"])
@token_required()
def get_employee_info():
    try:
        employee_id = g.user_id
        if not employee_id:
            return jsonify({"error": "Missing employee ID"}), 400

        employee = Employee.query.filter_by(id=employee_id).first()
        if not employee:
            return jsonify({"error": "Employee not found"}), 404

        return jsonify(employee.to_dict()), 200
    except Exception as e:
        logger.critical("Failed to get employee info", exc_info=e)
        return jsonify({"error": "Internal Server Error"}), 500

@bp.route("/upload/<client_id>", methods=["POST"])
@postman_consultant_token_required
def upload_employees(client_id):
    """
    Upload an Excel or CSV file to create employees in bulk.
    """
    try:
        client = db.session.get(Client, client_id)
        if not client:
            return jsonify({"error": f"Client with ID '{client_id}' does not exist"}), 400

        if "file" not in request.files:
            return jsonify({"error": "No file part in the request"}), 400

        file = request.files["file"]
        if file.filename == "":
            return jsonify({"error": "No selected file"}), 400

        filename = file.filename.lower()
        if filename.endswith(".xlsx") or filename.endswith(".xls"):
            df = pd.read_excel(file)
        elif filename.endswith(".csv"):
            df = pd.read_csv(file)
        else:
            try:
                df = pd.read_excel(file)
            except Exception:
                return jsonify({"error": "Unsupported file format. Provide .xlsx, .xls, or .csv."}), 400

        column_map = {
            "ID EMPLEADO": "employee_number",
            "NOMBRES EMPLEADO": "first_name",
            "APELLIDO PATERNO": "last_name_paternal",
            "APELLIDO MATERNO": "last_name_maternal",
            "TIPO DE EMPLEADO": "employee_type",
            "FECHA NACIMIENTO": "birth_date",
            "GÉNERO": "sex",
            "PAÍS": "country",
            "REGIÓN": "region",
            "LOCALIDAD": "city",
            "NIVEL JERÁRQUICO": "herichary_level",
            "AREA": "area",
            "DEPTO": "department",
            "FECHA INGRESO": "hire_date",
            "EMAIL": "email",
            "WHATSAPP": "phone_number",
            "PLANTA": "floor",
            "DIRECC": "position",
            "ID EMPLEADO JEFE DIRECTO": "direct_supervisor_number",
            "ID EMPLEADO JEFE FUNCIONAL": "functional_supervisor_number"
        }

        missing_cols = [col for col in column_map if col not in df.columns]
        if missing_cols:
            return jsonify({"error": f"Missing required columns: {missing_cols}"}), 400

        number_to_clerk_id = {}
        created = []
        errors = []
        created_employees = []

        for idx, row in df.iterrows():
            try:
                logger.info(f"Processing row {idx + 1} {row}")
                data = {new: row[old] for old, new in column_map.items()}

                for k in ["direct_supervisor_number", "functional_supervisor_number"]:
                    val = data.get(k)
                    if pd.isna(val) or str(val).strip() == "":
                        data[k] = None
                    else:
                        data[k] = str(val).split(".")[0]  # always store as string

                data["client_id"] = client_id

                user = CLERK_CLIENT.users.create(request={
                    "email_address": [data["email"]],
                    "public_metadata": {"user_type": "employee"}
                })

                time.sleep(0.8)

                if not user:
                    raise ValueError("Failed to create Clerk user")

                data["id"] = user.id
                created_employees.append(user.id)

                number_to_clerk_id[str(data["employee_number"])] = user.id

                sup_data = {
                    "direct_number": data.pop("direct_supervisor_number", None),
                    "func_number": data.pop("functional_supervisor_number", None),
                }

                employee = Employee.create_employee(data)  # must not commit
                created.append({**sup_data, "employee": employee})

            except Exception as e:
                logger.error(f"Error processing row {idx}: {e}")
                errors.append({"row": idx, "error": str(e)})

        for item in created:
            emp = item["employee"]
            direct = item.get("direct_number")
            func = item.get("func_number")

            if direct and direct in number_to_clerk_id:
                emp.direct_supervisor_id = number_to_clerk_id[direct]
            if func and func in number_to_clerk_id:
                emp.functional_supervisor_id = number_to_clerk_id[func]

            db.session.add(emp)
        db.session.commit()
        return jsonify({
            "message": "Employee upload completed",
            "created_count": len(created),
            "created_employees": [e["employee"].to_dict() for e in created],
            "errors": errors
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.critical("Error uploading employees", exc_info=e)
        for clerk_id in created_employees:
            print(f"Attempting to delete Clerk user {clerk_id}")
            try:
                CLERK_CLIENT.users.delete(clerk_id)
                logger.warning(f"Rolled back Clerk user: {clerk_id}")
            except Exception as delete_err:
                logger.error(f"Failed to delete Clerk user {clerk_id}: {delete_err}")
        return jsonify({"error": "Internal Server Error"}), 500