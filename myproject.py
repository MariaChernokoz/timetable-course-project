from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user
from app import app
login_manager = LoginManager()
login_manager.init_app(app)
