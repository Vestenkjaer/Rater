import os
import stripe
from flask import Blueprint, request, jsonify, current_app, session
from models import db, Client
from datetime import datetime
import requests
import time

webhook_bp = Blueprint('webhook', __name__)

# Load Stripe API key from environment
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

# Define the mapping from plan IDs to tiers
PLAN_ID_TO_TIER = {
    'basic_plan_id': 1,       # Replace with your actual plan IDs
    'professional_plan_id': 2, # Replace with your actual plan IDs
    'enterprise_plan_id': 3    # Replace with your actual plan IDs
}

def determine_tier(plan_id):
    return PLAN_ID_TO_TIER.get(plan_id, 0)  # Default to 0 (Free) if plan_id is not found

# Define the webhook endpoint
@webhook_bp.route('/stripe-webhook', methods=['POST'])
def stripe_webhook():
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get('Stripe-Signature')
    endpoint_secret = os.getenv('STRIPE_WEBHOOK_SECRET')

    event = None

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except ValueError as e:
        # Invalid payload
        current_app.logger.error(f'Invalid payload: {e}')
        return jsonify({'error': 'Invalid payload'}), 400
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        current_app.logger.error(f'Invalid signature: {e}')
        return jsonify({'error': 'Invalid signature'}), 400

    # Handle the event
    if event['type'] in ['checkout.session.completed', 'invoice.payment_succeeded']:
        session_data = event['data']['object']
        customer_email = session_data['customer_details']['email']
        subscription_id = session_data['subscription']

        subscription = stripe.Subscription.retrieve(subscription_id)
        plan_id = subscription['items']['data'][0]['price']['product']
        tier = determine_tier(plan_id)

        client = Client.query.filter_by(email=customer_email).first()
        if not client:
            client = Client(email=customer_email, tier=tier, is_admin=True)  # Set is_admin to True
            db.session.add(client)
            db.session.commit()
        
        session['client_id'] = client.id  # Store client ID in session

        # Optionally, update Auth0 profile here if needed
        # update_auth0_profile(customer_email, tier)

    return jsonify({'status': 'success'}), 200


def update_auth0_profile(email, tier):
    url = f'https://{os.getenv("AUTH0_DOMAIN")}/api/v2/users-by-email?email={email}'
    headers = {
        'Authorization': f'Bearer {get_auth0_token()}',
        'Content-Type': 'application/json'
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        user_id = response.json()[0]['user_id']
        update_url = f'https://{os.getenv("AUTH0_DOMAIN")}/api/v2/users/{user_id}'
        data = {'user_metadata': {'tier': tier}}
        requests.patch(update_url, headers=headers, data=json.dumps(data))

def get_auth0_token():
    if 'auth0_token' not in get_auth0_token.__dict__:
        get_auth0_token.auth0_token = None
        get_auth0_token.auth0_token_expiry = 0

    if time.time() < get_auth0_token.auth0_token_expiry:
        return get_auth0_token.auth0_token

    url = f'https://{os.getenv("AUTH0_DOMAIN")}/oauth/token'
    headers = {'content-type': 'application/json'}
    data = {
        'client_id': os.getenv('AUTH0_CLIENT_ID'),
        'client_secret': os.getenv('AUTH0_CLIENT_SECRET'),
        'audience': f'https://{os.getenv("AUTH0_DOMAIN")}/api/v2/',
        'grant_type': 'client_credentials'
    }
    response = requests.post(url, json=data, headers=headers)
    response.raise_for_status()
    token_info = response.json()
    get_auth0_token.auth0_token = token_info['access_token']
    get_auth0_token.auth0_token_expiry = time.time() + token_info['expires_in'] - 60  # Refresh 1 minute before expiry

    return get_auth0_token.auth0_token

# Register the blueprint in your main app
# app.register_blueprint(webhook_bp)
