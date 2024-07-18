from flask import Blueprint, render_template, jsonify, request, session
from models import Team, TeamMember, Rating, User
from sqlalchemy import func

individual_evaluation_bp = Blueprint('individual_evaluation', __name__)

def get_current_user():
    user_id = session.get('user_id')
    if not user_id:
        print("No user_id in session")
        return None
    user = User.query.get(user_id)
    if not user:
        print(f"User not found for user_id: {user_id}")
    return user

@individual_evaluation_bp.route('/')
def individual_evaluation():
    user = get_current_user()
    if not user:
        print("User not authenticated")
        return jsonify({'error': 'User not authenticated'}), 403

    try:
        teams = user.teams
        if not teams:
            print("No teams assigned to user")
        else:
            print(f"Teams loaded for user: {[team.name for team in teams]}")
        return render_template('individual_evaluation.html', teams=teams)
    except Exception as e:
        print(f"Error loading teams: {str(e)}")
        return jsonify({'error': 'An internal error occurred'}), 500

@individual_evaluation_bp.route('/get_team_members/<int:team_id>')
def get_team_members(team_id):
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not authenticated'}), 403

    team = Team.query.get(team_id)
    if not team or team not in user.teams:
        print(f"Team not found or not assigned to user: team_id={team_id}")
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
    print(f"Team members data for team_id={team_id}: {members_data}")
    return jsonify({'team_name': team.name, 'members': members_data})

@individual_evaluation_bp.route('/get_historical_data/<int:member_id>', methods=['GET'])
def get_historical_data(member_id):
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not authenticated'}), 403

    member = TeamMember.query.get(member_id)
    if not member or member.team not in user.teams:
        print(f"Member not found or not assigned to user: member_id={member_id}")
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

    print(f"Historical data for member_id={member_id}: {historical_data}")
    return jsonify(historical_data)
