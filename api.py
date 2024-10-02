from flask import current_app, jsonify, request
from flask_restful import Resource, reqparse, Api
from flask_security import hash_password, verify_password
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from datetime import datetime, timedelta
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import SQLAlchemyError
import traceback
from models import db, User, Role, Section, Ebook, Request, Feedback

api = Api()

def get_cache():
    return current_app.extensions['cache']

def get_security():
    return current_app.extensions['security']

def get_datastore():
    return get_security()._datastore


user_req_args = reqparse.RequestParser()
user_req_args.add_argument('email', required=True, help="Email required")
user_req_args.add_argument('username', required=False, help="Username required")
user_req_args.add_argument('password', required=True, help="Password required")

register_args = reqparse.RequestParser()
register_args.add_argument('email', required=True, help="Email required")
register_args.add_argument('password', required=True, help="Password required")
register_args.add_argument('username', required=True, help="Username required")

section_post_args = reqparse.RequestParser()
section_post_args.add_argument('section_name', required=True, help="Section name required")
section_post_args.add_argument('section_description')

ebook_post_args = reqparse.RequestParser()
ebook_post_args.add_argument('title', required=True, help="Title required")
ebook_post_args.add_argument('content', required=True, help="Content required")
ebook_post_args.add_argument('author', required=True, help="Author required")
ebook_post_args.add_argument('section_id', type=int, required=True, help="Section ID required")

request_post_args = reqparse.RequestParser()
request_post_args.add_argument('ebook_id', type=int, required=True, help="Ebook ID required")

request_put_args = reqparse.RequestParser()
request_put_args.add_argument('status', type=str, required=True, help="Status required")

feedback_post_args = reqparse.RequestParser()
feedback_post_args.add_argument('ebook_id', type=int, required=True, help="Ebook ID required")
feedback_post_args.add_argument('rating', type=int, required=True, help="Rating required")
feedback_post_args.add_argument('comment', type=str)

print("api.py is being imported")

class LoginAPI(Resource):
    def post(self):
        args = user_req_args.parse_args()
        email = args.get("email")
        password = args.get("password")
        username = args.get("username")

        user = User.query.filter_by(email=email).first()

        if user and verify_password(password, user.password):
            is_librarian = 'librarian' in [role.name for role in user.roles]
            
            if is_librarian or (username and user.username == username):
                access_token = create_access_token(identity=user.user_id)
                return {
                    'message': 'Logged in successfully',
                    'role': 'librarian' if is_librarian else 'user',
                    'user_id': user.user_id,
                    'access_token': access_token
                }
            elif not username:
                return {'message': 'Username is required for regular users'}, 400
        
        return {'message': 'Invalid credentials'}, 401

class RegisterAPI(Resource):
    def post(self):
        args = register_args.parse_args()
        email = args.get("email")
        password = args.get("password")
        username = args.get("username")

        if User.query.filter_by(email=email).first():
            return {'message': 'Email already registered'}, 400

        if User.query.filter_by(username=username).first():
            return {'message': 'Username already taken'}, 400

        new_user = get_datastore().create_user(
            email=email,
            password=hash_password(password),
            username=username
        )
        db.session.commit()

        return {
            'message': 'User registered successfully',
            'user_id': new_user.user_id,
            'email': new_user.email,
            'username': new_user.username
        }, 201

class UserAPI(Resource):
    @jwt_required()
    def get(self):
        users = User.query.all()
        return jsonify([{
            'id': user.user_id,
            'email': user.email,
            'username': user.username,
            'role': 'librarian' if 'librarian' in [role.name for role in user.roles] else 'user'
        } for user in users])
    
class UserProfileAPI(Resource):
    @jwt_required()
    def get(self):
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        if user:
            return jsonify({
                'username': user.username,
                'email': user.email,
            })
        return jsonify({'error': 'User not found'}), 404
    
    @jwt_required()
    def put(self):
        try:
            user_id = get_jwt_identity()
            user = User.query.get(user_id)
            if not user:
                return jsonify({'error': 'User not found'}), 404

            data = request.get_json()
            username = data.get('username')
            email = data.get('email')
            password = data.get('password')

            if username:
                existing_user = User.query.filter(User.username == username, User.user_id != user_id).first()
                if existing_user:
                    return jsonify({'error': 'Username already taken'}), 400
                user.username = username
            if email:
                existing_user = User.query.filter(User.email == email, User.user_id != user_id).first()
                if existing_user:
                    return jsonify({'error': 'Email already in use'}), 400
                user.email = email
            if password:
                user.password = hash_password(password)

            db.session.commit()
            current_app.logger.info(f"Profile updated successfully for user {user_id}")
            return jsonify({'message': 'Profile updated successfully'}), 200
        except SQLAlchemyError as e:
            db.session.rollback()
            current_app.logger.error(f"SQLAlchemy error: {str(e)}")
            current_app.logger.error(traceback.format_exc())
            return jsonify({'error': 'Database error occurred'}), 500
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Unexpected error: {str(e)}")
            current_app.logger.error(traceback.format_exc())
            return jsonify({'error': 'An unexpected error occurred'}), 500

class UserStatsAPI(Resource):
    @jwt_required()
    def get(self):
        user_id = get_jwt_identity()
        user = User.query.get_or_404(user_id)
        
        books_requested = Request.query.filter_by(user_id=user_id).count()
        requests_granted = Request.query.filter_by(user_id=user_id, status='granted').count()
        requests_revoked = Request.query.filter_by(user_id=user_id, status='revoked').count()
        books_returned = Request.query.filter_by(user_id=user_id, status='returned').count()  # New line
        feedbacks_given = Feedback.query.filter_by(user_id=user_id).count()
        
        return {
            'books_requested': books_requested,
            'requests_granted': requests_granted,
            'requests_revoked': requests_revoked,
            'books_returned': books_returned,  # New line
            'feedbacks_given': feedbacks_given
        }

class SectionAPI(Resource):
    def get(self):
        sections = Section.query.all()
        return jsonify([{
            'id': section.section_id,
            'section_name': section.section_name,
            'section_description': section.section_description,
            'date_created': section.date_created
        } for section in sections])
    
    @jwt_required()    
    def post(self):
        args = section_post_args.parse_args()
        new_section = Section(section_name=args.get("section_name"), section_description=args.get("section_description"))
        db.session.add(new_section)
        db.session.commit()
        return jsonify({'message': 'Section created successfully', 'section_id': new_section.section_id})
    
    @jwt_required()    
    def put(self, section_id):
        section = Section.query.get_or_404(section_id)
        args = section_post_args.parse_args()
        section.section_name = args.get("section_name")
        section.section_description = args.get("section_description")
        db.session.commit()
        return jsonify({'message': 'Section has been updated'})

    @jwt_required()    
    def delete(self, section_id):
        section = Section.query.options(joinedload(Section.ebooks)).get_or_404(section_id)
        for ebook in section.ebooks:
            Feedback.query.filter_by(ebook_id=ebook.ebook_id).delete()
            Request.query.filter_by(ebook_id=ebook.ebook_id).delete()
            db.session.delete(ebook)
        db.session.delete(section)
        db.session.commit()
        return jsonify({'message': 'Section and all its books have been deleted'})
            
class EbookAPI(Resource):
    def get(self):
        ebooks = Ebook.query.join(Section).all()
        return jsonify([{
            'id': ebook.ebook_id,
            'ebook_name': ebook.ebook_name,
            'content': ebook.content,
            'author': ebook.author,
            'section_id': ebook.section_id,
            'section_name': ebook.section.section_name,
            'date_issued': ebook.date_issued.isoformat() if ebook.date_issued else None,
            'date_returned': ebook.date_returned.isoformat() if ebook.date_returned else None
        } for ebook in ebooks])

    @jwt_required()    
    def post(self):
        args = ebook_post_args.parse_args()
        new_ebook = Ebook(
            ebook_name=args.get("title"),
            content=args.get("content"),
            author=args.get("author"),
            section_id=args.get("section_id")
        )
        db.session.add(new_ebook)
        db.session.commit()
        return jsonify({'message': 'Ebook created successfully', 'id': new_ebook.ebook_id})
    
    @jwt_required()    
    def put(self, ebook_id):
        ebook = Ebook.query.get_or_404(ebook_id)
        args = ebook_post_args.parse_args()
        ebook.ebook_name = args.get("title")
        ebook.content = args.get("content")
        ebook.author = args.get("author")
        ebook.section_id = args.get("section_id")
        db.session.commit()
        return jsonify({'message': 'Ebook has been updated'})
        
    @jwt_required()    
    def delete(self, ebook_id):
        ebook = Ebook.query.get_or_404(ebook_id)
        Feedback.query.filter_by(ebook_id=ebook_id).delete()
        Request.query.filter_by(ebook_id=ebook_id).delete()        
        db.session.delete(ebook)
        db.session.commit()
        return jsonify({'message': 'Ebook along with its feedback and requests (if any) has been deleted'})
    
class RequestAPI(Resource):
    @jwt_required()
    def get(self):
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        if 'librarian' in [role.name for role in user.roles]:
            requests = Request.query.all()
        else:
            requests = Request.query.filter_by(user_id=user_id).all()
        
        result = [{
            'request_id': req.request_id,
            'ebook_id': req.ebook_id,
            'username': req.user.username,
            'ebook_name': req.ebook.ebook_name,
            'status': req.status,
            'date_requested': req.date_requested.isoformat(),
            'date_granted': req.date_granted.isoformat() if req.date_granted else None,
            'date_revoked': req.date_revoked.isoformat() if req.date_revoked else None,
            'return_date': req.return_date.isoformat() if req.return_date else None
        } for req in requests]
        
        print('Requests:', result)
        return jsonify(result)


    @jwt_required()    
    def post(self):
        args = request_post_args.parse_args()
        user_id = get_jwt_identity()
        ebook_id = args.get("ebook_id")
        
        active_requests = Request.query.filter_by(user_id=user_id, status='granted').count()
        if active_requests >= 5:
            return jsonify({'message': 'You have reached the maximum limit of 5 active e-book requests'}), 400
        
        existing_request = Request.query.filter_by(user_id=user_id, ebook_id=ebook_id, status='requested').first()
        if existing_request:
            return jsonify({'message': 'You have already requested this e-book'}), 400

        new_request = Request(user_id=user_id, ebook_id=ebook_id, status='requested', date_requested=datetime.utcnow())
        db.session.add(new_request)
        db.session.commit()
        return jsonify({'message': 'Request submitted successfully', 'request_id': new_request.request_id})

    @jwt_required()    
    def put(self, request_id):
        req = Request.query.get_or_404(request_id)
        args = request_put_args.parse_args()
        status = args.get("status")
        
        user = User.query.get(req.user_id)
        if status == 'granted':
            if user.no_of_books >= 5:
                return jsonify({'message': 'User has already borrowed the maximum number of books'}), 400
            
            req.status = 'granted'
            req.date_granted = datetime.now()
            req.return_date = datetime.now() + timedelta(days=7)
            user.no_of_books = Request.query.filter_by(user_id=user.user_id, status='granted').count() + 1
        elif status == 'revoked':
            if req.status == 'granted':
                user.no_of_books = max(0, user.no_of_books - 1)
            req.status = 'revoked'
            req.date_revoked = datetime.now()
        
        db.session.commit()
        return jsonify({'message': f'Request status updated to {status}'})
    
class ReturnAPI(Resource):
    @jwt_required()
    def post(self, request_id):
        user_id = get_jwt_identity()
        req = Request.query.get_or_404(request_id)
        
        if req.user_id == user_id and req.status == 'granted':
            req.status = 'returned'
            req.date_revoked = datetime.now()
            user = User.query.get(req.user_id)
            user.no_of_books = max(0, Request.query.filter_by(user_id=user.user_id, status='granted').count() - 1)
            db.session.commit()
            return jsonify({'message': 'E-book returned successfully'})
        else:
            return jsonify({'message': 'Invalid return request'}), 400
        
class AutoReturnAPI(Resource):
    def post(self):
        current_date = datetime.utcnow()
        overdue_requests = Request.query.filter(
            Request.status == 'granted',
            Request.date_granted <= current_date - timedelta(days=7)
        ).all()

        returned_books = []
        for request in overdue_requests:
            request.status = 'returned'
            request.date_revoked = current_date
            user = User.query.get(request.user_id)
            user.no_of_books = max(0, user.no_of_books - 1)
            returned_books.append({
                'request_id': request.request_id,
                'ebook_name': request.ebook.ebook_name,
                'user': request.user.username
            })

        db.session.commit()

        return jsonify({
            'message': f'{len(returned_books)} overdue books returned automatically',
            'returned_books': returned_books
        })

class FeedbackAPI(Resource):
    @jwt_required()
    def get(self):
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        if 'librarian' in [role.name for role in user.roles]:
            feedbacks = Feedback.query.all()
        else:
            feedbacks = Feedback.query.filter_by(user_id=user_id).all()
        
        return jsonify([{
            'feedback_id': feedback.feedback_id,
            'user_id': feedback.user_id,
            'username': feedback.user.username,
            'ebook_id': feedback.ebook_id,
            'ebook_name': feedback.ebook.ebook_name,
            'rating': feedback.rating,
            'comment': feedback.comment,
            'date_created': feedback.date_created.isoformat()
        } for feedback in feedbacks])

    @jwt_required()
    def post(self):
        user_id = get_jwt_identity()
        args = feedback_post_args.parse_args()
        ebook_id = args.get("ebook_id")
        
        # Check if the user has been granted access to this book
        granted_request = Request.query.filter_by(
            user_id=user_id,
            ebook_id=ebook_id,
            status='granted'
        ).first()
        
        if not granted_request:
            return jsonify({'message': 'You can only provide feedback for books you have been granted access to'}), 403
        
        # Check if the user has already given feedback for this book
        existing_feedback = Feedback.query.filter_by(
            user_id=user_id,
            ebook_id=ebook_id
        ).first()
        
        if existing_feedback:
            return jsonify({'message': 'You have already provided feedback for this book'}), 400
        
        new_feedback = Feedback(
            user_id=user_id,
            ebook_id=ebook_id,
            rating=args.get("rating"),
            comment=args.get("comment"),
            date_created=datetime.utcnow()
        )
        db.session.add(new_feedback)
        db.session.commit()
        return jsonify({'message': 'Feedback submitted successfully', 'feedback_id': new_feedback.feedback_id})

    @jwt_required()    
    def delete(self, feedback_id):
        feedback = Feedback.query.get_or_404(feedback_id)
        db.session.delete(feedback)
        db.session.commit()
        return jsonify({'message': 'Feedback has been deleted'})

class LibrarianDashboardAPI(Resource):
    @jwt_required()
    def get(self):
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        if not user or not user.has_role('librarian'):
            return {'message': 'Insufficient permissions'}, 403
            
        active_users = User.query.join(Request).filter(Request.status == 'granted').distinct().count()
        pending_requests = Request.query.filter_by(status='requested').count()
        granted_requests = Request.query.filter_by(status='granted').count()
        revoked_requests = Request.query.filter_by(status='revoked').count()
        total_returns = Request.query.filter_by(status='returned').count()  
        total_feedbacks = Feedback.query.count()
            
        return jsonify({
            'active_users': active_users,
            'pending_requests': pending_requests,
            'granted_requests': granted_requests,
            'revoked_requests': revoked_requests,
            'total_returns': total_returns,
            'total_feedbacks': total_feedbacks
            })
    
api.add_resource(LoginAPI, '/api/login')
api.add_resource(RegisterAPI, '/api/register')
api.add_resource(UserAPI, '/api/users')
api.add_resource(UserProfileAPI, '/api/user/profile')
api.add_resource(UserStatsAPI, '/api/user/stats')
api.add_resource(SectionAPI, '/api/section', '/api/section/<int:section_id>')
api.add_resource(EbookAPI, '/api/ebook', '/api/ebook/<int:ebook_id>')
api.add_resource(RequestAPI, '/api/request', '/api/request/<int:request_id>')
api.add_resource(ReturnAPI, '/api/return/<int:request_id>')
api.add_resource(AutoReturnAPI, '/api/auto-return')
api.add_resource(FeedbackAPI, '/api/feedback', '/api/feedback/<int:feedback_id>')
api.add_resource(LibrarianDashboardAPI, '/api/librarian/dashboard')