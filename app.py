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

        logger.debug(f"State in callback: {state}")
        logger.debug(f"State in session: {session_state}")
        logger.debug(f"Session in callback: {dict(session)}")

        if state != session_state:
            logger.warning("CSRF check failed")
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
            logger.error(f"Error during Auth0 callback: {str(e)}")
            logger.exception("Exception during Auth0 callback")
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

            if not email:
                return jsonify({'error': 'Email is required'}), 400

            client_id = session.get('client_id')
            if not client_id:
                client = Client.query.filter_by(email=email).first()
                if not client:
                    client = Client(name='default_client_name', email=email, tier=0)
                    db.session.add(client)
                    db.session.commit()
                client_id = client.id

            # Check if user already exists
            existing_user = User.query.filter_by(email=email).first()
            if existing_user:
                return jsonify({'error': 'User already exists'}), 400

            # Ensure unique username
            if not username:
                username = 'default_username'
            if User.query.filter_by(username=username).first():
                suffix = 1
                new_username = f"{username}{suffix}"
                while User.query.filter_by(username=new_username).first():
                    suffix += 1
                    new_username = f"{username}{suffix}"
                username = new_username

            # Generate a password
            password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(10))
            hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

            # Create a new user
            new_user = User(username=username, email=email, password_hash=hashed_password, client_id=client_id)
            db.session.add(new_user)
            db.session.commit()

            # Create user in Auth0
            auth0_domain = os.getenv('AUTH0_DOMAIN')
            auth0_token = get_auth0_token()
            auth0_headers = {
                'Authorization': f'Bearer {auth0_token}',
                'Content-Type': 'application/json'
            }
            auth0_data = {
                'email': email,
                'password': password,
                'connection': 'Username-Password-Authentication'
            }
            auth0_response = requests.post(f'https://{auth0_domain}/api/v2/users', headers=auth0_headers, json=auth0_data)
            if auth0_response.status_code != 201:
                raise Exception('Auth0 user creation failed')

            # Inside the register route where the email is constructed and sent
            msg = Message('Welcome to Raterware!', recipients=[email])
            msg.html = f"""
              <p>Hi {username},</p>

             <p>Welcome to Raterware! We're thrilled to have you on board.</p>

             <p>Raterware is your ultimate tool for objectively rating and monitoring the progress of your team members.
             Whether you’re managing a business team, a sports team, or any group of individuals that require regular evaluation,
             Raterware adapts to your unique requirements.</p>

             <p>Here is your password to get started:</p>
             <p><strong style="font-size: 18px; color: blue;">{password}</strong></p>

             <p>Please log in using your email and this password. In the log in dialog box, you can change your password to something more secure and personal.</p>

             <p>We're here to help you unlock the true potential of your team. If you have any questions or need assistance, feel free to reach out to our support team.</p>

             <p>Best regards,</p>
             <p>The Raterware Team</p>
             <p>Empowering Your Team with Data-Driven Insights</p>
            """

            mail.send(msg)


            return jsonify({'message': 'Registration successful. A password has been sent to your email.'}), 200
        except Exception as e:
            logger.error(f"Error during registration: {str(e)}")
            logger.exception("Exception during registration")
            return jsonify({'error': 'Registration failed.'}), 500

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
            logger.error(f"Webhook error: {str(e)}")
            return jsonify({'error': str(e)}), 400
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Signature verification failed: {str(e)}")
            return jsonify({'error': str(e)}), 400

        if event['type'] == 'checkout.session.completed':
            session_data = event['data']['object']
            customer_email = session_data['customer_details']['email']
            subscription_id = session_data['subscription']

            logger.info(f"Checkout session completed for customer: {customer_email}, subscription: {subscription_id}")

            subscription = stripe.Subscription.retrieve(subscription_id)
            plan_id = subscription['items']['data'][0]['price']['product']
            tier = determine_tier(plan_id)

            logger.debug(f"Determined tier: {tier} for plan ID: {plan_id}")

            client = Client.query.filter_by(email=customer_email).first()
            if client:
                logger.debug(f"Updating tier for client: {client.email} to tier {tier}")
                client.tier = tier
                db.session.commit()
            else:
                logger.debug(f"Creating new client for email: {customer_email}")
                new_client = Client(name='default_client_name', email=customer_email, tier=tier)
                db.session.add(new_client)
                db.session.commit()

            update_auth0_profile(customer_email, tier)

        return jsonify({'status': 'success'}), 200

    def determine_tier(plan_id):
        for plan, data in products.items():
            if data['price_id'] == plan_id:
                return data['tier']
        return 0  # Default tier if not found

    def update_auth0_profile(email, tier):
        logger.debug(f"Updating Auth0 profile for email: {email} with tier: {tier}")
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

    @app.route('/payment/success')
    def payment_success():
        session_id = request.args.get('session_id')
        desired_tier = request.args.get('tier')  # Get the desired tier from the query parameters
        if not session_id:
            return jsonify({'error': 'Session ID is missing'}), 400

        session_data = stripe.checkout.Session.retrieve(session_id)
        customer_email = session_data['customer_details']['email']
        client = Client.query.filter_by(email=customer_email).first()
    
        if client:
            # Existing client, upgrading tier
            registration_needed = False
            client.tier = desired_tier
            db.session.commit()
        else:
            # New client
            registration_needed = True

        return render_template('success_page.html', session_id=session_id, registration_needed=registration_needed, show_home_button=not registration_needed)


    return app

if __name__ == '__main__':
    app = create_app()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
