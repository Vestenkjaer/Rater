from flask import Blueprint, request, jsonify, render_template
from models import db, Client, User

client_management_bp = Blueprint('client_management', __name__)

@client_management_bp.route('/client_setup')
def client_setup():
    clients = Client.query.all()
    return render_template('client_setup.html', clients=clients)

@client_management_bp.route('/add_client', methods=['POST'])
def add_client():
    try:
        data = request.get_json()
        client_name = data.get('client_name')
        admin_username = data.get('admin_username')
        admin_email = data.get('admin_email')
        admin_password = data.get('admin_password')

        # Create new client
        new_client = Client(name=client_name, is_blocked=False)
        db.session.add(new_client)
        db.session.commit()

        # Create admin user
        admin_user = User(username=admin_username, email=admin_email, client_id=new_client.id, is_admin=True)
        admin_user.password = admin_password
        db.session.add(admin_user)
        db.session.commit()

        return jsonify({'message': 'Client and admin user created successfully'}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@client_management_bp.route('/edit_client/<int:client_id>', methods=['POST'])
def edit_client(client_id):
    try:
        data = request.get_json()
        client = Client.query.get(client_id)
        if not client:
            return jsonify({'error': 'Client not found'}), 404
        
        client.name = data.get('client_name', client.name)
        db.session.commit()

        return jsonify({'message': 'Client updated successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@client_management_bp.route('/delete_client/<int:client_id>', methods=['DELETE'])
def delete_client(client_id):
    try:
        client = Client.query.get(client_id)
        if not client:
            return jsonify({'error': 'Client not found'}), 404
        
        db.session.delete(client)
        db.session.commit()

        return jsonify({'message': 'Client deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@client_management_bp.route('/get_client_users/<int:client_id>', methods=['GET'])
def get_client_users(client_id):
    try:
        client = Client.query.get(client_id)
        if not client:
            return jsonify({'error': 'Client not found'}), 404
        
        users = User.query.filter_by(client_id=client_id).all()
        users_data = [{'id': user.id, 'username': user.username, 'email': user.email, 'is_admin': user.is_admin} for user in users]

        return jsonify({'client_name': client.name, 'users': users_data}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@client_management_bp.route('/edit_user/<int:user_id>', methods=['POST'])
def edit_user(user_id):
    try:
        data = request.get_json()
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        user.username = data.get('username', user.username)
        user.email = data.get('email', user.email)
        if data.get('password'):
            user.password = data.get('password')
        db.session.commit()

        return jsonify({'message': 'User updated successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@client_management_bp.route('/delete_user/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        db.session.delete(user)
        db.session.commit()

        return jsonify({'message': 'User deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@client_management_bp.route('/toggle_client_block/<int:client_id>', methods=['POST'])
def toggle_client_block(client_id):
    try:
        client = Client.query.get(client_id)
        if not client:
            return jsonify({'error': 'Client not found'}), 404
        
        client.is_blocked = not client.is_blocked
        db.session.commit()

        return jsonify({'message': f'Client {"blocked" if client.is_blocked else "unblocked"} successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
