from apscheduler.schedulers.background import BackgroundScheduler
from models import db, Client, User
import requests
import os
import logging

def check_and_block_users():
    logging.info("Checking and blocking users based on client status...")
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
    auth0_token = os.getenv('AUTH0_API_TOKEN')
    headers = {
        'Authorization': f'Bearer {auth0_token}',
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
    auth0_token = os.getenv('AUTH0_API_TOKEN')
    headers = {
        'Authorization': f'Bearer {auth0_token}',
        'Content-Type': 'application/json'
    }
    response = requests.get(f'https://{auth0_domain}/api/v2/users-by-email?email={email}', headers=headers)
    if response.status_code == 200:
        user_id = response.json()[0]['user_id']
        unblock_payload = {
            'blocked': False
        }
        requests.patch(f'https://{auth0_domain}/api/v2/users/{user_id}', headers=headers, json=unblock_payload)

def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(func=check_and_block_users, trigger="interval", minutes=60)  # Adjust interval as needed
    scheduler.start()
    logging.info("Scheduler started...")
