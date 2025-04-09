from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Fighter(db.Model):
    __tablename__ = 'fighters'
    
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    nickname = db.Column(db.String(100))
    height = db.Column(db.Float)  # Height in inches/cm
    reach = db.Column(db.Float)   # Reach in inches/cm
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    fights_as_fighter1 = db.relationship('Fight', foreign_keys='Fight.fighter1_id', backref='fighter1', lazy=True)
    fights_as_fighter2 = db.relationship('Fight', foreign_keys='Fight.fighter2_id', backref='fighter2', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'nickname': self.nickname,
            'height': self.height,
            'reach': self.reach,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class Event(db.Model):
    __tablename__ = 'events'
    
    id = db.Column(db.Integer, primary_key=True)
    event_name = db.Column(db.String(100), nullable=False)
    event_date = db.Column(db.Date, nullable=False)
    location = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    fights = db.relationship('Fight', backref='event', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'event_name': self.event_name,
            'event_date': self.event_date.isoformat() if self.event_date else None,
            'location': self.location,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class Fight(db.Model):
    __tablename__ = 'fights'
    
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id', ondelete='CASCADE'), nullable=False)
    fighter1_id = db.Column(db.Integer, db.ForeignKey('fighters.id', ondelete='SET NULL'))
    fighter2_id = db.Column(db.Integer, db.ForeignKey('fighters.id', ondelete='SET NULL'))
    weight_class = db.Column(db.String(50))
    scheduled_rounds = db.Column(db.Integer, default=3)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'event_id': self.event_id,
            'fighter1_id': self.fighter1_id,
            'fighter2_id': self.fighter2_id,
            'weight_class': self.weight_class,
            'scheduled_rounds': self.scheduled_rounds,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        } 