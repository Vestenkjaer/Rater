from flask import Blueprint, jsonify, request, url_for, redirect, render_template, session
import stripe
import os

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

        # Retrieve the client by email
        client = Client.query.filter_by(email=customer_email).first()
        if client:
            desired_tier = session.get('desired_tier', client.tier)
            client.tier = max(client.tier, desired_tier)
            db.session.commit()
            session['tier'] = client.tier
        else:
            return jsonify({"error": "Client not found"}), 404

        registration_needed = False if 'user' in session else True

        return render_template('success_page.html', session_data=session_data, registration_needed=registration_needed)
    except stripe.error.InvalidRequestError as e:
        return jsonify(error=str(e)), 400

@payment_bp.route('/cancel')
def cancel():
    return "Payment was canceled!"

@payment_bp.route('/contact/sales')
def contact_sales():
    return "Please contact our sales team for enterprise solutions."
