import json
from flask import Flask, request, jsonify
from datetime import datetime, timedelta, timezone
from flask_jwt_extended import create_access_token, get_jwt, get_jwt_identity, unset_jwt_cookies, jwt_required, JWTManager
import os
from pymongo import MongoClient
from passlib.hash import pbkdf2_sha256
from dotenv import load_dotenv, find_dotenv
from waitress import serve

# flask
api = Flask(__name__)

api.config["JWT_SECRET_KEY"] = "xwmq1cf4xqkjmv4tcnh8hepa822n8yog"
api.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=1)
jwt = JWTManager(api)

# db
load_dotenv(find_dotenv())
password = os.environ.get("MONGODB_PWD")

connection_string = f"mongodb+srv://CodeNinjas:{password}@codeninjas.lppiwo8.mongodb.net/?retryWrites=true&w=majority&appName=codeninjas"
client = MongoClient(connection_string)

databases = client.list_database_names()
userLogin_database = client.loginData
userData_database = client.userData

# sign up
@api.route('/signup', methods=["POST"])
def signup():
    user = {
        "email": request.json.get("email"),
        "password": pbkdf2_sha256.encrypt(request.json.get("password"))
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
            "tasks": [[]],
            "isTeacher": False
        }
    

    if userLogin_database.users.find_one({"email": user["email"]}):
        return {"msg": "Email already in use"}, 400

    if userLogin_database.users.insert_one(user) and userData_database.userData.insert_one(userData):
        return {"msg": "Sign up succeeded"}, 200
    
    return {"msg": "Error, one or both parts of signup failed"}, 400


# logging in
@api.route('/token', methods=["POST"])
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

@api.route('/getacctype', methods=["GET"])
@jwt_required()
def get_acctype():
    current_user = get_jwt_identity()
    userData = userData_database.userData.find_one({"email": current_user})
    response = {'isTeacher': userData['isTeacher']}
    return response

@api.route('/profile', methods=["GET"])
@jwt_required()
def my_profile():
    current_user = get_jwt_identity()
    print("User, " + current_user + ", made a request for their profile")
    response_body = userData_database.userData.find_one({
        "email": current_user
    })
    del response_body['_id']
    if response_body:
        profile = json.dumps(response_body)
        return profile

    return {"msg": "Something went wrong with your token"}, 400

@api.route('/getallstudents', methods=["GET"])
@jwt_required()
def get_allstudents():
    current_user = get_jwt_identity()
    teacherData = userData_database.userData.find_one({"email": current_user})
    if not teacherData['isTeacher']:
        return {"msg": "Account not authorized to complete action"}, 400
    
    allStudents = userData_database.userData.find({"isTeacher": False})
    response = []
    for student in allStudents:
        del student['_id']
        response.append(student)
    return response, 200

@api.route('/setnb', methods=["POST"])
@jwt_required()
def set_ninjabucks():
    current_user = get_jwt_identity()
    teacherData = userData_database.userData.find_one({"email": current_user})
    if not teacherData['isTeacher']:
        return {"msg": "Account not authorized to complete action"}, 400
    
    studentQuery = {"email": request.json.get("email")}
    studentData = userData_database.userData.find_one(studentQuery)
    if studentData:
        nb = request.json.get("nb")
        newData = { "$set": { 'nb': nb } }
        userData_database.userData.update_one(studentQuery, newData)
        print("nb of " + request.json.get("email") + " have been updated to: " + str(nb))
        return {"msg": studentData['email'] + "'s ninja bucks have been updated successfully"}, 200
    
    return {"msg": "Student not found"}, 500

@api.route('/settasks', methods=["POST"])
@jwt_required()
def set_tasks():
    current_user = get_jwt_identity()
    teacherData = userData_database.userData.find_one({"email": current_user})
    if not teacherData['isTeacher']:
        return {"msg": "Account not authorized to complete action"}, 400

    tasks = request.json.get("tasks")
    studentQuery = {"email": request.json.get("email")}
    newData = { "$set": { 'tasks': tasks } }
    if userData_database.userData.update_one(studentQuery, newData):
        return {"msg": request.json.get("email") + "'s tasks have been updated successfully"}

    return {"msg": "Student not found"}, 500

hostip = '192.168.86.20'
port = 50100
if __name__ == '__main__':
    print("Server running on: "  + hostip + ":" + str(port))
    serve(api, host=hostip, port=port, threads=2)
