import os
from dotenv import load_dotenv

load_dotenv()

print("AUTH0_DOMAIN:", os.getenv('AUTH0_DOMAIN'))
print("AUTH0_CLIENT_ID:", os.getenv('AUTH0_CLIENT_ID'))
print("AUTH0_CLIENT_SECRET:", os.getenv('AUTH0_CLIENT_SECRET'))