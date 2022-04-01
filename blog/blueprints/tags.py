from flask import Blueprint, jsonify
from blog.models import Tag


tags_bp = Blueprint('tags', __name__)


@tags_bp.route('/api/tags', methods=['GET'])
def get_tags():
    ret_data = {
        "data": {'tags': [tag.name for tag in Tag.query.all()]},
        'message': 'null',
        'code': 10000,
    }
    return jsonify(ret_data)
