from flask import request, jsonify, Blueprint
from app.models.product import Product
from app.utils import logger
from app.middleware import postman_consultant_token_required


product = Blueprint("product", __name__)

@product.route("/", methods=["POST"])
@postman_consultant_token_required
def create_product():
    try:
        data = request.json
        
        if "name" not in data:
            logger.error("Missing fields in body")
            return jsonify({"error": "Missing required fields"}), 400
        
        product = Product.create_product(data)
        logger.info(f"Created new product {data['name']}")
        return jsonify({"message": "Created new product", "data": product.to_dict()}), 201
    except Exception as e:
        logger.error({"error": str(e)})
        return jsonify({"error": "Internal Server Error"}), 500
    
@product.route("/", methods=["GET"])
@postman_consultant_token_required
def get_all_products():
    try:
        products = Product.query.all()
        return jsonify([product.to_dict() for product in products]), 200
    except Exception as e:
        logger.critical("Failed to gather products", exc_info=e)
        return jsonify({"error": "Internal Server Error"}), 500

@product.route("/<id>", methods=["GET"])
@postman_consultant_token_required
def get_one_product(id):
    try:
        product = Product.query.get(id)
        if product is None:
            return jsonify({"error": "Product doesn't exist"}), 404
        return jsonify(product.to_dict()), 200
    except Exception as e:
        logger.critical("Failed to gather product", exc_info=e)
        return jsonify({"error": "Internal Server Error"}), 500

@product.route("/<id>", methods=["PUT"])
@postman_consultant_token_required
def update_product(id):
    try:
        data = request.json
        product = Product.update_product(id, data)
        return jsonify({"message": "Updated product", "data": product.to_dict()}), 200
    except Exception as e:
        logger.error({"error": str(e)})
        return jsonify({"error": "Internal Server Error"}), 500

@product.route("/<id>", methods=["DELETE"])
@postman_consultant_token_required
def delete_product(id):
    try:
        Product.delete_product(id)
        return jsonify({"message": "Product deleted"}), 200
    except Exception as e:
        logger.error({"error": str(e)})
        return jsonify({"error": "Internal Server Error"}), 500
    