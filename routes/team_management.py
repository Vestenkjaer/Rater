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
    client_id = session.get('client_id')  # Ensure client_id is retrieved from the session
    if not user_id or not client_id:
        return jsonify({"error": "User not logged in"}), 401

    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found in database"}), 404

    if session.get('is_admin'):
        # Admin sees all teams within their client tenant
        teams = Team.query.filter_by(client_id=client_id).all()
    else:
        # Regular users see only the teams assigned to them
        teams = user.teams

    teams_list = [{"id": team.id, "name": team.name} for team in teams]

    return jsonify({"teams": teams_list})

@team_management_bp.route('/add_team', methods=['POST'])
def add_team():
    try:
        data = request.get_json()
        user_id = session.get('user_id')
        client_id = session.get('client_id')  # Ensure client_id is retrieved from the session

        if not user_id or not client_id:
            return jsonify({"error": "User not found in session"}), 401

        user = User.query.get(user_id)
        if not user:
            return jsonify({"error": "User not found in database"}), 404

        if not session.get('is_admin'):
            return jsonify({"error": "You do not have administrative privileges to create a team."}), 403

        new_team = Team(name=data['team_name'], client_id=client_id)  # Assign the team to the client's ID
        db.session.add(new_team)
        db.session.commit()

        return jsonify(id=new_team.id, name=new_team.name)
    except Exception as e:
        logger.error(f"Error adding team: {e}")
        return jsonify(error=str(e)), 500

@team_management_bp.route('/get_team_members/<int:team_id>', methods=['GET'])
def get_team_members(team_id):
    client_id = session.get('client_id')  # Ensure client_id is retrieved from the session
    team = Team.query.filter_by(id=team_id, client_id=client_id).first()  # Ensure the team belongs to the client
    if team is None:
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
        client_id = session.get('client_id')  # Ensure client_id is retrieved from the session
        if not user_id or not client_id:
            return jsonify({"error": "User not found in session"}), 401

        team = Team.query.filter_by(id=team_id, client_id=client_id).first()  # Ensure the team belongs to the client
        if not team:
            return jsonify({"error": "Team not found"}), 404

        # Check if the user is allowed to add members to this team
        user = User.query.get(user_id)
        if not user.is_admin and team not in user.teams:
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
        if member is None:
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
        if member is None:
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
        if team is None:
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
        if team is None:
            return "Team not found", 404
        db.session.delete(team)
        db.session.commit()
        logger.debug(f"Deleted team with ID: {team.id}")
        return "", 204
    except Exception as e:
        logger.error(f"Error deleting team: {e}")
        return jsonify(error=str(e)), 500
