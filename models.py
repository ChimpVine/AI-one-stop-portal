from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db, login


@login.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    full_name = db.Column(db.String(120))  # New field for full name
    is_admin = db.Column(db.Boolean, default=False)
    departments = db.relationship(
        'Department', secondary='user_department', back_populates='users')

    def __init__(self, email, full_name,  is_admin=False):  # Updated __init__ method
        self.email = email
        self.full_name = full_name
        self.is_admin = is_admin  # Assign the is_admin value

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Department(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)
    users = db.relationship(
        'User', secondary='user_department', back_populates='departments')


user_department = db.Table('user_department',
                           db.Column('user_id', db.Integer, db.ForeignKey(
                               'user.id'), primary_key=True),
                           db.Column('department_id', db.Integer, db.ForeignKey(
                               'department.id'), primary_key=True)
                           )
