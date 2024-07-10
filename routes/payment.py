from flask import Blueprint, render_template, jsonify, request, url_for, redirect
import stripe
import os

payment_bp = Blueprint('payment', __name__)

stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

def get_stripe_price(price_id):
    price = stripe.Price.retrieve(price_id)
    return price.unit_amount, price.currency

# Define Stripe price IDs
price_ids = {
    'basic': 'price_1PZBUCLvebSJUJfhPnFmeZpI',
    'professional': 'price_1PaawvLvebSJUJfhPF8pxtIW',
    'enterprise': 'price_abcde'  # Replace with your actual Stripe Price ID for Enterprise Plan
}

@payment_bp.route('/create-checkout-session/<plan>', methods=['POST'])
def create_checkout_session(plan):
    if plan not in price_ids:
        return jsonify({"error": "Invalid plan"}), 400

    # For Enterprise plan, redirect to contact sales page
    if plan == 'enterprise':
        return redirect(url_for('payment.contact_sales'))

    # Fetch price details from Stripe
    try:
        amount, currency = get_stripe_price(price_ids[plan])
    except Exception as e:
        return jsonify(error=str(e)), 403

    plan_details = {
        'name': f'{plan.capitalize()} Plan',
        'amount': amount,
        'currency': currency
    }

    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[
                {
                    'price_data': {
                        'currency': plan_details['currency'],
                        'product_data': {
                            'name': plan_details['name'],
                        },
                        'unit_amount': plan_details['amount'],
                    },
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
