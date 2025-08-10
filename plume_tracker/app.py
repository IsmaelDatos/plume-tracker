import os
from flask import Flask, send_from_directory
from concurrent.futures import ThreadPoolExecutor

# Crea la instancia de Flask
app = Flask(
    __name__,
    template_folder=os.path.join(os.path.dirname(__file__), 'templates'),
    static_folder=os.path.join(os.path.dirname(__file__), 'static')
)

app.config['EXECUTOR_PROPAGATE_EXCEPTIONS'] = True
executor = ThreadPoolExecutor(max_workers=4)

# Importa blueprints después de crear la app
from plume_tracker.core.routes import bp as core_bp
app.register_blueprint(core_bp)

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(
        os.path.join(app.root_path, 'static'),
        'favicon.ico',
        mimetype='image/vnd.microsoft.icon'
    )

# Exporta la app para Vercel
app = app
handler = app  # Asegúrate de que esta línea esté al final del archivo