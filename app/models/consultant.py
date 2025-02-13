from app.services import db
from datetime import datetime

class Consultant(db.Model):
    __tablename__ = 'consultant'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    lastname = db.Column(db.String(255), nullable=False)
    
    def __repr__(self):
        return f"<Consultant {self.name} {self.lastname}>"
    
    def to_dict(self):
        return {"id": self.id, "name": self.name, "lastname": self.lastname}
    
    @staticmethod
    def create_consultant(data):
        consultant = Consultant(**data)
        db.session.add(consultant)
        db.session.commit()
        return consultant
    
    @staticmethod
    def update_consultant(consultant_id, data):
        consultant = db.session.get(Consultant, consultant_id)
        if not consultant:
            return None
        for key, value in data.items():
            setattr(consultant, key, value)
        db.session.commit()
        return consultant
    
    @staticmethod
    def delete_consultant(consultant_id):
        consultant = db.session.get(Consultant, consultant_id)
        if not consultant:
            return False
        db.session.delete(consultant)
        db.session.commit()
        return True