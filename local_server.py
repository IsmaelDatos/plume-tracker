import sys
from os.path import abspath, dirname

sys.path.insert(0, dirname(abspath(__file__)))
from plume_tracker.app import app
if __name__ == '__main__':
    app.run(debug=True, port=5000)