from app.services import db
from datetime import datetime


class Employee(db.Model):
    __tablename__ = 'employee'


    id = db.Column(db.String(255), primary_key=True)
    employee_number = db.Column(db.Integer, nullable=False)
    first_name = db.Column(db.String(255), nullable=False)
    last_name_paternal = db.Column(db.String(255), nullable=False)
    last_name_maternal = db.Column(db.String(255))
    position = db.Column(db.String(255), nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=True)
    hire_date = db.Column(db.Date, nullable=False)
    email = db.Column(db.String(255), nullable=False, unique=True)
    phone_number = db.Column(db.String(255), nullable=True)
    direct_supervisor_id = db.Column(db.String(255), db.ForeignKey('employee.id'), nullable=True)
    functional_supervisor_id = db.Column(db.String(255), db.ForeignKey('employee.id'), nullable=True)

    # Relationships
    client = db.relationship('Client', back_populates='employee', lazy=True)
    event = db.relationship('Event', back_populates='employee', lazy=True)
    
    direct_supervisor = db.relationship(
        'Employee', 
        remote_side=[id], 
        foreign_keys=[direct_supervisor_id],
        backref='direct_reports',
        lazy=True
    )
    functional_supervisor = db.relationship(
        'Employee', 
        remote_side=[id], 
        foreign_keys=[functional_supervisor_id],
        backref='functional_reports',
        lazy=True
    )

    def __repr__(self):
        return f"<Employee {self.first_name} {self.last_name_paternal}>"
    

    def to_dict(self):
        """
        Serialize the Employee model to a dictionary.
        """
        return {
            "id": self.id,
            "employee_number": self.employee_number,
            "first_name": self.first_name,
            "last_name_paternal": self.last_name_paternal,
            "last_name_maternal": self.last_name_maternal,
            "position": self.position,
            "hire_date": str(self.hire_date),  # Convert to string
            "email": self.email,
            "phone_number": self.phone_number,
            "direct_supervisor_id": self.direct_supervisor_id,
            "functional_supervisor_id": self.functional_supervisor_id,
        }


    @staticmethod
    def create_employee(data):
        """
        Creates a new employee record.
        :param data: Dictionary containing employee details.
        :return: Newly created Employee object.
        """
        # Ensure hire_date is a datetime.date object
        if "hire_date" in data and isinstance(data["hire_date"], str):
            data["hire_date"] = datetime.strptime(data["hire_date"], "%Y-%m-%d").date()

        # Validate direct supervisor
        if data.get("direct_supervisor"):
            direct_supervisor = db.session.get(Employee, data["direct_supervisor"])
            if not direct_supervisor:
                raise ValueError(f"Direct supervisor with ID {data['direct_supervisor']} does not exist.")
            data["direct_supervisor_id"] = data["direct_supervisor"]
        else:
            data["direct_supervisor_id"] = None

        # Validate functional supervisor
        if data.get("functional_supervisor"):
            functional_supervisor = db.session.get(Employee, data["functional_supervisor"])
            if not functional_supervisor:
                raise ValueError(f"Functional supervisor with ID {data['functional_supervisor']} does not exist.")
            data["functional_supervisor_id"] = data["functional_supervisor"]
        else:
            data["functional_supervisor_id"] = None

        # Clean up non-column keys
        data.pop("direct_supervisor", None)
        data.pop("functional_supervisor", None)

        # Create and save employee
        employee = Employee(**data)
        db.session.add(employee)
        db.session.commit()
        return employee

    @staticmethod
    def get_employee(employee_id):
        """
        Retrieves an employee record by ID.
        :param employee_id: ID of the employee.
        :return: Employee object or None.
        """
        return db.session.get(Employee, employee_id)

    @staticmethod
    def update_employee(employee_id, data):
        """
        Updates an existing employee record.
        :param employee_id: ID of the employee.
        :param data: Dictionary containing updated fields.
        :return: Updated Employee object or None if not found.
        """
        employee = db.session.get(Employee, employee_id)
        if not employee:
            return None
        for key, value in data.items():
            setattr(employee, key, value)
        db.session.commit()
        return employee

    @staticmethod
    def delete_employee(employee_id):
        """
        Deletes an employee record by ID.
        :param employee_id: ID of the employee.
        :return: True if deleted, False if not found.
        """
        employee = db.session.get(Employee, employee_id)
        if not employee:
            return False
        db.session.delete(employee)
        db.session.commit()
        return True