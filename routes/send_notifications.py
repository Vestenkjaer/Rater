import os
import requests
import time
from datetime import datetime, timedelta
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message

# Initialize Flask and SQLAlchemy
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER')
app.config['MAIL_PORT'] = os.getenv('MAIL_PORT')
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
app.config['MAIL_USE_SSL'] = os.getenv('MAIL_USE_SSL', 'false').lower() in ['true', 'on', '1']
db = SQLAlchemy(app)
mail = Mail(app)

class Client(db.Model):
    __tablename__ = 'client'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    settings = db.relationship('Settings', backref='client', uselist=False, lazy=True)

class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)

class Settings(db.Model):
    __tablename__ = 'settings'
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    notify_1_week = db.Column(db.Boolean, default=False)
    notify_3_days = db.Column(db.Boolean, default=True)
    notify_1_day = db.Column(db.Boolean, default=False)
    frequency_weekly = db.Column(db.Boolean, default=False)
    frequency_bi_weekly = db.Column(db.Boolean, default=False)
    frequency_monthly = db.Column(db.Boolean, default=True)
    frequency_quarterly = db.Column(db.Boolean, default=False)

def get_clients_to_notify():
    today = datetime.now().date()
    day_of_month = today.day

    if day_of_month == 18:
        notify_date = '1_week'
    elif day_of_month == 22:
        notify_date = '3_days'
    elif day_of_month == 24:
        notify_date = '1_day'
    else:
        return []

    clients = Settings.query.filter_by(**{f'notify_{notify_date}': True}).all()
    return clients

def send_notification_email(user_email):
    msg = Message('Upcoming Rating Reminder',
                  recipients=[user_email])
    msg.html = '''
    <p>Dear User,</p>

    <p>This is a reminder that your team rating is due on the 25th of this month.</p>

    <p>You can perform the rating using one of the following links:</p>
    <ul>
        <li><a href="http://www.raterware.com">Raterware (Production)</a></li>
        <li><a href="https://raterware-8e1bd4f1708e.herokuapp.com/">Raterware (Testing)</a></li>
    </ul>

    <p>Best regards,<br>
    The Raterware Team</p>
    '''
    mail.send(msg)

def main():
    with app.app_context():
        clients = get_clients_to_notify()
        for client_settings in clients:
            client = Client.query.get(client_settings.client_id)
            users = User.query.filter_by(client_id=client.id).all()
            for user in users:
                send_notification_email(user.email)

if __name__ == '__main__':
    main()
