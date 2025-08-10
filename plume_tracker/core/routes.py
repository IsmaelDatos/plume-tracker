from flask import Blueprint, jsonify, render_template
from .services import PlumeService

bp = Blueprint('core', __name__)
service = PlumeService()

@bp.route('/')
def home():
    return render_template('index.html')

@bp.route('/api/top-earners')
async def top_earners():
    results = await service.get_top_earners()
    return jsonify(results)