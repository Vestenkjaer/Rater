from flask import Blueprint, jsonify, request, url_for, redirect, render_template, session
import stripe
import os
from models import db, User
import logging

payment_bp = Blueprint('payment', __name__)

stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

logger = logging.getLogger(__name__)

def determine_tier(plan):
    plan_tiers = {
        'basic': 1,
        'professional': 2,
        'enterprise': 3
    }
    return plan_tiers.get(plan, 0)

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
            success_url=url_for('payment.success', plan=plan, _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=url_for('payment.cancel', _external=True),
        )
        return jsonify({'id': checkout_session.id})
    except Exception as e:
        logger.error(f"Error creating checkout session: {str(e)}")
        return jsonify(error=str(e)), 403

@payment_bp.route('/success')
def success():
    session_id = request.args.get('session_id')
    plan = request.args.get('plan')
    if not session_id or not plan:
        return jsonify({"error": "Session ID or plan is missing"}), 400

    try:
        session_data = stripe.checkout.Session.retrieve(session_id)
        customer_email = session_data['customer_details']['email']
        subscription_id = session_data['subscription']
        subscription = stripe.Subscription.retrieve(subscription_id)
        plan_id = subscription['items']['data'][0]['price']['product']
        tier = determine_tier(plan)

        if 'user' in session:
            # Update existing user tier if logged in
            email = session['user']['email']
            user = User.query.filter_by(email=email).first()
            if user:
                user.client.tier = tier
                db.session.commit()
                return render_template('success_page.html', session_id=session_id, show_home_button=True, registration_needed=False)
            else:
                return jsonify({'error': 'User not found'}), 404
        else:
            # No user in session, show registration form
            return render_template('success_page.html', session_id=session_id, show_home_button=False, registration_needed=True, plan=plan)
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@payment_bp.route('/cancel')
def cancel():
    return "Payment was canceled!"

@payment_bp.route('/contact/sales')
def contact_sales():
    return "Please contact our sales team for enterprise solutions."
