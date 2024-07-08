from flask import Blueprint, request, jsonify, session, render_template, current_app
from models import db, User, Team, Client, Settings
import requests
import json
import os
import secrets
from mail import mail  # Import mail from mail.py
from flask_mail import Message

setup_bp = Blueprint('setup', __name__)

@setup_bp.route('/', methods=['GET'])
def setup():
    return render_template('setup.html')

@setup_bp.route('/get_users', methods=['GET'])
def get_users():
    client_id = session.get('client_id')
    if not client_id:
        return jsonify({'error': 'Client ID not found in session'}), 401

    users = User.query.filter_by(client_id=client_id).all()
    users_data = []
    for user in users:
        teams = Team.query.filter_by(client_id=client_id, user_id=user.id).all()
        users_data.append({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'teams': [{'id': team.id, 'name': team.name} for team in teams],
            'auth0_id': user.auth0_id  # Use auth0_id from User model
        })

    return jsonify({'users': users_data})

@setup_bp.route('/get_teams', methods=['GET'])
def get_teams():
    client_id = session.get('client_id')
    if not client_id:
        return jsonify({'error': 'Client ID not found in session'}), 401

    teams = Team.query.filter_by(client_id=client_id).all()
    teams_data = [{'id': team.id, 'name': team.name} for team in teams]
    return jsonify({'teams': teams_data})

@setup_bp.route('/get_settings', methods=['GET'])
def get_settings():
    client_id = session.get('client_id')
    if not client_id:
        return jsonify({'error': 'Client ID not found in session'}), 401

    settings = Settings.query.filter_by(client_id=client_id).first()
    if settings:
        return jsonify({'settings': settings.to_dict()})
    else:
        return jsonify({'settings': None})

@setup_bp.route('/save_settings', methods=['POST'])
def save_settings():
    client_id = session.get('client_id')
    if not client_id:
        return jsonify({'error': 'Client ID not found in session'}), 401

    data = request.json
    settings = Settings.query.filter_by(client_id=client_id).first()
    if not settings:
        settings = Settings(client_id=client_id)

    settings.red_min = data['score_ranges']['red']['min']
    settings.red_max = data['score_ranges']['red']['max']
    settings.orange_min = data['score_ranges']['orange']['min']
    settings.orange_max = data['score_ranges']['orange']['max']
    settings.white_min = data['score_ranges']['white']['min']
    settings.white_max = data['score_ranges']['white']['max']
    settings.green_min = data['score_ranges']['green']['min']
    settings.green_max = data['score_ranges']['green']['max']
    settings.notify_1_week = data['email_notifications']['1_week']
    settings.notify_3_days = data['email_notifications']['3_days']
    settings.notify_1_day = data['email_notifications']['1_day']
    settings.frequency_weekly = data['rating_frequency']['weekly']
    settings.frequency_bi_weekly = data['rating_frequency']['bi_weekly']
    settings.frequency_monthly = data['rating_frequency']['monthly']
    settings.frequency_quarterly = data['rating_frequency']['quarterly']

    db.session.add(settings)
    db.session.commit()

    return jsonify({'status': 'success', 'settings': data})

@setup_bp.route('/create_user', methods=['POST'])
def create_user():
    data = request.json
    username = data.get('username')
    email = data.get('email')
    client_id = session.get('client_id')
    if not client_id:
        current_app.logger.error('Client ID not found in session')
        return jsonify({'error': 'Client ID not found in session'}), 401

    # Check if user already exists
    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        current_app.logger.error('User with this email already exists')
        return jsonify({'error': 'User with this email already exists'}), 400

    # Create Auth0 user and get auth0_id
    try:
        auth0_id, temp_password = create_auth0_user(email)
    except Exception as e:
        current_app.logger.error(f'Error creating Auth0 user: {e}')
        return jsonify({'error': str(e)}), 500

    # Store user with auth0_id in local database
    user = User(username=username, email=email, client_id=client_id, auth0_id=auth0_id)
    db.session.add(user)
    db.session.commit()

    team_ids = data.get('teams', [])
    for team_id in team_ids:
        team = Team.query.get(team_id)
        if team and team.client_id == client_id:
            team.user_id = user.id
            db.session.commit()

    send_password_email(email, temp_password)  # Send email with temporary password

    current_app.logger.info(f'User {username} created successfully with Auth0 ID {auth0_id}')
    return jsonify({'status': 'success'})

def create_auth0_user(email):
    auth0_domain = os.getenv('AUTH0_DOMAIN')
    auth0_token = os.getenv('AUTH0_MANAGEMENT_API_TOKEN')
    headers = {
        'Authorization': f'Bearer {auth0_token}',
        'Content-Type': 'application/json'
    }

    # Create user in Auth0
    temp_password = secrets.token_urlsafe(16)  # Generate a temporary password
    payload = {
        "email": email,
        "password": temp_password,  # Include the password field
        "connection": "Username-Password-Authentication",
        "email_verified": False
    }
    
    # Log the payload
    current_app.logger.info(f"Creating Auth0 user with payload: {payload}")
    
    response = requests.post(f'https://{auth0_domain}/api/v2/users', headers=headers, json=payload)
    
    # Log detailed response information
    current_app.logger.info(f"Response status code: {response.status_code}")
    current_app.logger.info(f"Response content: {response.content}")
    
    if response.status_code != 201:
        raise Exception(f"Failed to create Auth0 user: {response.content.decode()}")
    
    auth0_user = response.json()
    current_app.logger.info(f"Auth0 user created: {auth0_user}")

    # Send verification email
    payload = {
        "user_id": auth0_user["user_id"]
    }
    response = requests.post(f'https://{auth0_domain}/api/v2/jobs/verification-email', headers=headers, json=payload)
    response.raise_for_status()
    current_app.logger.info(f"Verification email sent: {response.json()}")

    return auth0_user["user_id"], temp_password

def send_password_email(email, password):
    msg = Message('Your New Account Password',
                  recipients=[email])
    msg.body = f'''
    Welcome to Raterware!

    Your temporary password is: {password}

    Please visit the following link to log in with your new password:
    http://raterware.com/login

    
    Best regards,
    The Raterware Team
    '''
    try:
        mail.send(msg)
        current_app.logger.info(f"Password email sent to {email}")
    except Exception as e:
        current_app.logger.error(f"Failed to send email: {e}")

def send_deletion_email(email):
    msg = Message('Account Deletion Notice',
                  recipients=[email])
    msg.body = '''
    Dear User,

    You have been removed from Raterware.

    If you have any questions or believe this is a mistake, please contact your manager or your Raterware responsible contact.

    Best regards,
    The Raterware Team
    '''
    try:
        mail.send(msg)
        current_app.logger.info(f"Deletion email sent to {email}")
    except Exception as e:
        current_app.logger.error(f"Failed to send deletion email: {e}")

@setup_bp.route('/edit_user/<auth0_id>/<int:user_id>', methods=['POST'])
def edit_user(auth0_id, user_id):
    data = request.json
    username = data.get('username')
    email = data.get('email')
    client_id = session.get('client_id')
    if not client_id:
        return jsonify({'error': 'Client ID not found in session'}), 401

    user = User.query.filter_by(id=user_id, client_id=client_id).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    user.username = username
    user.email = email
    db.session.commit()

    # Update team assignments
    team_ids = data.get('teams', [])
    for team in Team.query.filter_by(user_id=user.id, client_id=client_id).all():
        team.user_id = None
    db.session.commit()

    for team_id in team_ids:
        team = Team.query.get(team_id)
        if team and team.client_id == client_id:
            team.user_id = user.id
            db.session.commit()

    return jsonify({'status': 'success'})

@setup_bp.route('/request_password_reset', methods=['POST'])
def request_password_reset():
    data = request.json
    email = data.get('email')

    auth0_domain = os.getenv('AUTH0_DOMAIN')
    client_id = os.getenv('AUTH0_CLIENT_ID')

    headers = {
        'content-type': 'application/json'
    }
    payload = {
        'client_id': client_id,
        'email': email,
        'connection': 'Username-Password-Authentication'
    }

    response = requests.post(f'https://{auth0_domain}/dbconnections/change_password', headers=headers, json=payload)
    
    if response.status_code == 200:
        return jsonify({'status': 'success', 'message': 'Password reset email sent successfully.'})
    else:
        return jsonify({'status': 'error', 'message': 'Failed to send password reset email.'}), response.status_code

@setup_bp.route('/password_reset', methods=['GET'])
def password_reset():
    return render_template('request_password_reset.html')

@setup_bp.route('/delete_user/<auth0_id>/<int:user_id>', methods=['POST'])
def delete_user(auth0_id, user_id):
    try:
        client_id = session.get('client_id')
        if not client_id:
            return jsonify({'error': 'Client ID not found in session'}), 401

        user = User.query.filter_by(id=user_id, client_id=client_id).first()
        if not user:
            return jsonify({'error': 'User not found'}), 404

        email = user.email  # Save email before deletion
        db.session.delete(user)
        db.session.commit()

        # Also delete the user from Auth0
        auth0_domain = os.getenv('AUTH0_DOMAIN')
        auth0_token = os.getenv('AUTH0_MANAGEMENT_API_TOKEN')
        headers = {
            'Authorization': f'Bearer {auth0_token}',
            'Content-Type': 'application/json'
        }
        response = requests.delete(f'https://{auth0_domain}/api/v2/users/{auth0_id}', headers=headers)
        response.raise_for_status()

        send_deletion_email(email)  # Send email notification of deletion

        return jsonify({'status': 'success'})
    except Exception as e:
        current_app.logger.error(f"Error deleting user: {e}")
        return jsonify({'error': 'An unexpected error occurred while deleting the user'}), 500
