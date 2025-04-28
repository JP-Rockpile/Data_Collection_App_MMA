from flask import Flask, redirect, url_for
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from flask_sqlalchemy import SQLAlchemy
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize SQLAlchemy instance
db = SQLAlchemy()

def create_app():
    app = Flask(__name__)
    
    # Database configuration
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
    
    # Initialize extensions
    db.init_app(app)
    
    # Import models
    from .models import Fighter, Event, Fight, FightRoundStats
    
    # Initialize Admin
    admin = Admin(app, name='MMA Data Collection', template_mode='bootstrap3')
    
    # Add model views
    admin.add_view(ModelView(Fighter, db.session))
    admin.add_view(ModelView(Event, db.session))
    admin.add_view(ModelView(Fight, db.session))
    admin.add_view(ModelView(FightRoundStats, db.session))
    
    @app.route('/')
    def index():
        return redirect(url_for('admin.index'))
    
    # Register blueprints if needed
    # from .routes import api
    # app.register_blueprint(api, url_prefix='/api')
    
    # Create tables when app is created
    with app.app_context():
        db.create_all()
    
    return app 