from functools import wraps
from flask import request, jsonify, g
from app.config import CLERK_CLIENT
from app.middleware.auth import token_required

def postman_consultant_token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        consultant_id = request.headers.get("X-Consultant-Id")
        if consultant_id:
            try:
                # Check if a consultant with this ID exists in Clerk.
                user = CLERK_CLIENT.users.get(user_id=consultant_id)
                if not user:
                    return jsonify({"error": "Consultant not found in Clerk"}), 404
            except Exception as e:
                return jsonify({"error": "Error verifying consultant with Clerk", "message": str(e)}), 500

            # Set the consultant's ID in Flask's global context.
            g.user_id = consultant_id
            g.provisional_auth = True
            return f(*args, **kwargs)
        else:
            # Fallback to standard token verification.
            return token_required(f)(*args, **kwargs)
    return decorated
