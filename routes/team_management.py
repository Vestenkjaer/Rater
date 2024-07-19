import logging
from flask import Blueprint, render_template, request, jsonify, session
from models import db, Team, TeamMember, User

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

team_management_bp = Blueprint('team_management', __name__)

@team_management_bp.route('/')
def team_management():
    return render_template('team_management.html')

@team_management_bp.route('/get_teams', methods=['GET'])
def get_teams():
    user_id = session.get('user_id')
    client_id = session.get('client_id')
    if not user_id or not client_id:
        return jsonify({"error": "User not logged in"}), 401

    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found in database"}), 404

    teams = Team.query.filter_by(client_id=client_id).all()
    teams_list = [{"id": team.id, "name": team.name} for team in teams]

    return jsonify({"teams": teams_list})

@team_management_bp.route('/add_team', methods=['POST'])
def add_team():
    try:
        data = request.get_json()
        user_id = session.get('user_id')
        client_id = session.get('client_id')

        if not user_id or not client_id:
            return jsonify({"error": "User not found in session"}), 401

        user = User.query.get(user_id)
        if not user:
            return jsonify({"error": "User not found in database"}), 404

        if not session.get('is_admin'):
            return jsonify({"error": "You do not have administrative privileges to create a team."}), 403

        new_team = Team(name=data['team_name'], client_id=client_id)
        db.session.add(new_team)
        db.session.commit()

        return jsonify(id=new_team.id, name=new_team.name)
    except Exception as e:
        logger.error(f"Error adding team: {e}")
        return jsonify(error=str(e)), 500

@team_management_bp.route('/get_team_members/<int:team_id>')
def get_team_members(team_id):
    team = Team.query.get(team_id)
    if team is None or team.client_id != session.get('client_id'):
        return jsonify({"error": "Team not found"}), 404
    members = [
        {
            'id': member.id,
            'first_name': member.first_name,
            'surname': member.surname,
            'employer_id': member.employer_id
        } for member in team.members
    ]
    return jsonify(team_name=team.name, members=members)

@team_management_bp.route('/add_team_member/<int:team_id>', methods=['POST'])
def add_team_member(team_id):
    try:
        data = request.get_json()

        user_id = session.get('user_id')
        client_id = session.get('client_id')
        if not user_id or not client_id:
            return jsonify({"error": "User not found in session"}), 401

        team = Team.query.get(team_id)
        if not team or team.client_id != client_id:
            return jsonify({"error": "Team not found"}), 404

        # Check if the user is allowed to add members to this team
        user = User.query.get(user_id)
        if not user.is_admin and team not in user.teams.filter_by(client_id=client_id).all():
            return jsonify({"error": "You do not have permissions to add members to this team."}), 403

        new_member = TeamMember(
            team_id=team_id, 
            first_name=data['first_name'], 
            surname=data['surname'],
            employer_id=data['employer_id']
        )
        db.session.add(new_member)
        db.session.commit()
        return jsonify(id=new_member.id, first_name=new_member.first_name, surname=new_member.surname, employer_id=new_member.employer_id)
    except Exception as e:
        logger.error(f"Error adding team member: {e}")
        return jsonify(error=str(e)), 500

@team_management_bp.route('/update_team_member/<int:member_id>', methods=['PUT'])
def update_team_member(member_id):
    try:
        data = request.get_json()
        logger.debug(f"Received data to update team member ID {member_id}: {data}")
        member = TeamMember.query.get(member_id)
        team = Team.query.get(member.team_id)
        if member is None or team.client_id != session.get('client_id'):
            return "Team member not found", 404
        member.first_name = data['first_name']
        member.surname = data['surname']
        member.employer_id = data['employer_id']
        db.session.commit()
        logger.debug(f"Updated team member with ID: {member.id}")
        return jsonify(id=member.id, first_name=member.first_name, surname=member.surname, employer_id=member.employer_id)
    except Exception as e:
        logger.error(f"Error updating team member: {e}")
        return jsonify(error=str(e)), 500

@team_management_bp.route('/delete_team_member/<int:member_id>', methods=['DELETE'])
def delete_team_member(member_id):
    try:
        member = TeamMember.query.get(member_id)
        team = Team.query.get(member.team_id)
        if member is None or team.client_id != session.get('client_id'):
            return "Team member not found", 404
        db.session.delete(member)
        db.session.commit()
        logger.debug(f"Deleted team member with ID: {member.id}")
        return "", 204
    except Exception as e:
        logger.error(f"Error deleting team member: {e}")
        return jsonify(error=str(e)), 500

@team_management_bp.route('/update_team/<int:team_id>', methods=['PUT'])
def update_team(team_id):
    try:
        data = request.get_json()
        logger.debug(f"Received data to update team ID {team_id}: {data}")
        team = Team.query.get(team_id)
        if team is None or team.client_id != session.get('client_id'):
            return "Team not found", 404
        team.name = data['team_name']
        db.session.commit()
        logger.debug(f"Updated team with ID: {team.id}")
        return jsonify(id=team.id, name=team.name)
    except Exception as e:
        logger.error(f"Error updating team: {e}")
        return jsonify(error=str(e)), 500

@team_management_bp.route('/delete_team/<int:team_id>', methods=['DELETE'])
def delete_team(team_id):
    try:
        team = Team.query.get(team_id)
        if team is None or team.client_id != session.get('client_id'):
            return "Team not found", 404
        db.session.delete(team)
        db.session.commit()
        logger.debug(f"Deleted team with ID: {team.id}")
        return "", 204
    except Exception as e:
        logger.error(f"Error deleting team: {e}")
        return jsonify(error=str(e)), 500
