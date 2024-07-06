import os
from dotenv import load_dotenv
import subprocess

# Load .env file
load_dotenv()

# Define the environment variables to set
env_vars = [
    'FLASK_APP', 'AUTH0_CLIENT_ID', 'AUTH0_CLIENT_SECRET', 'AUTH0_DOMAIN', 
    'AUTH0_CALLBACK_URL', 'AUTH0_AUDIENCE', 'AUTH0_MANAGEMENT_API_TOKEN', 
    'SECRET_KEY', 'STRIPE_SECRET_KEY', 'STRIPE_PUBLISHABLE_KEY', 'MAIL_USE_TLS', 
    'MAIL_USE_SSL', 'MAIL_USERNAME', 'MAIL_PASSWORD', 'MAIL_DEFAULT_SENDER', 
    'MAIL_SERVER', 'MAIL_PORT', 'OPENAI_API_KEY', 'CELERY_BROKER_URL', 
    'CELERY_RESULT_BACKEND'
]

# Set environment variables on Heroku
for var in env_vars:
    value = os.getenv(var)
    if value is None:
        print(f"Warning: {var} is not set in .env file.")
    else:
        command = f"heroku config:set {var}={value} -a raterware"
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Error setting {var}: {result.stderr}")
        else:
            print(f"Set {var} successfully.")

print("Environment variables set successfully on Heroku.")
