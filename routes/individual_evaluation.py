from flask import Blueprint, render_template, jsonify, request, session
from models import Team, TeamMember, Rating, User
import logging

individual_evaluation_bp = Blueprint('individual_evaluation', __name__)

def get_current_user():
    user_id = session.get('user_id')
    if not user_id:
        return None
    return User.query.get(user_id)

@individual_evaluation_bp.route('/')
def individual_evaluation():
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not authenticated'}), 403

    try:
        assigned_teams = Team.query.filter_by(client_id=user.client_id).all()
        return render_template('individual_evaluation.html', tier=session.get('tier', 0), teams=assigned_teams)
    except Exception as e:
        logging.error(f"Error in individual_evaluation: {e}")
        return jsonify({'error': 'An internal error occurred'}), 500

@individual_evaluation_bp.route('/get_assigned_teams')
def get_assigned_teams():
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not authenticated'}), 403

    try:
        assigned_teams = Team.query.filter_by(client_id=user.client_id).all()
        teams_data = [{'id': team.id, 'name': team.name} for team in assigned_teams]
        return jsonify({'teams': teams_data})
    except Exception as e:
        logging.error(f"Error in get_assigned_teams: {e}")
        return jsonify({'error': 'An internal error occurred'}), 500

@individual_evaluation_bp.route('/get_team_members/<int:team_id>')
def get_team_members(team_id):
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not authenticated'}), 403

    try:
        team = Team.query.filter_by(id=team_id, client_id=user.client_id).first()
        if not team:
            return jsonify({'error': 'Team not found or not assigned to user'}), 404

        members = team.members
        members_data = []
        for member in members:
            latest_ratings = Rating.query.filter_by(team_member_id=member.id).order_by(Rating.timestamp.desc()).first()
            member_ratings = {
                'ability_to_impart_knowledge': latest_ratings.ability_to_impart_knowledge if latest_ratings else 0,
                'approachable': latest_ratings.approachable if latest_ratings else 0,
                'necessary_skills': latest_ratings.necessary_skills if latest_ratings else 0,
                'trained': latest_ratings.trained if latest_ratings else 0,
                'absence': latest_ratings.absence if latest_ratings else 0,
                'self_motivation': latest_ratings.self_motivation if latest_ratings else 0,
                'capacity_for_learning': latest_ratings.capacity_for_learning if latest_ratings else 0,
                'adaptability': latest_ratings.adaptability if latest_ratings else 0
            }

            avg_score = latest_ratings.avg_score if latest_ratings else 0
            total_score = latest_ratings.total_score if latest_ratings else 0

            members_data.append({
                'id': member.id,
                'first_name': member.first_name,
                'surname': member.surname,
                'team_id': member.team_id,
                'ratings': member_ratings,
                'avg_score': avg_score,
                'total_score': total_score
            })
        return jsonify({'team_name': team.name, 'members': members_data})
    except Exception as e:
        logging.error(f"Error in get_team_members: {e}")
        return jsonify({'error': 'An internal error occurred'}), 500

@individual_evaluation_bp.route('/get_historical_data/<int:member_id>')
def get_historical_data(member_id):
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not authenticated'}), 403

    try:
        member = TeamMember.query.get(member_id)
        if not member or member.team.client_id != user.client_id:
            return jsonify({'error': 'Member not found or team not assigned to user'}), 404

        ratings = Rating.query.filter_by(team_member_id=member_id).order_by(Rating.timestamp.desc()).all()
        historical_data = [{'timestamp': rating.timestamp.isoformat(), 'score': rating.total_score} for rating in ratings]
        return jsonify(historical_data)
    except Exception as e:
        logging.error(f"Error in get_historical_data: {e}")
        return jsonify({'error': 'An internal error occurred'}), 500
