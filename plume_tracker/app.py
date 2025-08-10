import os
from flask import Flask
from concurrent.futures import ThreadPoolExecutor

def create_app():
    template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'templates'))
    static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'static'))

    app = Flask(__name__,
               template_folder=template_dir,
               static_folder=static_dir)
    
    app.config['EXECUTOR_PROPAGATE_EXCEPTIONS'] = True
    executor = ThreadPoolExecutor(max_workers=4)

    from .core.routes import bp as core_bp
    app.register_blueprint(core_bp)

    return app
