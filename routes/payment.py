from flask import Blueprint, jsonify, request, url_for, redirect, render_template
import stripe
import os

payment_bp = Blueprint('payment', __name__)

stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

@payment_bp.route('/buy/<plan>', methods=['POST'])
def buy(plan):
    # Define product details based on the plan
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

    # For Enterprise plan, redirect to contact sales page
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
        return jsonify({'id': checkout_session.id})
    except Exception as e:
        return jsonify(error=str(e)), 403

@payment_bp.route('/success')
def success():
    session_id = request.args.get('session_id')
    session_data = stripe.checkout.Session.retrieve(session_id)
    return render_template('success_page.html', session_data=session_data)

@payment_bp.route('/cancel')
def cancel():
    return "Payment was canceled!"

@payment_bp.route('/contact/sales')
def contact_sales():
    return "Please contact our sales team for enterprise solutions."
