from flask import Flask
import os
from concurrent.futures import ThreadPoolExecutor

executor = ThreadPoolExecutor(max_workers=4)

def create_app():
    app = Flask(
        __name__,
        template_folder=os.path.join(os.path.dirname(__file__), 'templates'),
        static_folder=os.path.join(os.path.dirname(__file__), 'static')
    )

    app.config['EXECUTOR_PROPAGATE_EXCEPTIONS'] = True

    from plume_tracker.core.routes import bp as core_bp
    app.register_blueprint(core_bp)

    return app
