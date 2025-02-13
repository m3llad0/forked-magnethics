# app/models/event.py

from app.services import db
from datetime import datetime

class Event(db.Model):
    __tablename__ = 'event'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    begin_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    survey_id = db.Column(db.String(255), nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    survey_type = db.Column(db.String(50), nullable=False)


    client = db.relationship('Client', backref='events')

    def __repr__(self):
        return f"<Event {self.id} - {self.begin_date} to {self.end_date}>"
    
    def to_dict(self):
        return {
            "id": self.id,
            "begin_date": str(self.begin_date),
            "end_date": str(self.end_date),
            "survey_id": self.survey_id,    # <-- Es solo un string
            "client_id": self.client_id,
            "survey_type": self.survey_type
        }
    
    @staticmethod
    def create_event(data):
        event = Event(**data)
        db.session.add(event)
        db.session.commit()
        return event
    
    @staticmethod
    def update_event(event_id, data):
        event = db.session.get(Event, event_id)
        if not event:
            return None
        for key, value in data.items():
            setattr(event, key, value)
        db.session.commit()
        return event
    
    @staticmethod
    def delete_event(event_id):
        event = db.session.get(Event, event_id)
        if not event:
            return False
        db.session.delete(event)
        db.session.commit()
        return True
