from app import api, userLogin_database, userData_database
import json
from flask import request, jsonify
from datetime import datetime, timedelta, timezone
from flask_jwt_extended import create_access_token, get_jwt, get_jwt_identity, unset_jwt_cookies, jwt_required, JWTManager
from passlib.hash import pbkdf2_sha256
from flask_cors import cross_origin

# sign up
@api.route('/signup', methods=["POST"])
def signup():
    user = {
        "email": request.json.get("email"),
        "password": pbkdf2_sha256.hash(request.json.get("password"))
    }

    userData = {}
    current_datetime = datetime.now()
    if request.json.get("isTeacher"):
        userData = {
            "email": request.json.get("email"),
            "name": request.json.get("name"),
            "join_date": current_datetime.strftime("%m/%d/%Y"),
            "isTeacher": True
        }
    else:
        userData = {
            "email": request.json.get("email"),
            "name": request.json.get("name"),
            "join_date": current_datetime.strftime("%m/%d/%Y"),
            "nb": 0,
            "tasks": [],
            "notes": {
                "rank": "n/a",
                "age": "n/a",
                "membership": "n/a",
                "sensei": "n/a",
                "platform": "n/a",
                "dateofbirth": "n/a",
                "lastcontacted": "n/a",
                "lastadvanced": "n/a",
                "progress": "n/a",
                "status": "n/a",
                "entries": []
            },
            "isTeacher": False
        }
    

    if userLogin_database.users.find_one({"email": user["email"]}):
        return {"msg": "Email already in use"}, 400

    if userLogin_database.users.insert_one(user) and userData_database.userData.insert_one(userData):
        return {"msg": "Sign up succeeded"}, 200
    
    return {"msg": "Error, one or both parts of signup failed"}, 400


# logging in
@api.route('/token', methods=["POST"])
@cross_origin()
def create_token():
    email = request.json.get("email", None)
    password = request.json.get("password", None)

    user = userLogin_database.users.find_one({
        "email": email
    })

    if user and pbkdf2_sha256.verify(password, user['password']):
        access_token = create_access_token(identity=email)
        response = {"access_token": access_token}
        return response
    
    return {"msg": "Wrong email or password"}, 401
    
# logging out
@api.route("/logout", methods=["POST"])
def logout():
    response = jsonify({"msg": "logout successful"})
    unset_jwt_cookies(response)
    return response

@api.after_request
def refresh_expiring_jwts(response):
    try:
        exp_timestamp = get_jwt()["exp"]
        now = datetime.now(timezone.utc)
        target_timestamp = datetime.timestamp(now + timedelta(minutes=30))
        if target_timestamp > exp_timestamp:
            access_token = create_access_token(identity=get_jwt_identity())
            data = response.get_json()
            if type(data) is dict:
                data["access_token"] = access_token
                response.data = json.dumps(data)
        return response
    except (RuntimeError, KeyError):
        return response