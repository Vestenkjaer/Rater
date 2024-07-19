from flask import Blueprint, render_template, redirect, url_for, session, request, jsonify
from models import User, Client  # Ensure this import is correct based on your project structure
import logging

index_bp = Blueprint('index', __name__)

@index_bp.route('/')
def home():
    return render_template('index.html')

@index_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = authenticate_user(email, password)
        if user:
            session['user_id'] = user.id
            session['client_id'] = user.client_id  # Assuming user model has client_id
            session['tier'] = user.client.tier
            session['is_admin'] = user.is_admin
            return redirect(url_for('dashboard.dashboard'))  # Ensure this corresponds to your dashboard route
        return 'Login Failed', 401
    return render_template('login.html')

def authenticate_user(email, password):
    user = User.query.filter_by(email=email).first()
    if user and user.verify_password(password):  # Assuming User model has verify_password method
        return user
    return None

@index_bp.route('/user_info')
def user_info():
    user_id = session.get('user_id')
    client_id = session.get('client_id')
    if not user_id or not client_id:
        return jsonify({'error': 'User not authenticated'}), 401

    user = User.query.get(user_id)
    client = Client.query.get(client_id)

    if not user or not client or user.client_id != client.id:
        return jsonify({'error': 'User or client not found or mismatch'}), 404

    return jsonify({
        'name': user.username,
        'email': user.email,
        'tier': client.tier
    })

# Ensure this Blueprint is registered in your create_app function in app.py
