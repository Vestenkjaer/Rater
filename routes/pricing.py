# routes/pricing.py
from flask import Blueprint, render_template

pricing_bp = Blueprint('pricing', __name__)

@pricing_bp.route('/')
def pricing():
    return render_template('pricing.html')