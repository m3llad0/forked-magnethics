from app.services import db
import uuid


class Event(db.Model):
    __tablename__ = 'event'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    begin_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    survey_id = db.Column(db.String(255), nullable=True)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'))

    product = db.relationship('Product', back_populates='events', lazy=True)
    client = db.relationship('Client', backref='events', lazy=True)
    employees = db.relationship('Employee', back_populates='event', lazy=True)

    def __repr__(self):
        return f"<Event {self.id} - {self.begin_date} to {self.end_date}>"

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "begin_date": str(self.begin_date),
            "end_date": str(self.end_date),
            "product_id": self.product_id,
            "client_id": self.client_id
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
            raise ValueError("Event not found")
        for key, value in data.items():
            setattr(event, key, value)
        db.session.commit()
        return event

    @staticmethod
    def delete_event(event_id):
        event = db.session.get(Event, event_id)
        if not event:
            raise ValueError("Event not found")
        db.session.delete(event)
        db.session.commit()
        return True
