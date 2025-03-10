"""
Tag routes and controllers
"""
from flask import Blueprint, request, jsonify
from app.tags.models import find_all_tags, find_tag_by_name

# Create Blueprint
tags_bp = Blueprint('tags', __name__, url_prefix='/api/tags')

@tags_bp.route('', methods=['GET'])
def get_tags():
    """Get all tags and their counts"""
    tags = find_all_tags()
    return jsonify(tags)