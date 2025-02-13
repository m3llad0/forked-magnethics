from app.services import db
from datetime import datetime

class Client(db.Model):
    __tablename__ = 'client'
    
    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(255), nullable=False)
    business_name = db.Column(db.String(255), nullable=False)
    group_name = db.Column(db.String(255))
    holding_group = db.Column(db.String(255))
    country = db.Column(db.String(100))
    primary_contact = db.Column(db.String(255))
    contact_email = db.Column(db.String(255), unique=True)
    contact_phone = db.Column(db.String(50))
    account_executive_id = db.Column(db.Integer, db.ForeignKey('consultant.id'))
    status = db.Column(db.String(50))
    registration_date = db.Column(db.Date, default=datetime.utcnow)
    last_modification_date = db.Column(db.Date, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relación con Consultant
    account_executive = db.relationship('Consultant', backref='clients')
    
    # NUEVA RELACIÓN INVERSA hacia Employee (employee.py)
    employees = db.relationship(
        "Employee",
        back_populates="client",
        lazy=True
    )

    def __repr__(self):
        return f"<Client {self.company_name}>"
    
    def to_dict(self):
        return {
            "id": self.id,
            "company_name": self.company_name,
            "business_name": self.business_name,
            "country": self.country,
            "primary_contact": self.primary_contact
        }
    
    @staticmethod
    def create_client(data):
        client = Client(**data)
        db.session.add(client)
        db.session.commit()
        return client
    
    @staticmethod
    def update_client(client_id, data):
        client = db.session.get(Client, client_id)
        if not client:
            return None
        for key, value in data.items():
            setattr(client, key, value)
        db.session.commit()
        return client
    
    @staticmethod
    def delete_client(client_id):
        client = db.session.get(Client, client_id)
        if not client:
            return False
        db.session.delete(client)
        db.session.commit()
        return True
