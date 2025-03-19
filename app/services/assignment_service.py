from io import BytesIO
import pandas as pd
from flask import current_app
# from app.services import db
from app.models.product import Product
from app.models.employee import Employee
from app.models.employee_survey_assignment import EmployeeSurveyAssignment
from app.utils import logger

class AssignmentService:
    def __init__(self, db):
            self.db = db
    def determine_survey_type(self, survey_doc):
        """
        Determines the survey type in a flexible manner.
        - If the survey document already specifies a survey_type, use it.
        - Otherwise, infer from the product name using a configurable mapping.
        """


        # Use survey_type from the document if present.
        if "survey_type" in survey_doc and survey_doc["survey_type"]:
            return survey_doc["survey_type"].lower()

        # Otherwise, retrieve the product and use a mapping.
        product_obj = self.db.session.get(Product, survey_doc.get("product_id"))
        if not product_obj:
            raise ValueError("Product not found")

        product_name = product_obj.name.lower()
        # Mapping to determine survey type based on keywords in product name.
        mapping = {
            "enex": "enex",
            "360": "360"
            # Add more mappings here if needed in the future.
        }
        for key, survey_type in mapping.items():
            if key in product_name:
                return survey_type

        raise ValueError("Unsupported survey type")

    def generate_assignment_excel(self, survey_id, client_id):
        """
        Generates an Excel file containing an organization chart based on employees for the given client.
        This file will include:
            - Employee details (employee_id, employee_number, first_name, last_name, email, position)
            - Their direct and functional supervisor names
            - Survey details (survey_id, survey_type)
            - For ENEX surveys: target_employee_id is None, target_type is "company"
            - For 360 surveys: target_employee_id is left blank and target_type is "employee"
        The client can then modify this file to select who will answer the surveys.
        """
        mongo_db = current_app.mongo_db
        surveys_coll = mongo_db.get_collection("Surveys")
        survey_doc = surveys_coll.find_one({"_id": survey_id})
        if not survey_doc:
            raise ValueError("Survey not found")
        
        # Determine survey type using the new flexible method.
        survey_type = self.determine_survey_type(survey_doc)
        
        # Fetch employees for the client
        employees = self.db.session.query(Employee).filter_by(client_id=client_id).all()
        if not employees:
            raise ValueError("No employees found for the client")
        # Build a dictionary for quick lookup (for supervisor names)
        employees_dict = {emp.id: emp for emp in employees}
        
        assignment_rows = []
        for emp in employees:
            # Get supervisor names (if available)
            direct_sup_name = ""
            if emp.direct_supervisor_id:
                direct_sup = employees_dict.get(emp.direct_supervisor_id) or self.db.session.get(Employee, emp.direct_supervisor_id)
                if direct_sup:
                    direct_sup_name = f"{direct_sup.first_name} {direct_sup.last_name_paternal}"
            func_sup_name = ""
            if emp.functional_supervisor_id:
                func_sup = employees_dict.get(emp.functional_supervisor_id) or self.db.session.get(Employee, emp.functional_supervisor_id)
                if func_sup:
                    func_sup_name = f"{func_sup.first_name} {func_sup.last_name_paternal}"
            
            row = {
                "employee_id": emp.id,
                "employee_number": emp.employee_number,
                "first_name": emp.first_name,
                "last_name": f"{emp.last_name_paternal} {emp.last_name_maternal or ''}".strip(),
                "email": emp.email,
                "position": emp.position,
                "direct_supervisor": direct_sup_name,
                "functional_supervisor": func_sup_name,
                "survey_id": survey_id,
                "survey_type": survey_type,
            }
            if survey_type == "enex":
                row["target_employee_id"] = None
                row["target_type"] = "company"
            elif survey_type == "360":
                row["target_employee_id"] = ""  # To be filled by the client manually
                row["target_type"] = "employee"
            assignment_rows.append(row)
        
        # Create a DataFrame and write to Excel in memory
        df = pd.DataFrame(assignment_rows)
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="OrganizationChart")
        output.seek(0)
        logger.info(f"Generated assignment Excel with {len(assignment_rows)} rows for survey {survey_id}")
        return output

    def finalize_assignment(self, df):
        """
        Accepts a DataFrame read from an uploaded Excel file and finalizes the assignments
        by creating records in the EmployeeSurveyAssignment table.
        """
        assignments = []
        for idx, row in df.iterrows():
            if pd.notna(row["target_employee_id"]) and pd.notna(row["survey_id"]):
                print(row)
                try:
                    assignment_data = {
                        "employee_id": row["employee_id"],
                        "survey_id": row["survey_id"],
                        "survey_type": row["survey_type"],
                        "target_employee_id": row["target_employee_id"],
                        "target_type": row["target_type"]
                    }
                    assignment = EmployeeSurveyAssignment.create_assignment(assignment_data)
                    assignments.append(assignment.to_dict())
                except Exception as inner_e:
                    logger.error(f"Error processing row {idx}: {inner_e}")
        self.db.session.commit()
        return assignments
