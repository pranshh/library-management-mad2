from flask_sqlalchemy import SQLAlchemy
from flask_security import UserMixin, RoleMixin
import uuid
from datetime import datetime

db = SQLAlchemy()

class RolesUsers(db.Model):
    __tablename__ = 'roles_users'
    id = db.Column(db.Integer(), primary_key=True)
    user_id = db.Column('user_id', db.Integer(), db.ForeignKey('user.user_id'))
    role_id = db.Column('role_id', db.Integer(), db.ForeignKey('role.role_id'))  

class Role(db.Model, RoleMixin):
    __tablename__ = 'role'
    role_id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(80), unique=True)
    description = db.Column(db.String(255))

class User(db.Model, UserMixin):
    __tablename__ = 'user'
    user_id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True)
    username = db.Column(db.String(255), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    active = db.Column(db.Boolean())
    fs_uniquifier = db.Column(db.String(255), unique=True, nullable=False)
    no_of_books = db.Column(db.Integer, default=0)
    roles = db.relationship('Role', secondary='roles_users',
                            backref=db.backref('users', lazy='dynamic'))
    
    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)
        self.fs_uniquifier = str(uuid.uuid4())

    def get_id(self):
        return str(self.user_id)

class Section(db.Model):
    __tablename__ = 'section'
    section_id = db.Column(db.Integer, primary_key=True)
    section_name = db.Column(db.String(100), nullable=False)
    section_description = db.Column(db.String(500))
    date_created = db.Column(db.DateTime, default=datetime.utcnow)

class Ebook(db.Model):
    __tablename__ = 'ebook'
    ebook_id = db.Column(db.Integer, primary_key=True)
    ebook_name = db.Column(db.String(100), nullable=False)
    author = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    date_issued = db.Column(db.DateTime)
    date_returned = db.Column(db.DateTime)
    section_id = db.Column(db.Integer, db.ForeignKey('section.section_id'), nullable=False)
    section = db.relationship('Section', backref='ebooks')

class Request(db.Model):
    __tablename__ = 'request'
    request_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), nullable=False)
    ebook_id = db.Column(db.Integer, db.ForeignKey('ebook.ebook_id'), nullable=False)
    status = db.Column(db.String(20), nullable=False)
    date_requested = db.Column(db.DateTime, nullable=False)
    date_granted = db.Column(db.DateTime)
    date_revoked = db.Column(db.DateTime)
    return_date = db.Column(db.DateTime)
    user = db.relationship('User', backref=db.backref('requests', lazy='dynamic'))
    ebook = db.relationship('Ebook', backref=db.backref('requests', lazy='dynamic'))

class Feedback(db.Model):
    __tablename__ = 'feedback'
    feedback_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), nullable=False)
    ebook_id = db.Column(db.Integer, db.ForeignKey('ebook.ebook_id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text)
    date_created = db.Column(db.DateTime, nullable=False)
    user = db.relationship('User', backref=db.backref('feedbacks', lazy='dynamic'))
    ebook = db.relationship('Ebook', backref=db.backref('feedbacks', lazy='dynamic'))