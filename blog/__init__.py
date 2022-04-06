import os
from flask import Flask
from blog.settings import config
from blog.blueprints.users import users_bp
from blog.blueprints.tags import tags_bp
from blog.blueprints.articles import articles_bp
from blog.estensions import migrate, db, login_manager, mail, jwt
from blog.models import User, Article, Tag, Comment


# 工厂函数
def create_app(config_name=None):
    if config_name is None:
        config_name = os.getenv('FLASK_CONFIG', 'development')
    app = Flask('blog')
    app.config.from_object(config[config_name])
    register_blueprints(app)
    register_extensions(app)
    register_shell_context(app)
    return app


def register_blueprints(app):
    app.register_blueprint(users_bp)
    app.register_blueprint(articles_bp)
    app.register_blueprint(tags_bp)


def register_extensions(app):
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    mail.init_app(app)
    jwt.init_app(app)


def register_shell_context(app):
    @app.shell_context_processor
    def shell_context():
        return dict(db=db, User=User, Article=Article, Comment=Comment, Tags=Tag)
