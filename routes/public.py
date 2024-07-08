from flask import Blueprint, render_template, request, jsonify
import requests
import os

public_bp = Blueprint('public', __name__)

@public_bp.route('/password_reset', methods=['GET'])
def password_reset():
    return render_template('password_reset.html')

@public_bp.route('/request_password_reset', methods=['POST'])
def request_password_reset():
    data = request.json
    email = data.get('email')

    auth0_domain = os.getenv('AUTH0_DOMAIN')
    client_id = os.getenv('AUTH0_CLIENT_ID')

    headers = {
        'content-type': 'application/json'
    }
    payload = {
        'client_id': client_id,
        'email': email,
        'connection': 'Username-Password-Authentication'
    }

    response = requests.post(f'https://{auth0_domain}/dbconnections/change_password', headers=headers, json=payload)
    
    if response.status_code == 200:
        return jsonify({'status': 'success', 'message': 'Password reset email sent successfully.'})
    else:
        return jsonify({'status': 'error', 'message': 'Failed to send password reset email.'}), response.status_code
