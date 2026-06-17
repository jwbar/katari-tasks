from pymongo import MongoClient
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from datetime import datetime

client = MongoClient('mongodb://localhost:27017/')
db = client.assignment_db

class User(UserMixin):
    def __init__(self, user_data):
        self.id = str(user_data['_id'])
        self.username = user_data['username']
        self.email = user_data.get('email', '')
        self.role = user_data['role']
        self.active = user_data.get('active', True)
    
    @staticmethod
    def get_by_id(user_id):
        user_data = db.users.find_one({'_id': ObjectId(user_id)})
        return User(user_data) if user_data else None
    
    @staticmethod
    def get_by_username(username):
        return db.users.find_one({'username': username})
    
    @staticmethod
    def create_user(username, password, email, role='user'):
        if db.users.find_one({'username': username}):
            return None
        user = {
            'username': username,
            'password': generate_password_hash(password),
            'email': email,
            'role': role,
            'created_at': datetime.utcnow(),
            'active': True
        }
        result = db.users.insert_one(user)
        return result.inserted_id

class Task:
    @staticmethod
    def create_task(title, description, assigned_to, assigned_by, weekday, due_date=None):
        task = {
            'title': title,
            'description': description,
            'assigned_to': assigned_to,
            'assigned_by': assigned_by,
            'weekday': weekday,
            'status': 'pending',
            'comment': '',
            'photo_path': None,
            'created_at': datetime.utcnow(),
            'completed_at': None,
            'approved_at': None,
            'approved_by': None,
            'archived': False,
            'due_date': due_date
        }
        result = db.tasks.insert_one(task)
        return result.inserted_id
    
    @staticmethod
    def get_user_tasks(user_id, weekday=None, include_archived=False):
        query = {'assigned_to': user_id}
        if weekday:
            query['weekday'] = weekday
        if not include_archived:
            query['archived'] = False
        return list(db.tasks.find(query).sort('created_at', -1))
    
    @staticmethod
    def get_user_archived_tasks(user_id):
        return list(db.tasks.find({'assigned_to': user_id, 'archived': True}).sort('approved_at', -1))
    
    @staticmethod
    def get_all_tasks(include_archived=False):
        query = {}
        if not include_archived:
            query['archived'] = False
        return list(db.tasks.find(query).sort('created_at', -1))
    
    @staticmethod
    def get_archived_tasks():
        return list(db.tasks.find({'archived': True}).sort('approved_at', -1))
    
    @staticmethod
    def get_task(task_id):
        return db.tasks.find_one({'_id': ObjectId(task_id)})
    
    @staticmethod
    def update_task(task_id, updates):
        db.tasks.update_one({'_id': ObjectId(task_id)}, {'$set': updates})
    
    @staticmethod
    def approve_task(task_id, admin_id):
        db.tasks.update_one(
            {'_id': ObjectId(task_id)},
            {'$set': {
                'archived': True,
                'approved_at': datetime.utcnow(),
                'approved_by': admin_id
            }}
        )
    
    @staticmethod
    def delete_task(task_id):
        db.tasks.delete_one({'_id': ObjectId(task_id)})