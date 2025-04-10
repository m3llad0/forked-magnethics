# app/models/client.py

from app.services import db
from datetime import datetime
import enum


class ClientStatus(enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"


class Client(db.Model):
    __tablename__ = 'client'
    
    id = db.Column(db.String(255), primary_key=True)
    company_name = db.Column(db.String(255), nullable=False)
    company_rfc = db.Column(db.String(255), unique=True, nullable=False)
    business_name = db.Column(db.String(255), nullable=False)
    group_name = db.Column(db.String(255))
    holding_group = db.Column(db.String(255))
    country = db.Column(db.String(100))
    primary_contact = db.Column(db.String(255))
    contact_email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    contact_phone = db.Column(db.String(50))
    account_executive_id = db.Column(db.String(255), db.ForeignKey('consultant.id'), index=True)
    status = db.Column(db.Enum(ClientStatus), default=ClientStatus.ACTIVE)
    registration_date = db.Column(db.Date, default=datetime.utcnow)
    last_modification_date = db.Column(db.Date, default=datetime.utcnow, onupdate=datetime.utcnow)

    employees = db.relationship('Employee', back_populates='client', lazy=True)

    def __repr__(self):
        return f"<Client {self.company_name}>"

    def to_dict(self):
        return {
            "id": self.id,
            "company_name": self.company_name,
            "business_name": self.business_name,
            "rfc": self.company_rfc,
            "group_name": self.group_name,
            "holding_group": self.holding_group,
            "contact_email": self.contact_email,
            "country": self.country,
            "primary_contact": self.primary_contact,
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
            raise ValueError("Client not found")
        for key, value in data.items():
            setattr(client, key, value)
        db.session.commit()
        return client

    @staticmethod
    def delete_client(client_id):
        client = db.session.get(Client, client_id)
        if not client:
            raise ValueError("Client not found")
        db.session.delete(client)
        db.session.commit()
        return True
