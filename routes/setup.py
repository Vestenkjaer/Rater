# routes/setup.py
from flask import Blueprint, request, jsonify, session, render_template
from models import db, User, Team, Client, Settings

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
            'auth0_id': user.email
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

@setup_bp.route('/create_user', methods=['POST'])
def create_user():
    data = request.json
    username = data.get('username')
    email = data.get('email')
    client_id = session.get('client_id')
    if not client_id:
        return jsonify({'error': 'Client ID not found in session'}), 401

    user = User(username=username, email=email, client_id=client_id)
    db.session.add(user)
    db.session.commit()

    team_ids = data.get('teams', [])
    for team_id in team_ids:
        team = Team.query.get(team_id)
        if team and team.client_id == client_id:
            team.user_id = user.id
            db.session.commit()

    return jsonify({'status': 'success'})

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

@setup_bp.route('/delete_user/<auth0_id>/<int:user_id>', methods=['POST'])
def delete_user(auth0_id, user_id):
    client_id = session.get('client_id')
    if not client_id:
        return jsonify({'error': 'Client ID not found in session'}), 401

    user = User.query.filter_by(id=user_id, client_id=client_id).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    db.session.delete(user)
    db.session.commit()

    return jsonify({'status': 'success'})

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
