from flask import Blueprint, render_template, session, redirect, url_for, jsonify
from models import Team, TeamMember, Rating, Client, User
import logging
from sqlalchemy import func

logging.basicConfig(level=logging.DEBUG)

landing_page_bp = Blueprint('landing_page', __name__)

def get_current_user():
    user_id = session.get('user_id')
    client_id = session.get('client_id')
    if not user_id or not client_id:
        logging.error('User ID or Client ID not found in session.')
        return None

    user = User.query.get(user_id)
    client = Client.query.get(client_id)
    if not user or not client:
        logging.error('User or Client not found in database.')
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
        'tier': user.client.tier
    })

@landing_page_bp.route('/')
def dashboard():
    user = get_current_user()
    if not user:
        return redirect(url_for('index.home'))
    
    return render_template('landing_page.html')

@landing_page_bp.route('/team_management/get_teams', methods=['GET'])
def get_teams():
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not authenticated'}), 401

    try:
        teams = Team.query.filter_by(client_id=user.client_id).all()
        teams_data = [{'id': team.id, 'name': team.name} for team in teams]
        logging.debug(f"Teams fetched: {teams_data}")
        return jsonify({'teams': teams_data})
    except Exception as e:
        logging.error(f"Error fetching teams: {e}")
        return jsonify({'error': 'An internal error occurred'}), 500

@landing_page_bp.route('/rate_team/get_team_members/<int:team_id>', methods=['GET'])
def get_team_members(team_id):
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not authenticated'}), 401

    try:
        team = Team.query.filter_by(id=team_id, client_id=user.client_id).first()
        if not team:
            logging.error(f"Team not found for ID: {team_id}")
            return jsonify({'error': 'Team not found'}), 404

        members = team.members
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
    except Exception as e:
        logging.error(f"Error fetching team members: {e}")
        return jsonify({'error': 'An internal error occurred'}), 500

@landing_page_bp.route('/rate_team/get_historical_data/<int:member_id>', methods=['GET'])
def get_historical_data(member_id):
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not authenticated'}), 401

    try:
        member = TeamMember.query.get(member_id)
        if not member or member.team.client_id != user.client_id:
            return jsonify({'error': 'Member not found or not assigned to user'}), 404

        ratings = Rating.query.filter_by(team_member_id=member_id).all()
        data = [{'timestamp': rating.timestamp, 'total_score': rating.total_score, 'avg_score': rating.avg_score} for rating in ratings]
        logging.debug(f"Historical data fetched: {data}")
        return jsonify(data)
    except Exception as e:
        logging.error(f"Error fetching historical data: {e}")
        return jsonify({'error': 'An internal error occurred'}), 500

@landing_page_bp.route('/rate_team/get_last_submission/<int:team_id>', methods=['GET'])
def get_last_submission(team_id):
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not authenticated'}), 401

    try:
        latest_submission = db.session.query(
            Rating.team_member_id,
            func.max(Rating.timestamp).label('latest_submission')
        ).join(TeamMember, TeamMember.id == Rating.team_member_id).filter(
            TeamMember.team_id == team_id,
            TeamMember.team.has(client_id=user.client_id)
        ).group_by(Rating.team_member_id).order_by(func.max(Rating.timestamp).desc()).first()

        if latest_submission:
            member_id, latest_submission_time = latest_submission

            latest_rating = Rating.query.filter_by(
                team_member_id=member_id,
                timestamp=latest_submission_time
            ).first()

            if latest_rating:
                submission_data = {
                    'date': latest_rating.timestamp.strftime('%d.%m.%Y')
                }
                return jsonify(submission_data), 200

        logging.debug('No submissions found.')
        return jsonify({'message': 'No submissions found'}), 200
    except Exception as e:
        logging.error(f"Error fetching last submission: {e}")
        return jsonify({'error': 'An internal error occurred'}), 500
