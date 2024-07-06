import os
import secrets
from dotenv import load_dotenv
from flask import Flask, render_template, redirect, url_for, session, jsonify, request, current_app
from flask_session import Session
from config import Config
from models import db, Client, User, Settings
from flask_migrate import Migrate
from authlib.integrations.flask_client import OAuth
import logging
import stripe
import requests
import json
import time
from apscheduler.schedulers.background import BackgroundScheduler
from mail import mail  # Import mail from mail.py

load_dotenv()  # Load environment variables from .env file

stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    app.secret_key = app.config['SECRET_KEY']
    app.config['STRIPE_PUBLISHABLE_KEY'] = os.getenv('STRIPE_PUBLISHABLE_KEY')

    # Configure session to use the filesystem
    app.config['SESSION_TYPE'] = 'filesystem'
    app.config['SESSION_FILE_DIR'] = './.flask_session/'  
    app.config['SESSION_PERMANENT'] = False
    app.config['SESSION_USE_SIGNER'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db?timeout=30'

    # Print out environment variables for debugging
    print(f"MAIL_SERVER: {os.getenv('MAIL_SERVER')}")
    print(f"MAIL_PORT: {os.getenv('MAIL_PORT')}")
    print(f"MAIL_USERNAME: {os.getenv('MAIL_USERNAME')}")
    print(f"MAIL_PASSWORD: {os.getenv('MAIL_PASSWORD')}")

    # Configure Flask-Mail
    app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER')
    app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT'))
    app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS') == 'True'
    app.config['MAIL_USE_SSL'] = os.getenv('MAIL_USE_SSL') == 'True'
    app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
    app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
    app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER')
    mail.init_app(app)  # Initialize the mail instance

    Session(app)

    db.init_app(app)
    migrate = Migrate(app, db)  # Ensure Migrate is initialized
    oauth = OAuth(app)

    auth0 = oauth.register(
        'auth0',
        client_id=app.config['AUTH0_CLIENT_ID'],
        client_secret=app.config['AUTH0_CLIENT_SECRET'],
        api_base_url=f"https://{app.config['AUTH0_DOMAIN']}",
        access_token_url=f"https://{app.config['AUTH0_DOMAIN']}/oauth/token",
        authorize_url=f"https://{app.config['AUTH0_DOMAIN']}/authorize",
        server_metadata_url=f"https://{app.config['AUTH0_DOMAIN']}/.well-known/openid-configuration",
        client_kwargs={
            'scope': 'openid profile email',
        },
    )

    logging.basicConfig(level=logging.DEBUG)

    with app.app_context():
        db.create_all()

    from routes.main import main_bp
    from routes.rate_team import rate_team_bp
    from routes.setup import setup_bp
    from routes.team_management import team_management_bp
    from routes.client_management import client_management_bp
    from routes.individual_evaluation import individual_evaluation_bp
    from routes.landing_page import landing_page_bp  
    from routes.pricing import pricing_bp
    from routes.payment import payment_bp
    from routes.public import public_bp  # Import the public blueprint

    app.register_blueprint(main_bp)
    app.register_blueprint(rate_team_bp, url_prefix='/rate_team')
    app.register_blueprint(setup_bp, url_prefix='/setup')
    app.register_blueprint(team_management_bp, url_prefix='/team_management')
    app.register_blueprint(client_management_bp, url_prefix='/client_management')
    app.register_blueprint(individual_evaluation_bp, url_prefix='/individual_evaluation')
    app.register_blueprint(landing_page_bp, url_prefix='/dashboard') 
    app.register_blueprint(pricing_bp, url_prefix='/pricing')
    app.register_blueprint(payment_bp)
    app.register_blueprint(public_bp, url_prefix='/public')  # Register the public blueprint

    def check_and_block_users():
        clients = Client.query.all()
        for client in clients:
            if client.payment_status == 'blocked':
                users = User.query.filter_by(client_id=client.id).all()
                for user in users:
                    block_user_in_auth0(user.email)
            else:
                users = User.query.filter_by(client_id=client.id).all()
                for user in users:
                    unblock_user_in_auth0(user.email)

    def block_user_in_auth0(email):
        auth0_domain = os.getenv('AUTH0_DOMAIN')
        token = get_auth0_token()
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        response = requests.get(f'https://{auth0_domain}/api/v2/users-by-email?email={email}', headers=headers)
        if response.status_code == 200:
            user_id = response.json()[0]['user_id']
            block_payload = {
                'blocked': True
            }
            requests.patch(f'https://{auth0_domain}/api/v2/users/{user_id}', headers=headers, json=block_payload)

    def unblock_user_in_auth0(email):
        auth0_domain = os.getenv('AUTH0_DOMAIN')
        token = get_auth0_token()
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        response = requests.get(f'https://{auth0_domain}/api/v2/users-by-email?email={email}', headers=headers)
        if response.status_code == 200:
            user_id = response.json()[0]['user_id']
            unblock_payload = {
                'blocked': False
            }
            requests.patch(f'https://{auth0_domain}/api/v2/users/{user_id}', headers=headers, json=unblock_payload)

    # Scheduler setup
    scheduler = BackgroundScheduler()
    scheduler.add_job(func=check_and_block_users, trigger="interval", hours=24)
    scheduler.start()

    @app.teardown_appcontext
    def shutdown_session(exception=None):
        db.session.remove()

    @app.route('/login')
    def login():
        state = secrets.token_urlsafe(16)
        session['auth0_state'] = state
        session.modified = True  
        app.logger.debug(f"Generated state: {state}")
        app.logger.debug(f"Session before redirect: {dict(session)}")
        return auth0.authorize_redirect(redirect_uri=app.config['AUTH0_CALLBACK_URL'], state=state)

    @app.route('/callback')
    def callback_handling():
        state = request.args.get('state')
        session_state = session.get('auth0_state')

        app.logger.debug(f"State in callback: {state}")
        app.logger.debug(f"State in session: {session_state}")
        app.logger.debug(f"Session in callback: {dict(session)}")

        if state != session_state:
            app.logger.warning("CSRF check failed")
            return jsonify({"error": "CSRF Warning! State not equal in request and response."}), 400

        try:
            token_response = auth0.authorize_access_token()
            response = auth0.get('userinfo')
            user_info = response.json()
            session['user'] = user_info

            email = user_info['email']
            user = User.query.filter_by(email=email).first()
            if user:
                session['client_id'] = user.client_id
                session['tier'] = user.client.tier

            session.pop('auth0_state', None)
        except Exception as e:
            app.logger.error(f"Error during Auth0 callback: {str(e)}")
            app.logger.exception("Exception during Auth0 callback")
            return jsonify({"error": str(e)}), 500
        return redirect('/dashboard')

    @app.route('/dashboard')
    def dashboard():
        if 'user' not in session:
            return redirect(url_for('login'))
        return render_template('landing_page.html')

    @app.route('/logout')
    def logout():
        session.clear()
        return redirect(auth0.api_base_url + '/v2/logout?client_id=' + app.config['AUTH0_CLIENT_ID'] + '&returnTo=' + url_for('index', _external=True))

    @app.route('/')
    def index():
        return redirect(url_for('logout'))

    @app.route('/set_session')
    def set_session():
        session['test'] = 'This is a test'
        session.modified = True  
        return 'Session data set'

    @app.route('/get_session')
    def get_session():
        test_data = session.get('test', 'Not set')
        return f'Session data: {test_data}'

    @app.route('/user_info')
    def user_info():
        user_info = session.get('user', {})
        return jsonify({
            'name': user_info.get('name', 'Unknown User'),
            'email': user_info.get('email', 'unknown@example.com')
        })

    @app.route('/stripe-webhook', methods=['POST'])
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
            return jsonify({'error': str(e)}), 400
        except stripe.error.SignatureVerificationError as e:
            return jsonify({'error': str(e)}), 400

        if event['type'] == 'checkout.session.completed':
            session_data = event['data']['object']
            customer_email = session_data['customer_details']['email']
            subscription_id = session_data['subscription']

            subscription = stripe.Subscription.retrieve(subscription_id)
            plan_id = subscription['items']['data'][0]['price']['product']
            tier = determine_tier(plan_id)

            client = Client.query.filter_by(email=customer_email).first()
            if client:
                client.tier = tier
                db.session.commit()

            update_auth0_profile(customer_email, tier)

        return jsonify({'status': 'success'}), 200

    def determine_tier(plan_id):
        if plan_id == 'basic_plan_id':
            return 1  # Basic tier
        elif plan_id == 'professional_plan_id':
            return 2  # Professional tier
        elif plan_id == 'enterprise_plan_id':
            return 3  # Enterprise tier
        return 0  # Free tier

    def update_auth0_profile(email, tier):
        url = f'https://{app.config["AUTH0_DOMAIN"]}/api/v2/users-by-email?email={email}'
        headers = {
            'Authorization': f'Bearer {get_auth0_token()}',
            'Content-Type': 'application/json'
        }
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            user_id = response.json()[0]['user_id']
            update_url = f'https://{app.config["AUTH0_DOMAIN"]}/api/v2/users/{user_id}'
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

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
