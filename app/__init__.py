from flask import Flask
from .config import Config
from .models import db
from .routes import api

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialize extensions
    db.init_app(app)
    
    # Register blueprints
    app.register_blueprint(api, url_prefix='/api')
    
    # Create database tables if they don't exist
    with app.app_context():
        db.create_all()
    
    @app.route('/')
    def index():
        return {
            'status': 'ok',
            'message': 'MMA Data API is running'
        }
    
    return app 