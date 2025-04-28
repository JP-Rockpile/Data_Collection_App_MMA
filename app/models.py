from datetime import datetime
from app import db

class Fighter(db.Model):
    __tablename__ = 'fighters'
    
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    nickname = db.Column(db.String(100))
    height = db.Column(db.Float)  # Height in inches/cm
    reach = db.Column(db.Float)   # Reach in inches/cm
    weight = db.Column(db.Float)  # Weight in pounds/kg
    stance = db.Column(db.String(50))
    DOB = db.Column(db.Date)
    age = db.Column(db.Integer)
    nationality = db.Column(db.String(50))
    wins = db.Column(db.Integer, default=0)
    losses = db.Column(db.Integer, default=0)
    draws = db.Column(db.Integer, default=0)
    no_contests = db.Column(db.Integer, default=0)
    win_streak = db.Column(db.Integer, default=0)
    loss_streak = db.Column(db.Integer, default=0)
    SLpM = db.Column(db.Float)
    Str_Acc = db.Column(db.Float)
    SApM = db.Column(db.Float)
    Str_Def = db.Column(db.Float)
    Takedown_Avg = db.Column(db.Float)
    Takedown_Acc = db.Column(db.Float)
    Takedown_Def = db.Column(db.Float)
    Sub_Avg = db.Column(db.Float)
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
            'weight': self.weight,
            'stance': self.stance,
            'DOB': self.DOB,
            'age': self.age,
            'nationality': self.nationality,
            'wins': self.wins,
            'losses': self.losses,
            'draws': self.draws,
            'no_contests': self.no_contests,
            'win_streak': self.win_streak,
            'loss_streak': self.loss_streak,
            'SLpM': self.SLpM,
            'Str_Acc': self.Str_Acc,
            'SApM': self.SApM,
            'Str_Def': self.Str_Def,
            'Takedown_Avg': self.Takedown_Avg,
            'Takedown_Acc': self.Takedown_Acc,
            'Takedown_Def': self.Takedown_Def,
            'Sub_Avg': self.Sub_Avg,
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
    winner_id = db.Column(db.Integer, db.ForeignKey('fighters.id', ondelete='SET NULL'), nullable=True)
    
    weight_class = db.Column(db.String(50))
    method = db.Column(db.String(100))
    end_round = db.Column(db.Integer)
    end_time = db.Column(db.String(10))
    scheduled_rounds = db.Column(db.Integer, default=3)
    referee = db.Column(db.String(100))
    finish_details = db.Column(db.String(255))
    is_title_fight = db.Column(db.Boolean, default=False)

    # Fight Totals - Fighter 1
    fighter1_knockdowns = db.Column(db.Integer)
    fighter1_sig_strikes_landed = db.Column(db.Integer)
    fighter1_sig_strikes_attempted = db.Column(db.Integer)
    fighter1_sig_strikes_pct = db.Column(db.Float)
    fighter1_total_strikes_landed = db.Column(db.Integer)
    fighter1_total_strikes_attempted = db.Column(db.Integer)
    fighter1_takedowns_landed = db.Column(db.Integer)
    fighter1_takedowns_attempted = db.Column(db.Integer)
    fighter1_takedowns_pct = db.Column(db.Float)
    fighter1_submission_attempts = db.Column(db.Integer)
    fighter1_reversals = db.Column(db.Integer)
    fighter1_control_time_seconds = db.Column(db.Integer)

    # Fight Totals - Fighter 2
    fighter2_knockdowns = db.Column(db.Integer)
    fighter2_sig_strikes_landed = db.Column(db.Integer)
    fighter2_sig_strikes_attempted = db.Column(db.Integer)
    fighter2_sig_strikes_pct = db.Column(db.Float)
    fighter2_total_strikes_landed = db.Column(db.Integer)
    fighter2_total_strikes_attempted = db.Column(db.Integer)
    fighter2_takedowns_landed = db.Column(db.Integer)
    fighter2_takedowns_attempted = db.Column(db.Integer)
    fighter2_takedowns_pct = db.Column(db.Float)
    fighter2_submission_attempts = db.Column(db.Integer)
    fighter2_reversals = db.Column(db.Integer)
    fighter2_control_time_seconds = db.Column(db.Integer)

    # Significant Strikes Breakdown - Fighter 1
    fighter1_sig_strikes_head_landed = db.Column(db.Integer)
    fighter1_sig_strikes_head_attempted = db.Column(db.Integer)
    fighter1_sig_strikes_body_landed = db.Column(db.Integer)
    fighter1_sig_strikes_body_attempted = db.Column(db.Integer)
    fighter1_sig_strikes_leg_landed = db.Column(db.Integer)
    fighter1_sig_strikes_leg_attempted = db.Column(db.Integer)
    fighter1_sig_strikes_distance_landed = db.Column(db.Integer)
    fighter1_sig_strikes_distance_attempted = db.Column(db.Integer)
    fighter1_sig_strikes_clinch_landed = db.Column(db.Integer)
    fighter1_sig_strikes_clinch_attempted = db.Column(db.Integer)
    fighter1_sig_strikes_ground_landed = db.Column(db.Integer)
    fighter1_sig_strikes_ground_attempted = db.Column(db.Integer)

    # Significant Strikes Breakdown - Fighter 2
    fighter2_sig_strikes_head_landed = db.Column(db.Integer)
    fighter2_sig_strikes_head_attempted = db.Column(db.Integer)
    fighter2_sig_strikes_body_landed = db.Column(db.Integer)
    fighter2_sig_strikes_body_attempted = db.Column(db.Integer)
    fighter2_sig_strikes_leg_landed = db.Column(db.Integer)
    fighter2_sig_strikes_leg_attempted = db.Column(db.Integer)
    fighter2_sig_strikes_distance_landed = db.Column(db.Integer)
    fighter2_sig_strikes_distance_attempted = db.Column(db.Integer)
    fighter2_sig_strikes_clinch_landed = db.Column(db.Integer)
    fighter2_sig_strikes_clinch_attempted = db.Column(db.Integer)
    fighter2_sig_strikes_ground_landed = db.Column(db.Integer)
    fighter2_sig_strikes_ground_attempted = db.Column(db.Integer)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'event_id': self.event_id,
            'fighter1_id': self.fighter1_id,
            'fighter2_id': self.fighter2_id,
            'winner_id': self.winner_id,
            'weight_class': self.weight_class,
            'method': self.method,
            'end_round': self.end_round,
            'end_time': self.end_time,
            'scheduled_rounds': self.scheduled_rounds,
            'referee': self.referee,
            'finish_details': self.finish_details,
            'is_title_fight': self.is_title_fight,

            'fighter1_knockdowns': self.fighter1_knockdowns,
            'fighter1_sig_strikes_landed': self.fighter1_sig_strikes_landed,
            'fighter1_sig_strikes_attempted': self.fighter1_sig_strikes_attempted,
            'fighter1_sig_strikes_pct': self.fighter1_sig_strikes_pct,
            'fighter1_total_strikes_landed': self.fighter1_total_strikes_landed,
            'fighter1_total_strikes_attempted': self.fighter1_total_strikes_attempted,
            'fighter1_takedowns_landed': self.fighter1_takedowns_landed,
            'fighter1_takedowns_attempted': self.fighter1_takedowns_attempted,
            'fighter1_takedowns_pct': self.fighter1_takedowns_pct,
            'fighter1_submission_attempts': self.fighter1_submission_attempts,
            'fighter1_reversals': self.fighter1_reversals,
            'fighter1_control_time_seconds': self.fighter1_control_time_seconds,
            
            'fighter2_knockdowns': self.fighter2_knockdowns,
            'fighter2_sig_strikes_landed': self.fighter2_sig_strikes_landed,
            'fighter2_sig_strikes_attempted': self.fighter2_sig_strikes_attempted,
            'fighter2_sig_strikes_pct': self.fighter2_sig_strikes_pct,
            'fighter2_total_strikes_landed': self.fighter2_total_strikes_landed,
            'fighter2_total_strikes_attempted': self.fighter2_total_strikes_attempted,
            'fighter2_takedowns_landed': self.fighter2_takedowns_landed,
            'fighter2_takedowns_attempted': self.fighter2_takedowns_attempted,
            'fighter2_takedowns_pct': self.fighter2_takedowns_pct,
            'fighter2_submission_attempts': self.fighter2_submission_attempts,
            'fighter2_reversals': self.fighter2_reversals,
            'fighter2_control_time_seconds': self.fighter2_control_time_seconds,

            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        } 

class FightRoundStats(db.Model):
    __tablename__ = 'fight_round_stats'

    id = db.Column(db.Integer, primary_key=True)
    fight_id = db.Column(db.Integer, db.ForeignKey('fights.id', ondelete='CASCADE'), nullable=False)
    fighter_id = db.Column(db.Integer, db.ForeignKey('fighters.id', ondelete='CASCADE'), nullable=False) # Link to the specific fighter this row is for
    round_number = db.Column(db.Integer, nullable=False)

    # General Stats for this fighter in this round
    knockdowns = db.Column(db.Integer)
    sig_strikes_landed = db.Column(db.Integer)
    sig_strikes_attempted = db.Column(db.Integer)
    sig_strikes_pct = db.Column(db.Float)
    total_strikes_landed = db.Column(db.Integer)
    total_strikes_attempted = db.Column(db.Integer)
    takedowns_landed = db.Column(db.Integer)
    takedowns_attempted = db.Column(db.Integer)
    takedowns_pct = db.Column(db.Float)
    submission_attempts = db.Column(db.Integer)
    reversals = db.Column(db.Integer)
    control_time_seconds = db.Column(db.Integer) # Store as seconds

    # Significant Strikes Breakdown for this fighter in this round
    sig_strikes_head_landed = db.Column(db.Integer)
    sig_strikes_head_attempted = db.Column(db.Integer)
    sig_strikes_body_landed = db.Column(db.Integer)
    sig_strikes_body_attempted = db.Column(db.Integer)
    sig_strikes_leg_landed = db.Column(db.Integer)
    sig_strikes_leg_attempted = db.Column(db.Integer)
    sig_strikes_distance_landed = db.Column(db.Integer)
    sig_strikes_distance_attempted = db.Column(db.Integer)
    sig_strikes_clinch_landed = db.Column(db.Integer)
    sig_strikes_clinch_attempted = db.Column(db.Integer)
    sig_strikes_ground_landed = db.Column(db.Integer)
    sig_strikes_ground_attempted = db.Column(db.Integer)

    # Define relationships
    fight = db.relationship('Fight', backref=db.backref('round_stats', lazy='dynamic', cascade='all, delete-orphan'))
    fighter = db.relationship('Fighter', backref=db.backref('round_stats', lazy='dynamic'))

    # Ensure a fighter has only one entry per round for a fight
    __table_args__ = (db.UniqueConstraint('fight_id', 'fighter_id', 'round_number', name='_fight_fighter_round_uc'),)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        # Basic dict representation, expand as needed
        return {
            'id': self.id,
            'fight_id': self.fight_id,
            'fighter_id': self.fighter_id,
            'round_number': self.round_number,
            'knockdowns': self.knockdowns,
            'sig_strikes_landed': self.sig_strikes_landed,
            'sig_strikes_attempted': self.sig_strikes_attempted,
            'sig_strikes_pct': self.sig_strikes_pct,
            'total_strikes_landed': self.total_strikes_landed,
            'total_strikes_attempted': self.total_strikes_attempted,
            'takedowns_landed': self.takedowns_landed,
            'takedowns_attempted': self.takedowns_attempted,
            'takedowns_pct': self.takedowns_pct,
            'submission_attempts': self.submission_attempts,
            'reversals': self.reversals,
            'control_time_seconds': self.control_time_seconds,
            'sig_strikes_head_landed': self.sig_strikes_head_landed,
            'sig_strikes_head_attempted': self.sig_strikes_head_attempted,
            'sig_strikes_body_landed': self.sig_strikes_body_landed,
            'sig_strikes_body_attempted': self.sig_strikes_body_attempted,
            'sig_strikes_leg_landed': self.sig_strikes_leg_landed,
            'sig_strikes_leg_attempted': self.sig_strikes_leg_attempted,
            'sig_strikes_distance_landed': self.sig_strikes_distance_landed,
            'sig_strikes_distance_attempted': self.sig_strikes_distance_attempted,
            'sig_strikes_clinch_landed': self.sig_strikes_clinch_landed,
            'sig_strikes_clinch_attempted': self.sig_strikes_clinch_attempted,
            'sig_strikes_ground_landed': self.sig_strikes_ground_landed,
            'sig_strikes_ground_attempted': self.sig_strikes_ground_attempted,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        } 