from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf import CSRFProtect
from config import Config
from flask_mail import Mail




db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()
mail=Mail()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    mail.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    # Flask-Login configuration
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'

    # Register Blueprints
    from app.routes.dashboard import dashboard_bp
    from app.routes.secretary import secretary_bp
    from app.routes.finance import finance_bp
    from app.routes.auth import auth_bp
    from app.routes.member import member_bp
    from app.routes.chair import chair_bp
    
    
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(member_bp)
    app.register_blueprint(chair_bp)
    app.register_blueprint(secretary_bp)
    app.register_blueprint(finance_bp)

    # Main Landing Page Route
    @app.route('/')
    def index():
        return render_template('index.html')

    return app