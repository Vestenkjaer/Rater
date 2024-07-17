from flask import Blueprint, jsonify, request, url_for, redirect, render_template, session
import stripe
import os
from models import Client, db  # Ensure these are imported

payment_bp = Blueprint('payment', __name__)

stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

@payment_bp.route('/buy/<plan>', methods=['POST'])
def buy(plan):
    plans = {
        'basic': {
            'name': 'Basic Plan',
            'price_id': os.getenv('BASIC_PLAN_PRICE_ID'),
            'tier': 1
        },
        'professional': {
            'name': 'Professional Plan',
            'price_id': os.getenv('PROFESSIONAL_PLAN_PRICE_ID'),
            'tier': 2
        },
        'enterprise': {
            'name': 'Enterprise Plan',
            'price_id': os.getenv('ENTERPRISE_PLAN_PRICE_ID'),
            'tier': 3
        }
    }

    if plan not in plans:
        return jsonify({"error": "Invalid plan"}), 400

    if plan == 'enterprise':
        return redirect(url_for('payment.contact_sales'))

    plan_details = plans[plan]
    session['desired_tier'] = plan_details['tier']

    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[
                {
                    'price': plan_details['price_id'],
                    'quantity': 1,
                },
            ],
            mode='subscription',
            success_url=url_for('payment.success', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=url_for('payment.cancel', _external=True),
        )
        return jsonify({'id': checkout_session.id})
    except Exception as e:
        return jsonify(error=str(e)), 403

@payment_bp.route('/success')
def success():
    session_id = request.args.get('session_id')
    if not session_id:
        return jsonify({"error": "Session ID is missing"}), 400

    try:
        session_data = stripe.checkout.Session.retrieve(session_id)
        customer_email = session_data['customer_details']['email']
        customer_name = session_data['customer_details'].get('name', customer_email)  # Use email as name if not provided

        # Retrieve the client by email
        client = Client.query.filter_by(email=customer_email).first()
        desired_tier = session.get('desired_tier', 1)
        
        if client:
            # Update the client's tier if it's lower than the desired tier
            client.tier = max(client.tier, desired_tier)
        else:
            # Create a new client if not existing
            client = Client(
                email=customer_email,
                name=customer_name,  # Use the customer_name here
                tier=desired_tier,
                is_admin=True
            )
            db.session.add(client)
        
        db.session.commit()
        
        # Update the session with the client's tier and is_admin status
        session['tier'] = client.tier
        session['is_admin'] = client.is_admin
        session['client_id'] = client.id
        session['user_id'] = client.id  # For now set user_id to client.id

        registration_needed = 'user' not in session

        return render_template('success_page.html', session_data=session_data, registration_needed=registration_needed)
    except stripe.error.InvalidRequestError as e:
        return jsonify(error=str(e)), 400

@payment_bp.route('/cancel')
def cancel():
    return "Payment was canceled!"

@payment_bp.route('/contact/sales')
def contact_sales():
    return "Please contact our sales team for enterprise solutions."
