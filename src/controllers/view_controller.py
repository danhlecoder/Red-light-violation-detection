"""
View controller for the traffic monitoring system
"""
from flask import Blueprint, render_template, send_from_directory

from src.core.config import logger

# Create views blueprint
views = Blueprint('views', __name__)

@views.route('/')
def index():
    """Render index page"""
    return render_template('index.html') 