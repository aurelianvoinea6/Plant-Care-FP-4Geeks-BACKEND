"""
This module takes care of starting the API Server, Loading the DB and Adding the endpoints
"""
import os
from flask import Flask, request, jsonify, url_for, make_response
from flask_migrate import Migrate
from flask_swagger import swagger
from flask_cors import CORS
from utils import APIException, generate_sitemap, token_required
from admin import setup_admin
from models import db, Room, Users, Plants_Type, Plants_Grow_Phase, Plants_Sensors, Plants

from init_database import init_db
from werkzeug.security import generate_password_hash, check_password_hash
import uuid
import jwt
import datetime

app = Flask(__name__)
app.app_context().push()
data_base = os.environ['DB_CONNECTION_STRING']

app.url_map.strict_slashes = False
app.config['SQLALCHEMY_DATABASE_URI'] = data_base
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

MIGRATE = Migrate(app, db)
db.init_app(app)

CORS(app)
setup_admin(app)
app.cli.add_command(init_db)

@app.route('/user/<int:user_id>/rooms', methods=['POST'])
def add_new_room(user_id):  
    body = request.get_json()
    if body is None:
        raise APIException("You need to specify the request body as a json object", status_code=400)
    if 'name_room' not in body:
        raise APIException('You need to specify the name room', status_code=400)

    new_room = Room(name_room=body['name_room'], id_user=body["id_user"])
    new_room.create()

    return jsonify({'status': 'OK', 'message': 'Room Added succesfully'}), 201

@app.route('/user/<int:user_id>/rooms', methods=['GET'])
def get_rooms(user_id):
    rooms = Room.read_by_user(user_id)
    if rooms is None:
        return "You need to specify the request room as a json object, is empty", 400
    return jsonify(rooms), 200

@app.route('/user/<int:user_id>/rooms/<int:room_id>', methods=['PATCH'])
def update_room(user_id, room_id):
    body = request.get_json()
    if body is None:
        return "You need to specify the request body as a json object", 400

    room_to_update = Room.read_by_id(room_id)
    room_updated = room_to_update.update_room(body["name_room"])

    return jsonify(room_updated), 200

@app.route('/user/<int:user_id>/rooms/<int:room_id>', methods=['DELETE'])
def delete_room_user(user_id, room_id):
    room_to_delete = Room.read_by_id(room_id)
    room_deleted = room_to_delete.delete_room()

    return jsonify(room_to_delete.serialize()), 200

@app.route('/user/<int:user_id>/rooms/<int:room_id>/plants', methods=['POST'])
def add_new_plant(user_id, room_id):  
    body = request.get_json()
    if body is None:
        raise APIException("You need to specify the request body as a json object", status_code=400)
    if 'id_room' not in body:
        raise APIException('You need to specify the id room', status_code=400)
    if 'name_plant' not in body:
        raise APIException('You need to specify the name of the plant', status_code=400)
    if 'type_plant' not in body:
        raise APIException('You need to specify the type of plant', status_code=400)
    if 'grow_phase' not in body:
        raise APIException('You need to specify the grow phase', status_code=400)

    new_plant = Plants(id_room=body['id_room'], name_plant=body["name_plant"], type_plant=body["type_plant"], grow_phase=body["grow_phase"], sensor_number=body["sensor_number"]) 
    new_plant.create()

    return jsonify({'status': 'OK', 'message': 'Plant Added succesfully'}), 200

@app.route('/user/<int:user_id>/rooms/<int:room_id>/plants', methods=['GET'])
def get_plants(user_id, room_id):
    plants = Plants.read_by_id(room_id)
    if plants is None:
        return "Plants not found in this room", 400
    return jsonify(plants), 200

@app.route('/user/<int:user_id>/rooms/<int:room_id>/plants/<int:plant_id>', methods=['GET'])
def get_single_plant(user_id, room_id, plant_id):
    single_plant = Plants.read_by_id_single_plant(plant_id, room_id)
    if single_plant is None:
        return "The single plant object is empty", 400
    return jsonify(single_plant), 200

@app.route('/grows', methods=['GET'])
def get_grows():
    grows = Plants_Grow_Phase.read_all_grow()
    if grows is None:
        return "The grow object is empty", 400
    return jsonify(grows), 200

@app.route('/types', methods=['GET'])
def get_types():
    types = Plants_Type.read_all_type()
    if types is None:
        return "The type object is empty", 400
    return jsonify(types), 200

# Handle/serialize errors like a JSON object
@app.errorhandler(APIException)
def handle_invalid_usage(error):
    return jsonify(error.to_dict()), error.status_code

# generate sitemap with all your endpoints
@app.route('/')
def sitemap():
    return generate_sitemap(app)


@app.route('/register', methods=['GET', 'POST'])
def signup_user():  
 data = request.get_json()  

 hashed_password = generate_password_hash(data['password'], method='sha256')
 
 new_user = Users(username=data['username'], email=data['email'], password=hashed_password, location=data['location'], is_active=True) 
 new_user.create_user()

 return jsonify({'message': 'Registered successfully'})

@app.route('/login', methods=['POST'])
def login_user():
    body = request.get_json()
    
    if "x-acces-tokens" not in request.headers:
        if not body or not body["email"] or not body["password"]:
            return "Email or Password Invalid", 401
      
        user = Users.read_user_by_mail(body["email"])
        print(user)
    
        if check_password_hash(user.password, body["password"]):
            token = jwt.encode({'id': user.id, 'exp' : datetime.datetime.utcnow() + datetime.timedelta(minutes=30)}, app.config['SECRET_KEY'])
            return jsonify({'token' : token.decode('UTF-8')}, 200)
        
        return "Password Invalid", 400
    
    else:
        return "Welcome", 200

@app.route('/users', methods=['GET'])
def get_all_users():
    users = Users.query.all()
    result = []

    for user in users:
        user_data = {}
        user_data['email'] = user.email  
        user_data['password'] = user.password

        result.append(user_data)
        return jsonify({'users': result})

if __name__ == '__main__':
    PORT = int(os.environ.get('PORT', 3000))
    app.run(host='0.0.0.0', port=PORT, debug=False)
