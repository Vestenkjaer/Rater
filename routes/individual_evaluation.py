from flask import Blueprint, render_template, jsonify, request
from models import Team, TeamMember, Rating

individual_evaluation_bp = Blueprint('individual_evaluation', __name__)

@individual_evaluation_bp.route('/')
def individual_evaluation():
    teams = Team.query.all()
    return render_template('individual_evaluation.html', teams=teams)

@individual_evaluation_bp.route('/get_team_members/<int:team_id>')
def get_team_members(team_id):
    team = Team.query.get(team_id)
    if not team:
        return jsonify({'error': 'Team not found'}), 404

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
            'team_id': member.team_id,  # Corrected attribute name
            'ratings': member_ratings,
            'avg_score': avg_score,
            'total_score': total_score
        })
    return jsonify({'team_name': team.name, 'members': members_data})

@individual_evaluation_bp.route('/get_historical_data/<int:member_id>', methods=['GET'])
def get_historical_data(member_id):
    member = TeamMember.query.get(member_id)
    if not member:
        return jsonify({"error": "Member not found"}), 404

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
            "score": evaluation.total_score  # Assuming you have a total_score field
        }
        historical_data.append(data_entry)

    print("Historical Data for Member {}: {}".format(member_id, historical_data))
    return jsonify(historical_data)
