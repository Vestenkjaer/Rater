from flask import Blueprint, render_template, jsonify, request, session
from models import Team, TeamMember, Rating, db
from datetime import datetime, timedelta
import logging
import openai

logging.basicConfig(level=logging.DEBUG)

rate_team_bp = Blueprint('rate_team', __name__)

def get_client_id():
    return session.get('client_id')

def get_client_tier():
    return session.get('tier')

@rate_team_bp.route('/individual_evaluation')
def individual_evaluation():
    client_id = get_client_id()
    if not client_id:
        return jsonify({'error': 'Client not authenticated'}), 403

    client_tier = get_client_tier()
    if client_tier == 0:
        return render_template('upgrade.html', message="To get the full AI experience, please upgrade to the Professional version.")

    teams = Team.query.filter_by(client_id=client_id).all()
    return render_template('individual_evaluation.html', teams=teams)

@rate_team_bp.route('/')
def rate_team():
    client_id = get_client_id()
    if not client_id:
        return jsonify({'error': 'Client not authenticated'}), 403

    teams = Team.query.filter_by(client_id=client_id).all()
    return render_template('rate_team.html', teams=teams, tier=session.get('tier', 0))

@rate_team_bp.route('/get_team_members/<int:team_id>')
def get_team_members(team_id):
    client_id = get_client_id()
    if not client_id:
        return jsonify({'error': 'Client not authenticated'}), 403

    team = Team.query.filter_by(id=team_id, client_id=client_id).first()
    if not team:
        return jsonify({'error': 'Team not found'}), 404

    members = team.members
    members_data = []
    for member in members:
        latest_ratings = Rating.query.filter_by(team_member_id=member.id).order_by(Rating.timestamp.desc()).limit(1).first()
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

@rate_team_bp.route('/rate_member/<int:member_id>', methods=['POST'])
def rate_member(member_id):
    client_id = get_client_id()
    if not client_id:
        return jsonify({'error': 'Client not authenticated'}), 403

    data = request.get_json()
    logging.debug(f"Received data for member {member_id}: {data}")
    member = TeamMember.query.get(member_id)
    if not member or member.team.client_id != client_id:
        return jsonify({'error': 'Member not found'}), 404

    # Extract and convert criteria values to integers
    ability_to_impart_knowledge = int(data.get('ability_to_impart_knowledge', 0))
    approachable = int(data.get('approachable', 0))
    necessary_skills = int(data.get('necessary_skills', 0))
    trained = int(data.get('trained', 0))
    absence = int(data.get('absence', 0))
    self_motivation = int(data.get('self_motivation', 0))
    capacity_for_learning = int(data.get('capacity_for_learning', 0))
    adaptability = int(data.get('adaptability', 0))

    logging.debug(f"ability_to_impart_knowledge: {ability_to_impart_knowledge}")
    logging.debug(f"approachable: {approachable}")
    logging.debug(f"necessary_skills: {necessary_skills}")
    logging.debug(f"trained: {trained}")
    logging.debug(f"absence: {absence}")
    logging.debug(f"self_motivation: {self_motivation}")
    logging.debug(f"capacity_for_learning: {capacity_for_learning}")
    logging.debug(f"adaptability: {adaptability}")

    total_score = ability_to_impart_knowledge + approachable + necessary_skills + trained + absence + self_motivation + capacity_for_learning + adaptability
    avg_score = total_score / 8

    rating = Rating(
        team_member_id=member_id,
        ability_to_impart_knowledge=ability_to_impart_knowledge,
        approachable=approachable,
        necessary_skills=necessary_skills,
        trained=trained,
        absence=absence,
        self_motivation=self_motivation,
        capacity_for_learning=capacity_for_learning,
        adaptability=adaptability,
        total_score=total_score,
        avg_score=avg_score
    )

    db.session.add(rating)
    db.session.commit()

    logging.debug(f"Calculated total score for member {member_id}: {total_score}")
    logging.debug(f"Calculated average score for member {member_id}: {avg_score}")
    logging.debug(f"Saved rating for member {member_id}: {rating}")

    # Keep only the last 24 ratings (FIFO)
    ratings = Rating.query.filter_by(team_member_id=member_id).order_by(Rating.timestamp).all()
    if len(ratings) > 24:
        for rating in ratings[:-24]:
            db.session.delete(rating)
        db.session.commit()

    return jsonify({'message': 'Ratings submitted successfully'})

@rate_team_bp.route('/get_historical_data/<int:member_id>')
def get_historical_data(member_id):
    client_id = get_client_id()
    if not client_id:
        return jsonify({'error': 'Client not authenticated'}), 403

    member = TeamMember.query.get(member_id)
    if not member or member.team.client_id != client_id:
        return jsonify({'error': 'Member not found'}), 404

    ratings = Rating.query.filter(Rating.team_member_id == member_id).order_by(Rating.timestamp.desc()).limit(12).all()
    logging.debug(f"Retrieved historical data for member {member_id}: {ratings}")
    historical_data = [{'timestamp': rating.timestamp.isoformat(), 'score': rating.total_score} for rating in ratings]
    return jsonify(historical_data)

@rate_team_bp.route('/historical_data')
def historical_data():
    return render_template('historical_data.html')

@rate_team_bp.route('/get_teams')
def get_teams():
    client_id = get_client_id()
    if not client_id:
        return jsonify({'error': 'Client not authenticated'}), 403

    teams = Team.query.filter_by(client_id=client_id).all()
    team_list = [{'id': team.id, 'name': team.name} for team in teams]
    return jsonify({'teams': team_list})

@rate_team_bp.route('/get_ai_recommendation/<int:member_id>')
def get_ai_recommendation(member_id):
    client_id = get_client_id()
    if not client_id:
        return jsonify({'error': 'Client not authenticated'}), 403

    client_tier = get_client_tier()
    if client_tier == 0:
        return jsonify({'error': 'To get the full AI experience, please upgrade to the Professional version'}), 403

    member = TeamMember.query.get(member_id)
    if not member or member.team.client_id != client_id:
        return jsonify({'error': 'Member not found'}), 404

    # Get the last 24 ratings for the member
    ratings = Rating.query.filter_by(team_member_id=member_id).order_by(Rating.timestamp.desc()).limit(24).all()

    if not ratings:
        return jsonify({'error': 'No ratings found for the member'}), 404

    # Prepare the input for the AI model
    rating_data = []
    for rating in ratings:
        if rating.total_score > 0:
            rating_data.append({
                'timestamp': rating.timestamp.isoformat(),
                'ability_to_impart_knowledge': rating.ability_to_impart_knowledge,
                'approachable': rating.approachable,
                'necessary_skills': rating.necessary_skills,
                'trained': rating.trained,
                'absence': rating.absence,
                'self_motivation': rating.self_motivation,
                'capacity_for_learning': rating.capacity_for_learning,
                'adaptability': rating.adaptability,
                'total_score': rating.total_score,
                'avg_score': rating.avg_score
            })

    if not rating_data:
        return jsonify({'error': 'No valid ratings found for the member'}), 404

    # Generate the prompt with structured request
    prompt = f"""
    As an expert HR advisor, evaluate the following performance data for the member {member.first_name} {member.surname} and provide a structured recommendation. The evaluation should help the team manager make better decisions based on your analysis.

    Introduction:
    Briefly introduce the context of the evaluation.

    Summary of Recent Performance:
    Highlight key performance trends over the last 12 ratings, mentioning any significant improvements or declines in performance.

    Detailed Evaluation by Criteria:
    Analyze each criterion individually, mentioning notable scores and trends. Provide insights on strengths and weaknesses.

    Overall Performance Analysis:
    Provide an aggregate view of the performance, considering all criteria. Comment on the overall trajectory of the performance.

    Recommendations:
    Provide actionable recommendations based on the analysis. Suggest specific areas for improvement and potential steps to address them.

    Conclusion:
    Summarize the key points and the next steps.

    Performance Data:
    """
    for data in rating_data:
        prompt += f"Date: {data['timestamp']}, "
        prompt += f"Ability to Impart Knowledge: {data['ability_to_impart_knowledge']}, "
        prompt += f"Approachable: {data['approachable']}, "
        prompt += f"Necessary Skills: {data['necessary_skills']}, "
        prompt += f"Trained: {data['trained']}, "
        prompt += f"Absence: {data['absence']}, "
        prompt += f"Self Motivation: {data['self_motivation']}, "
        prompt += f"Capacity for Learning: {data['capacity_for_learning']}, "
        prompt += f"Adaptability: {data['adaptability']}, "
        prompt += f"Total Score: {data['total_score']}, "
        prompt += f"Average Score: {data['avg_score']}\n"

    # Call the OpenAI API
    openai.api_key = "sk-proj-AinR9TGumpwNVQtmUykQT3BlbkFJrUExG5KICvGb5a6RN5ka"  # Replace with your actual API key
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert HR advisor."},
                {"role": "user", "content": prompt}
            ]
        )
        recommendation = response.choices[0].message['content'].strip()
    except Exception as e:
        logging.error(f"Error fetching AI recommendation: {e}")
        return jsonify({'error': str(e)}), 500

    return jsonify({'recommendation': recommendation})

