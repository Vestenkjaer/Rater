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
            'price_id': os.getenv('BASIC_PLAN_PRICE_ID'),  # Use environment variables to store Stripe price IDs
        },
        'professional': {
            'name': 'Professional Plan',
            'price_id': os.getenv('PROFESSIONAL_PLAN_PRICE_ID'),
        },
        'enterprise': {
            'name': 'Enterprise Plan',
            'price_id': os.getenv('ENTERPRISE_PLAN_PRICE_ID'),
        }
    }

    if plan not in plans:
        return jsonify({"error": "Invalid plan"}), 400

    if plan == 'enterprise':
        return redirect(url_for('payment.contact_sales'))

    plan_details = plans[plan]

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
        session['checkout_session_id'] = checkout_session.id  # Store session ID in Flask session
        session['plan'] = plan  # Store the plan in Flask session
        return jsonify({'id': checkout_session.id})
    except Exception as e:
        return jsonify(error=str(e)), 403

@payment_bp.route('/success')
def success():
    session_id = request.args.get('session_id')
    if not session_id:
        session_id = session.get('checkout_session_id')  # Retrieve session ID from Flask session

    plan = session.get('plan')  # Retrieve the plan from Flask session

    if not session_id or not plan:
        return jsonify({"error": "Session ID or plan is missing"}), 400

    try:
        session_data = stripe.checkout.Session.retrieve(session_id)
        registration_needed = True if not session.get('user') else False
        show_home_button = not registration_needed

        return render_template('success_page.html', session_data=session_data, registration_needed=registration_needed, show_home_button=show_home_button)
    except stripe.error.InvalidRequestError as e:
        return jsonify({"error": str(e)}), 400

@payment_bp.route('/cancel')
def cancel():
    return "Payment was canceled!"

@payment_bp.route('/contact/sales')
def contact_sales():
    return "Please contact our sales team for enterprise solutions."
