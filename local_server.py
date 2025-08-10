import sys
from os.path import abspath, dirname

# Añade esta línea para asegurar que Python encuentra tu paquete
sys.path.insert(0, dirname(abspath(__file__)))

from app import create_app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True, port=5000)