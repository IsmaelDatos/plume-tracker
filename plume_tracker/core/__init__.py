from flask import Blueprint
from .routes import bp

def create_core_app(app):
    app.register_blueprint(bp)
    return app

__all__ = ['create_core_app']