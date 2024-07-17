import os
import secrets
import string
from dotenv import load_dotenv
from flask import Flask, render_template, redirect, url_for, session, jsonify, request
from flask_session import Session
from config import Config
from whitenoise import WhiteNoise
from models import db, Client, User, Settings, Team, TeamMember, Rating
from flask_migrate import Migrate
from authlib.integrations.flask_client import OAuth
import logging
import stripe
import requests
import json
import time
from apscheduler.schedulers.background import BackgroundScheduler
from mail import mail
from urllib.parse import urlencode
from werkzeug.security import generate_password_hash
from flask_mail import Message
from webhook import webhook_bp
from routes.payment import payment_bp
import traceback

# Load environment variables from .env file
load_dotenv()

# Set up Stripe API key
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
# Print the value of STRIPE_WEBHOOK_SECRET for debugging
print("STRIPE_WEBHOOK_SECRET:", os.getenv('STRIPE_WEBHOOK_SECRET'))

# Create the Flask app
def create_app():
    app = Flask(__name__, static_folder='static')
    app.config.from_object(Config)
    app.secret_key = os.getenv('SECRET_KEY')
    app.config['STRIPE_PUBLISHABLE_KEY'] = os.getenv('STRIPE_PUBLISHABLE_KEY')

    # Configure session to use the filesystem
    app.config['SESSION_TYPE'] = 'filesystem'
    app.config['SESSION_FILE_DIR'] = './.flask_session/'
    app.config['SESSION_PERMANENT'] = False
    app.config['SESSION_USE_SIGNER'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db?timeout=30'

    # Add this line to disable caching of static files
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

    # Initialize Whitenoise
    app.wsgi_app = WhiteNoise(
        app.wsgi_app,
        root='static/',
        prefix='static/',
        max_age=31536000,  # Cache files for 1 year
        autorefresh=True,  # Auto-refresh static files in development
        index_file=True,   # Serve index.html as default
        mimetypes={'text/css': 'text/css; charset=UTF-8'}  # Specify MIME types if needed
    )

    # Set up logging
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger(__name__)

    # Log environment variables
    required_env_vars = [
        'MAIL_SERVER', 'MAIL_PORT', 'MAIL_USERNAME', 'MAIL_PASSWORD',
        'AUTH0_CLIENT_ID', 'AUTH0_CLIENT_SECRET', 'AUTH0_DOMAIN',
        'AUTH0_CALLBACK_URL_HEROKU', 'AUTH0_CALLBACK_URL_CUSTOM'
    ]

    for var in required_env_vars:
        value = os.getenv(var)
        if not value:
            raise ValueError(f"Missing required environment variable: {var}")
        logger.debug(f"{var}: {value}")

    # Configure Flask-Mail
    app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER')
    app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT'))
    app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS') == 'True'
    app.config['MAIL_USE_SSL'] = os.getenv('MAIL_USE_SSL') == 'True'
    app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
    app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
    app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER')
    mail.init_app(app)  # Initialize the mail instance

    # Initialize session
    Session(app)

    # Initialize database and migration
    db.init_app(app)
    migrate = Migrate(app, db)
    oauth = OAuth(app)

    # Configure Auth0
    auth0 = oauth.register(
        'auth0',
        client_id=os.getenv('AUTH0_CLIENT_ID'),
        client_secret=os.getenv('AUTH0_CLIENT_SECRET'),
        api_base_url=f"https://{os.getenv('AUTH0_DOMAIN')}",
        access_token_url=f"https://{os.getenv('AUTH0_DOMAIN')}/oauth/token",
        authorize_url=f"https://{os.getenv('AUTH0_DOMAIN')}/authorize",
        server_metadata_url=f"https://{os.getenv('AUTH0_DOMAIN')}/.well-known/openid-configuration",
        client_kwargs={
            'scope': 'openid profile email',
        },
    )

    with app.app_context():
        db.create_all()

    # Register blueprints
    from routes.main import main_bp
    from routes.rate_team import rate_team_bp
    from routes.setup import setup_bp
    from routes.team_management import team_management_bp
    from routes.client_management import client_management_bp
    from routes.individual_evaluation import individual_evaluation_bp
    from routes.landing_page import landing_page_bp  
    from routes.pricing import pricing_bp
    from routes.public import public_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(rate_team_bp, url_prefix='/rate_team')
    app.register_blueprint(setup_bp, url_prefix='/setup')
    app.register_blueprint(team_management_bp, url_prefix='/team_management')
    app.register_blueprint(client_management_bp, url_prefix='/client_management')
    app.register_blueprint(individual_evaluation_bp, url_prefix='/individual_evaluation')
    app.register_blueprint(landing_page_bp, url_prefix='/dashboard')
    app.register_blueprint(pricing_bp, url_prefix='/pricing')
    app.register_blueprint(payment_bp, url_prefix='/payment')  # Register the payment blueprint
    app.register_blueprint(public_bp, url_prefix='/public')
    app.register_blueprint(webhook_bp)  # Register the webhook blueprint

    # User blocking/unblocking logic
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
        logger.debug(f"Blocking user in Auth0: {email}")
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
        logger.debug(f"Unblocking user in Auth0: {email}")
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

    @app.route('/pricing')
    def pricing():
        stripe_publishable_key = os.getenv('STRIPE_PUBLISHABLE_KEY')
        return render_template('pricing.html', stripe_publishable_key=stripe_publishable_key)

    # Define routes
    @app.route('/')
    def index():
        return redirect(url_for('dashboard'))

    @app.route('/login')
    def login():
        state = secrets.token_urlsafe(16)
        session['auth0_state'] = state
        session.modified = True
        logger.debug(f"Generated state: {state}")
        logger.debug(f"Session before redirect: {dict(session)}")
        return auth0.authorize_redirect(redirect_uri=os.getenv('AUTH0_CALLBACK_URL_HEROKU') or os.getenv('AUTH0_CALLBACK_URL_CUSTOM'), state=state)

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
                session['user_id'] = user.id
                session['tier'] = user.client.tier
                session['is_admin'] = user.is_admin  # Set is_admin in session

                # Ensure to log the session data for debugging
                app.logger.debug(f"Session after setting user data: {dict(session)}")

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
        params = {
            'returnTo': url_for('index', _external=True),
            'client_id': os.getenv('AUTH0_CLIENT_ID')
        }
        auth0_domain = os.getenv('AUTH0_DOMAIN')
        logout_url = f'https://{auth0_domain}/v2/logout?' + urlencode(params)
        return redirect(logout_url)

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
        client_id = session.get('client_id')
        client = Client.query.get(client_id) if client_id else None
        return jsonify({
            'name': user_info.get('name', 'Unknown User'),
            'email': user_info.get('email', 'unknown@example.com'),
            'tier': client.tier if client else 0,
            'is_admin': client.is_admin if client else False
        })

    @app.route('/register', methods=['POST'])
    def register():
        try:
            data = request.get_json()
            email = data.get('email')
            username = data.get('username')  # Get the username from the request if provided
            is_admin = data.get('is_admin', False)  # Default to False if not provided

            if not email:
                return jsonify({'error': 'Email is required'}), 400

            client_id = session.get('client_id')
            if
