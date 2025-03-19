from functools import wraps
from flask import request, jsonify, g
import jwt
from jwt.exceptions import InvalidTokenError
from app.config import CLERK_CLIENT, get_config
import os

config = get_config(os.getenv("FLASK_ENV"))
CLERK_PUBLIC_KEY = config.CLERK_PEM_PUBLIC_KEY
def token_required(allowed_user_types=None):
    """
    Decorator that verifies a token and optionally ensures that the user's type (from Clerk metadata)
    is one of the allowed_user_types. If allowed_user_types is None, no user type check is performed.
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            auth_header = request.headers.get("Authorization")
            if not auth_header:
                return jsonify({"error": "Missing token"}), 401

            parts = auth_header.split()
            if len(parts) != 2 or parts[0].lower() != "bearer":
                return jsonify({"error": "Invalid token format. Expected 'Bearer <token>'."}), 401

            token = parts[1]
            try:
                # Verify the token using Clerk
                decode = jwt.decode(token, CLERK_PUBLIC_KEY, algorithms=["RS256"])
            except Exception as e:
                return jsonify({"error": "Token verification failed", "message": str(e)}), 401

            # # Store session info in Flask's global context
            g.session = decode
            g.user_id = decode.get("id") or decode.get("sub")

            # If allowed_user_types is provided, check the user's type.
            if allowed_user_types is not None:
                # Assuming the user type is stored in the public_metadata of the decode
                public_metadata = decode.get("public_metadata", {})
                user_type = public_metadata.get("user_type")
                if user_type not in allowed_user_types:
                    return jsonify({"error": "Unauthorized user type"}), 403

            return f(*args, **kwargs)
        return decorated
    return decorator
