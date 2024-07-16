from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class Client(db.Model):
    __tablename__ = 'client'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    tier = db.Column(db.Integer, default=0)  # 0: Free, 1: Basic, 2: Professional, 3: Enterprise
    email = db.Column(db.String(120), unique=True, nullable=False)  # Added email to link with Stripe
    is_admin = db.Column(db.Boolean, default=False)  # Add this line
    users = db.relationship('User', backref='client', lazy=True)
    teams = db.relationship('Team', backref='client', lazy=True)
    settings = db.relationship('Settings', backref='client', uselist=False, lazy=True)  # One-to-One relationship


class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=True)  # Make nullable
    is_admin = db.Column(db.Boolean, default=False)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    teams = db.relationship('Team', backref='user', lazy=True)
    auth0_id = db.Column(db.String(120), unique=True, nullable=True)  # Add this line

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

class Team(db.Model):
    id = db.Column(db.Integer, primary_key=True)  # Corrected syntax here
    name = db.Column(db.String(100), nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # user_id can be nullable
    members = db.relationship('TeamMember', backref='team', lazy=True)

class TeamMember(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    surname = db.Column(db.String(100), nullable=False)
    employer_id = db.Column(db.String(100), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)
    evaluations = db.relationship('Rating', backref='team_member', lazy=True)

class Rating(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    team_member_id = db.Column(db.Integer, db.ForeignKey('team_member.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    ability_to_impart_knowledge = db.Column(db.Integer, nullable=False)
    approachable = db.Column(db.Integer, nullable=False)
    necessary_skills = db.Column(db.Integer, nullable=False)
    trained = db.Column(db.Integer, nullable=False)
    absence = db.Column(db.Integer, nullable=False)
    self_motivation = db.Column(db.Integer, nullable=False)
    capacity_for_learning = db.Column(db.Integer, nullable=False)
    adaptability = db.Column(db.Integer, nullable=False)
    total_score = db.Column(db.Integer, nullable=False)
    avg_score = db.Column(db.Float, nullable=False)

class Settings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    red_min = db.Column(db.Integer, default=0)
    red_max = db.Column(db.Integer, default=40)
    orange_min = db.Column(db.Integer, default=41)
    orange_max = db.Column(db.Integer, default=55)
    white_min = db.Column(db.Integer, default=56)
    white_max = db.Column(db.Integer, default=70)
    green_min = db.Column(db.Integer, default=71)
    green_max = db.Column(db.Integer, default=80)
    notify_1_week = db.Column(db.Boolean, default=False)
    notify_3_days = db.Column(db.Boolean, default=True)  # Default value as true
    notify_1_day = db.Column(db.Boolean, default=False)
    frequency_weekly = db.Column(db.Boolean, default=False)
    frequency_bi_weekly = db.Column(db.Boolean, default=False)
    frequency_monthly = db.Column(db.Boolean, default=True)  # Default value as true
    frequency_quarterly = db.Column(db.Boolean, default=False)

    def to_dict(self):
        return {
            'score_ranges': {
                'red': {'min': self.red_min, 'max': self.red_max},
                'orange': {'min': self.orange_min, 'max': self.orange_max},
                'white': {'min': self.white_min, 'max': self.white_max},
                'green': {'min': self.green_min, 'max': self.green_max}
            },
            'email_notifications': {
                '1_week': self.notify_1_week,
                '3_days': self.notify_3_days,
                '1_day': self.notify_1_day
            },
            'rating_frequency': {
                'weekly': self.frequency_weekly,
                'bi_weekly': self.frequency_bi_weekly,
                'monthly': self.frequency_monthly,
                'quarterly': self.frequency_quarterly
            }
        }
