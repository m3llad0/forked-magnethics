import pytest
from flask import Flask
from app.services import db
from app.routes.employee_routes import bp
from app.models.employee import Employee


@pytest.fixture
def app():
    """
    Flask application fixture with in-memory SQLite database.
    """
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)
    app.register_blueprint(bp, url_prefix="/employees")

    with app.app_context():
        db.create_all()

    yield app

    with app.app_context():
        db.drop_all()


@pytest.fixture
def client(app):
    """
    Flask test client fixture.
    """
    return app.test_client()


@pytest.fixture
def sample_employee():
    """
    Sample employee for testing.
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
        "direct_supervisor": None,
        "functional_supervisor": None,
    }


def test_create_employee(client, sample_employee):
    """
    Test creating an employee.
    """
    response = client.post("/employees/", json=sample_employee)
    assert response.status_code == 201
    data = response.get_json()
    assert data["message"] == "Created new employee"
    assert data["data"]["id"] == sample_employee["id"]


def test_get_employees(client, sample_employee):
    """
    Test retrieving all employees.
    """
    # Create an employee first
    client.post("/employees/", json=sample_employee)

    # Retrieve all employees
    response = client.get("/employees/")
    assert response.status_code == 200
    data = response.get_json()
    assert len(data["data"]) == 1
    assert data["data"][0]["id"] == sample_employee["id"]


def test_get_employee(client, sample_employee):
    """
    Test retrieving a specific employee.
    """
    # Create an employee first
    client.post("/employees/", json=sample_employee)

    # Retrieve the employee by ID
    response = client.get(f"/employees/{sample_employee['id']}")
    assert response.status_code == 200
    data = response.get_json()
    assert data["data"]["id"] == sample_employee["id"]


def test_update_employee(client, sample_employee):
    """
    Test updating an employee.
    """
    # Create an employee first
    client.post("/employees/", json=sample_employee)

    # Update the employee
    updated_data = {"first_name": "Jane"}
    response = client.put(f"/employees/{sample_employee['id']}", json=updated_data)
    assert response.status_code == 200
    data = response.get_json()
    assert data["message"] == "Employee updated!"
    assert data["data"]["first_name"] == "Jane"


def test_delete_employee(client, sample_employee):
    """
    Test deleting an employee.
    """
    # Create an employee first
    client.post("/employees/", json=sample_employee)

    # Delete the employee
    response = client.delete(f"/employees/{sample_employee['id']}")
    assert response.status_code == 200
    data = response.get_json()
    assert data["message"] == "Employee deleted successfully"

    # Verify the employee is no longer in the database
    response = client.get(f"/employees/{sample_employee['id']}")
    assert response.status_code == 404
