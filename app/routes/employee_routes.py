from flask import request, jsonify, Blueprint
from app.models.employee import Employee
from app.utils import logger
from app.config import CLERK_CLIENT
from app.middleware import postman_consultant_token_required
import pandas as pd
from io import StringIO, BytesIO

bp = Blueprint("employee", __name__)

@bp.route("/", methods=["POST"])
@postman_consultant_token_required
def create_employee():
    try:
        data = request.json

        required_fields = [
            "employee_number", "first_name", "last_name_paternal",
            "last_name_maternal", "position", "hire_date", "email", "phone_number",
            "client_id"  # Organization id to which the employee belongs
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
        employee = Employee.create_employee({
            "id": user.id,
            "employee_number": data["employee_number"],
            "first_name": data["first_name"],
            "last_name_paternal": data["last_name_paternal"],
            "last_name_maternal": data["last_name_maternal"],
            "position": data["position"],
            "hire_date": data["hire_date"],
            "email": data["email"],
            "phone_number": data["phone_number"],
            "client_id": data["client_id"],
            "direct_supervisor_id": data.get("direct_supervisor_id"),
            "functional_supervisor_id": data.get("functional_supervisor_id")
        })

        logger.info(f"Created new employee with id {employee.id}")
        return jsonify({"message": "Created new employee", "data": employee.to_dict()}), 201
    except ValueError as ve:
        logger.error(str(ve))
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
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

@bp.route("/upload", methods=["POST"])
@postman_consultant_token_required
def upload_employees():
    """
    Upload an Excel or CSV file to create employees in bulk.
    The file must include the following columns (adjust as needed):
      - employee_number, first_name, last_name_paternal, last_name_maternal,
        position, hire_date (YYYY-MM-DD), email, phone_number
      - direct_supervisor_id, functional_supervisor_id (optional)
    The client_id is taken from a query parameter (e.g. ?client_id=org_ABC).

    For each row:
      1) Create a Clerk user (with email_address).
      2) Add the user to the specified organization (client_id from query param).
      3) Create the local Employee record in the database.
    """
    try:
        # 1. Retrieve client_id from the query params (e.g., /upload?client_id=org_123)
        client_id = request.args.get("client_id")
        if not client_id:
            return jsonify({"error": "No client_id provided in query parameters"}), 400

        # 2. Check if file was provided
        if "file" not in request.files:
            return jsonify({"error": "No file part in the request"}), 400
        file = request.files["file"]
        if file.filename == "":
            return jsonify({"error": "No selected file"}), 400

        # 3. Determine file type (Excel or CSV) by extension or content
        filename = file.filename.lower()
        if filename.endswith(".xlsx") or filename.endswith(".xls"):
            df = pd.read_excel(file)
        elif filename.endswith(".csv"):
            df = pd.read_csv(file)
        else:
            # Attempt to parse as Excel by default
            try:
                df = pd.read_excel(file)
            except Exception:
                return jsonify({"error": "Unsupported file format. Provide .xlsx, .xls, or .csv."}), 400

        # 4. Validate required columns (excluding client_id since it's in query params)
        required_columns = [
            "employee_number", "first_name", "last_name_paternal",
            "last_name_maternal", "position", "hire_date", "email", "phone_number"
        ]
        missing_cols = [col for col in required_columns if col not in df.columns]
        if missing_cols:
            return jsonify({"error": f"Missing required columns: {missing_cols}"}), 400

        # 5. Iterate over each row, create the Clerk user & local Employee
        created_employees = []
        errors = []
        for idx, row in df.iterrows():
            try:
                # Build a dictionary for the required fields
                data = {
                    "employee_number": row["employee_number"],
                    "first_name": row["first_name"],
                    "last_name_paternal": row["last_name_paternal"],
                    "last_name_maternal": row["last_name_maternal"],
                    "position": row["position"],
                    "hire_date": str(row["hire_date"]),  # Ensure it's a string
                    "email": row["email"],
                    "phone_number": row["phone_number"],
                    "client_id": client_id,  # Use the same org for all employees
                    "direct_supervisor_id": row.get("direct_supervisor_id"),
                    "functional_supervisor_id": row.get("functional_supervisor_id")
                }

                # 5a. Create the user in Clerk
                user = CLERK_CLIENT.users.create(request={
                    "email_address": [data["email"]],
                    "public_metadata": {"user_type": "employee"}
                })

                # 5b. Add the user to the organization
                org = CLERK_CLIENT.organization_memberships.create(
                    organization_id=client_id,
                    user_id=user.id,
                    role="org:member"
                )

                if not user or not org:
                    raise ValueError("Failed to create employee in Clerk (user or org is None)")

                # 5c. Create the local Employee record
                data["id"] = user.id  # Use Clerk user ID as the employee's ID
                employee = Employee.create_employee(data)
                logger.info(f"Created new employee {employee.id} from row {idx}")
                created_employees.append(employee.to_dict())

            except Exception as e:
                # Log the error for this row and continue
                logger.error(f"Error processing row {idx}: {e}")
                errors.append({"row": idx, "error": str(e)})

        # 6. Return summary of created employees and any errors
        return jsonify({
            "message": "Employee upload completed",
            "created_count": len(created_employees),
            "created_employees": created_employees,
            "errors": errors
        }), 200

    except Exception as e:
        logger.critical("Error uploading employees", exc_info=e)
        return jsonify({"error": "Internal Server Error"}), 500