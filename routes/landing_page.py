from flask import Blueprint, render_template, session, redirect, url_for, jsonify
from models import Team, TeamMember, Rating, Client, User  # Ensure User model is imported
import logging

logging.basicConfig(level=logging.DEBUG)

landing_page_bp = Blueprint('landing_page', __name__)

def get_current_user():
    user_id = session.get('user_id')
    client_id = session.get('client_id')
    if not user_id or not client_id:
        return None

    user = User.query.get(user_id)
    client = Client.query.get(client_id)
    if not user or not client:
        return None

    user.client = client
    return user

@landing_page_bp.route('/user_info')
def user_info():
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not authenticated'}), 401

    logging.debug(f"User info: {user.username}, {user.email}, {user.client.tier}")
    return jsonify({
        'name': user.username,
        'email': user.email,
        'tier': user.client.tier  # Ensure the user's tier is included in the response
    })

@landing_page_bp.route('/')
def dashboard():
    user = get_current_user()
    if not user:
        return redirect(url_for('index.home'))
    
    return render_template('landing_page.html')

@landing_page_bp.route('/team_management/get_teams', methods=['GET'])
def get_teams():
    logging.debug("Fetching teams.")
    teams = Team.query.all()
    teams_data = [{'id': team.id, 'name': team.name} for team in teams]
    logging.debug(f"Teams fetched: {teams_data}")
    return jsonify(teams_data)

@landing_page_bp.route('/rate_team/get_team_members/<int:team_id>', methods=['GET'])
def get_team_members(team_id):
    logging.debug(f"Fetching team members for team ID: {team_id}")
    team = Team.query.get(team_id)
    if not team:
        logging.error(f"Team not found for ID: {team_id}")
        return jsonify({'error': 'Team not found'}), 404

    members = TeamMember.query.filter_by(team_id=team_id).all()
    members_data = []
    for member in members:
        ratings = Rating.query.filter_by(team_member_id=member.id).all()
        total_score = sum(rating.total_score for rating in ratings)
        avg_score = total_score / len(ratings) if ratings else 0
        members_data.append({
            'id': member.id,
            'first_name': member.first_name,
            'surname': member.surname,
            'total_score': total_score,
            'avg_score': avg_score
        })
    logging.debug(f"Members fetched: {members_data}")
    return jsonify({'members': members_data})

@landing_page_bp.route('/rate_team/get_historical_data/<int:member_id>', methods=['GET'])
def get_historical_data(member_id):
    logging.debug(f"Fetching historical data for member ID: {member_id}")
    ratings = Rating.query.filter_by(team_member_id=member_id).all()
    data = [{'timestamp': rating.timestamp, 'total_score': rating.total_score, 'avg_score': rating.avg_score} for rating in ratings]
    logging.debug(f"Historical data fetched: {data}")
    return jsonify(data)
