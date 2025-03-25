from io import BytesIO
import pandas as pd
from flask import current_app
from app.models.product import Product
from app.models.employee import Employee
from app.models.employee_survey_assignment import EmployeeSurveyAssignment
from app.utils import logger

class AssignmentService:
    def __init__(self, db):
        self.db = db

    def determine_survey_type(self, survey_doc):
        """
        Determina el tipo de encuesta de forma flexible.
        - Si el documento de encuesta ya especifica survey_type, lo usa.
        - De lo contrario, lo infiere a partir del nombre del producto utilizando un mapeo configurable.
        """
        if "survey_type" in survey_doc and survey_doc["survey_type"]:
            return survey_doc["survey_type"].lower()

        # Si no se especifica, se obtiene el producto y se usa un mapeo
        product_obj = self.db.session.get(Product, survey_doc.get("product_id"))
        if not product_obj:
            raise ValueError("Product not found")

        product_name = product_obj.name.lower()
        mapping = {
            "enex": "enex",
            "360": "360"
        }
        for key, survey_type in mapping.items():
            if key in product_name:
                return survey_type

        raise ValueError("Unsupported survey type")

    def generate_assignment_excel(self, survey_id, client_id):
        """
        Genera un archivo Excel con el organigrama basado en los empleados para el cliente dado.
        
        El archivo contendrá:
          - Detalles del evaluador: employee_number, first_name, last_name, email, position,
            direct_supervisor y functional_supervisor (rellenados automáticamente).
          - Detalles de la encuesta: survey_id y survey_type.
          - Para encuestas ENEX: target_employee_number será None y target_type "company".
          - Para encuestas 360: target_employee_number se deja en blanco (a completar por el cliente) y target_type "employee".
        """
        mongo_db = current_app.mongo_db
        surveys_coll = mongo_db.get_collection("Surveys")
        survey_doc = surveys_coll.find_one({"_id": survey_id})
        if not survey_doc:
            raise ValueError("Survey not found")
        
        survey_type = self.determine_survey_type(survey_doc)
        
        # Se obtienen los empleados asociados al cliente
        employees = self.db.session.query(Employee).filter_by(client_id=client_id).all()
        if not employees:
            raise ValueError("No employees found for the client")
        # Diccionario para búsqueda rápida (para nombres de supervisores)
        employees_dict = {emp.id: emp for emp in employees}
        
        assignment_rows = []
        for emp in employees:
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
            
            # Se utiliza el número de empleado, sin exponer el ID interno
            row = {
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
                row["target_employee_number"] = None
                row["target_type"] = "company"
            elif survey_type == "360":
                row["target_employee_number"] = ""  # El cliente completará este campo con el número de empleado del evaluado
                row["target_type"] = "employee"
            assignment_rows.append(row)
        
        df = pd.DataFrame(assignment_rows)
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="OrganizationChart")
        output.seek(0)
        logger.info(f"Generated assignment Excel with {len(assignment_rows)} rows for survey {survey_id}")
        return output

    def finalize_assignment(self, df):
        """
        Procesa un DataFrame (leído de un archivo Excel) y finaliza las asignaciones
        creando registros en la tabla EmployeeSurveyAssignment.
        
        Ahora, el archivo Excel usa la columna "employee_number" para el evaluador y
        "target_employee_number" para el evaluado. En esta última, se pueden escribir
        múltiples números (separados por comas), generándose una asignación para cada uno.
        """
        assignments = []
        from app.models.employee import Employee

        for idx, row in df.iterrows():
            if pd.notna(row.get("employee_number")) and pd.notna(row.get("survey_id")):
                try:
                    evaluator = self.db.session.query(Employee).filter_by(
                        employee_number=row["employee_number"]
                    ).first()
                    if not evaluator:
                        logger.error(f"No se encontró evaluador con employee_number: {row['employee_number']}")
                        continue

                    raw_targets = row.get("target_employee_number")
                    if pd.isna(raw_targets):
                        logger.error(f"No se especificaron evaluados para el evaluador {row['employee_number']}")
                        continue

                    target_numbers = [num.strip() for num in str(raw_targets).split(",") if num.strip()]

                    for target_num in target_numbers:
                        target_employee = self.db.session.query(Employee).filter_by(
                            employee_number=target_num
                        ).first()
                        if not target_employee:
                            logger.error(f"No se encontró evaluado con employee_number: {target_num}")
                            continue

                        assignment_data = {
                            "employee_id": evaluator.id,
                            "survey_id": row["survey_id"],
                            "survey_type": row["survey_type"],
                            "target_employee_id": target_employee.id,
                            "target_type": row["target_type"]
                        }
                        assignment = EmployeeSurveyAssignment.create_assignment(assignment_data)
                        assignments.append(assignment.to_dict())
                except Exception as inner_e:
                    logger.error(f"Error procesando la fila {idx}: {inner_e}")
        self.db.session.commit()
        return assignments
