"""
Vault routes and controllers
"""
from flask import Blueprint, request, jsonify
from app.vaults.models import (
    find_all_vaults, find_vault_by_id, 
    create_vault, update_vault, delete_vault
)

# Create Blueprint
vaults_bp = Blueprint('vaults', __name__, url_prefix='/api/vaults')

@vaults_bp.route('', methods=['GET'])
def get_vaults():
    """Get all vaults"""
    vaults = find_all_vaults()
    return jsonify(vaults)

@vaults_bp.route('', methods=['POST'])
def create_new_vault():
    """Create a new vault"""
    data = request.json
    if not data or 'name' not in data:
        return jsonify({'error': 'Name is required'}), 400
    
    vault = create_vault(data)
    return jsonify(vault), 201

@vaults_bp.route('/<vault_id>', methods=['PUT'])
def update_existing_vault(vault_id):
    """Update a vault"""
    data = request.json
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    result = update_vault(vault_id, data)
    
    if 'error' in result:
        return jsonify(result), 400 if 'Invalid' in result['error'] else 404
    
    return jsonify(result)

@vaults_bp.route('/<vault_id>', methods=['DELETE'])
def delete_existing_vault(vault_id):
    """Delete a vault and all its notes"""
    result = delete_vault(vault_id)
    
    if 'error' in result:
        return jsonify(result), 400 if 'Invalid' in result['error'] else 404
    
    return jsonify(result)