from flask import Blueprint, render_template, jsonify, request, session
from models import Team, TeamMember, Rating, User

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
        assigned_teams = user.teams
        print(f"Assigned teams: {assigned_teams}")  # Debug print
        return render_template('individual_evaluation.html', tier=session.get('tier', 0), teams=assigned_teams)
    except Exception as e:
        print(f"Error loading individual evaluation page: {e}")
        return jsonify({'error': 'An internal error occurred'}), 500

@individual_evaluation_bp.route('/get_team_members/<int:team_id>')
def get_team_members(team_id):
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not authenticated'}), 403

    team = Team.query.get(team_id)
    if not team or team not in user.teams:
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

@individual_evaluation_bp.route('/get_historical_data/<int:member_id>', methods=['GET'])
def get_historical_data(member_id):
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not authenticated'}), 403

    member = TeamMember.query.get(member_id)
    if not member or member.team not in user.teams:
        return jsonify({"error": "Member not found or not assigned to user"}), 404

    historical_data = []
    for evaluation in member.evaluations:
        data_entry = {
            "timestamp": evaluation.timestamp,
            "ability_to_impart_knowledge": evaluation.ability_to_impart_knowledge,
            "approachable": evaluation.approachable,
            "necessary_skills": evaluation.necessary_skills,
            "trained": evaluation.trained,
            "absence": evaluation.absence,
            "self_motivation": evaluation.self_motivation,
            "capacity_for_learning": evaluation.capacity_for_learning,
            "adaptability": evaluation.adaptability,
            "score": evaluation.total_score
        }
        historical_data.append(data_entry)

    return jsonify(historical_data)
