from app.services import db

class EmployeeSurveyAssignment(db.Model):
    __tablename__ = 'employee_survey_assignments'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    employee_id = db.Column(db.String(36), db.ForeignKey('employees.id'), nullable=False)
    survey_id = db.Column(db.String(255), nullable=False)
    survey_type = db.Column(db.String(50), nullable=False)
    target_employee_id = db.Column(db.String(36), db.ForeignKey('employees.id'), nullable=True)
    target_type = db.Column(db.String(50), nullable=True)  # "employee", "company", etc.


    def __repr__(self):
        return f"<EmployeeSurveyAssignment employee_id={self.employee_id}, survey_id={self.survey_id}>"

    def to_dict(self):
        return {
            "id": self.id,
            "employee_id": self.employee_id,
            "survey_id": self.survey_id,
            "survey_type": self.survey_type,
            "target_employee_id": self.target_employee_id,
            "target_type": self.target_type
        }

    @staticmethod
    def create_assignment(data):
        assignment = EmployeeSurveyAssignment(**data)
        db.session.add(assignment)
        db.session.commit()
        return assignment

    @staticmethod
    def get_assignment(assignment_id):
        return db.session.get(EmployeeSurveyAssignment, assignment_id)

    @staticmethod
    def update_assignment(assignment_id, data):
        assignment = db.session.get(EmployeeSurveyAssignment, assignment_id)
        if not assignment:
            return None
        for key, value in data.items():
            setattr(assignment, key, value)
        db.session.commit()
        return assignment

    @staticmethod
    def delete_assignment(assignment_id):
        assignment = db.session.get(EmployeeSurveyAssignment, assignment_id)
        if not assignment:
            return False
        db.session.delete(assignment)
        db.session.commit()
        return True
