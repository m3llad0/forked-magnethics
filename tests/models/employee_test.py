import pytest
from app.models.employee import Employee
from app.services import db
from flask import Flask
import datetime


@pytest.fixture
def app():
    """
    Flask application fixture for testing with an in-memory SQLite database.
    """
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"  # Use an in-memory database
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Bind the app to the existing db instance
    db.init_app(app)

    return app


@pytest.fixture
def setup_db(app):
    """
    Fixture to initialize and clean up the database.
    """
    with app.app_context():
        db.create_all()
    yield db
    with app.app_context():
        db.drop_all()


@pytest.fixture
def sample_employee_data():
    """
    Sample employee data for testing.
    """
    return {
        "id": "1",
        "employee_number": 12345,
        "first_name": "John",
        "last_name_paternal": "Doe",
        "last_name_maternal": "Smith",
        "position": "Software Engineer",
        "hire_date": "2022-01-01",
        "email": "john.doe@example.com",
        "phone_number": "555-555-5555",
    }


def test_create_employee(app, setup_db, sample_employee_data):
    """
    Test the creation of an employee.
    """
    with app.app_context():
        employee = Employee.create_employee(sample_employee_data)
        assert employee.id == "1"
        assert employee.first_name == "John"
        assert employee.email == "john.doe@example.com"

        # Verify the employee is in the database
        retrieved = db.session.get(Employee, "1")
        assert retrieved is not None
        assert retrieved.first_name == "John"

def test_to_dict(app, setup_db, sample_employee_data):
    with app.app_context():
        employee = Employee.create_employee(sample_employee_data)
        dict_employee = employee.to_dict()

        assert dict_employee["id"] == "1"
        assert dict_employee["first_name"] == "John"


def test_get_employee(app, setup_db, sample_employee_data):
    """
    Test retrieving an employee by ID.
    """
    with app.app_context():
        Employee.create_employee(sample_employee_data)
        employee = Employee.get_employee("1")
        assert employee is not None
        assert employee.first_name == "John"


def test_update_employee(app, setup_db, sample_employee_data):
    """
    Test updating an employee's information.
    """
    with app.app_context():
        Employee.create_employee(sample_employee_data)

        # Update the employee's first name
        updated_data = {"first_name": "Jane"}
        employee = Employee.update_employee("1", updated_data)
        assert employee is not None
        assert employee.first_name == "Jane"

        # Verify the update in the database
        retrieved = db.session.get(Employee, "1")
        assert retrieved.first_name == "Jane"


def test_delete_employee(app, setup_db, sample_employee_data):
    """
    Test deleting an employee by ID.
    """
    with app.app_context():
        Employee.create_employee(sample_employee_data)

        # Delete the employee
        result = Employee.delete_employee("1")
        assert result is True

        # Verify the employee is no longer in the database
        retrieved = db.session.get(Employee, "1")
        assert retrieved is None
