from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_mail import Mail
from flask_jwt_extended import JWTManager

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
mail = Mail()
jwt = JWTManager()


# 用户加载函数
@login_manager.user_loader
def load_user(user_id):
    from blog.models import User
    user = User.query.get(int(user_id))
    return user
