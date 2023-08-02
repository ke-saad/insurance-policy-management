
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from flask_restx import Api, Resource, fields
from flask_pymongo import PyMongo
import pandas as pd

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mssql+pyodbc://SAAD\\SQLEXPRESS/policies_db?driver=ODBC+Driver+17+for+SQL+Server'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = '1234'

db = SQLAlchemy(app)
ma = Marshmallow(app)
api = Api(app)
mongo = PyMongo(app, uri='mongodb://localhost:27017/mydatabase')
policy_info_collection = mongo.db.policies_infos


# Define the model for the file upload
file_upload_model = api.model('FileUpload', {
    'file': fields.String(description='CSV or XLSX file to upload')
})

# Table


class Policy(db.Model):
    __tablename__ = 'Policy'
    policy_id = db.Column(db.Integer, primary_key=True,
                          nullable=False, autoincrement=True)
    policy_number = db.Column(db.String(50), nullable=False)
    policy_holder_name = db.Column(db.String(100), nullable=False)
    coverage_amount = db.Column(db.Float, nullable=False)
    premium_amount = db.Column(db.Float, nullable=False)

    def __init__(self, policy_number, policy_holder_name, coverage_amount, premium_amount):
        self.policy_number = policy_number
        self.policy_holder_name = policy_holder_name
        self.coverage_amount = coverage_amount
        self.premium_amount = premium_amount


class PolicySchema(ma.Schema):
    class Meta:
        fields = ('policy_id', 'policy_number', 'policy_holder_name',
                  'coverage_amount', 'premium_amount')


policy_schema = PolicySchema()
policies_schema = PolicySchema(many=True)


# MongoDB data
class PolicyInfo:
    def __init__(self, policy_id, claims_info, policy_documents):
        self.policy_id = policy_id
        self.claims_info = claims_info
        self.policy_documents = policy_documents


class PolicyInfoSchema(ma.Schema):
    class Meta:
        fields = ('policy_id', 'claims_info', 'policy_documents')


policy_info_schema = PolicyInfoSchema()
policy_infos_schema = PolicyInfoSchema(many=True)


# Routes
@api.route('/get/main infos')
class GetSQLPolicy(Resource):
    def get(self):
        policies_sql = Policy.query.all()
        ordered_policies_sql = [policy_schema.dump(
            policy) for policy in policies_sql]
        return {'SQL policies info list': ordered_policies_sql}


# @api.route('/get/secondary infos')
# class GetMongoDBPolicy(Resource):
#     def get(self):
#         policies_mongo = policy_info_collection.find()
#         ordered_policies_mongo = [policy_info_schema.dump(
#             policy) for policy in policies_mongo]
#         return {'MongoDB policies info list': ordered_policies_mongo}


@api.route('/get/exhaustive list')
class GetCombinedPolicy(Resource):
    def get(self):
        policies_sql = Policy.query.all()
        ordered_policies_sql = [policy_schema.dump(
            policy) for policy in policies_sql]
        policies_mongo = policy_info_collection.find()
        ordered_policies_mongo = [policy_info_schema.dump(
            policy) for policy in policies_mongo]
        combined_policies = []
        for policy_sql in ordered_policies_sql:
            policy_id = policy_sql['policy_id']
            policy_mongo = next(
                (policy for policy in ordered_policies_mongo if policy['policy_id'] == policy_id), None)
            if policy_mongo:
                combined_policy = {**policy_sql, **policy_mongo}
                combined_policies.append(combined_policy)
        return {'Combined policies info list': combined_policies}


@api.route('/post')
class PostPolicy(Resource):
    @api.expect(api.model('Policy', {
        'policy_number': fields.String(description='Enter Policy Number'),
        'policy_holder_name': fields.String(description='Enter Policy Holder Name'),
        'coverage_amount': fields.Float(description='Enter Coverage Amount'),
        'premium_amount': fields.Float(description='Enter Premium Amount'),
        'claims_info': fields.String(description='Enter Claims Info'),
        'policy_documents': fields.String(description='Enter Policy Documents'),
        'add_to_mongodb': fields.Boolean(description='Add to MongoDB'),
    }))
    def post(self):
        policy_number = request.json['policy_number']
        policy_holder_name = request.json['policy_holder_name']
        coverage_amount = request.json['coverage_amount']
        premium_amount = request.json['premium_amount']
        claims_info = request.json.get('claims_info', None)
        policy_documents = request.json.get('policy_documents', None)
        add_to_mongodb = request.json.get('add_to_mongodb', True)

        policy = Policy(
            policy_number=policy_number,
            policy_holder_name=policy_holder_name,
            coverage_amount=coverage_amount,
            premium_amount=premium_amount
        )

        db.session.add(policy)
        db.session.commit()

        if add_to_mongodb:
            policy_id = policy.policy_id  # Get the auto-generated policy ID
            policy_info = PolicyInfo(
                policy_id=policy_id,
                claims_info=claims_info,
                policy_documents=policy_documents
            )
            policy_info_collection.insert_one(
                policy_info_schema.dump(policy_info))

        return {'message': 'Policy added to database successfully'}


@api.route('/put/<int:policy_id>')
class PutPolicy(Resource):
    @api.expect(api.model('Policy', {
        'policy_number': fields.String(description='Enter Policy Number'),
        'policy_holder_name': fields.String(description='Enter Policy Holder Name'),
        'coverage_amount': fields.Float(description='Enter Coverage Amount'),
        'premium_amount': fields.Float(description='Enter Premium Amount'),
        'claims_info': fields.String(description='Enter Claims Info'),
        'policy_documents': fields.String(description='Enter Policy Documents')
    }))
    def put(self, policy_id):
        with app.app_context():
            policy = Policy.query.get(policy_id)
            if not policy:
                return {'message': 'Policy not found'}, 404

            policy.policy_number = request.json['policy_number']
            policy.policy_holder_name = request.json['policy_holder_name']
            policy.coverage_amount = request.json['coverage_amount']
            policy.premium_amount = request.json['premium_amount']

            db.session.commit()

            policy_info_collection.update_one(
                {'policy_id': policy_id},
                {'$set': {
                    'claims_info': request.json.get('claims_info', policy_info_collection.find_one({'policy_id': policy_id}).get('claims_info')),
                    'policy_documents': request.json.get('policy_documents', policy_info_collection.find_one({'policy_id': policy_id}).get('policy_documents'))
                }}
            )

            return {'message': 'Policy updated successfully'}


@api.route('/delete/<int:policy_id>')
class DeletePolicy(Resource):
    def delete(self, policy_id):
        with app.app_context():
            policy = Policy.query.get(policy_id)
            if not policy:
                return {'message': 'Policy not found'}, 404

            db.session.delete(policy)
            db.session.commit()

            policy_info_collection.delete_one({'policy_id': policy_id})

            return {'message': 'Policy deleted successfully'}


if __name__ == "__main__":
    app.run()


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mssql+pyodbc://SAAD\\SQLEXPRESS/policies_db?driver=ODBC+Driver+17+for+SQL+Server'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = '1234'

db = SQLAlchemy(app)
ma = Marshmallow(app)
api = Api(app)
mongo = PyMongo(app, uri='mongodb://localhost:27017/mydatabase')
policy_info_collection = mongo.db.policies_infos


# Table
class Policy(db.Model):
    __tablename__ = 'Policy'
    policy_id = db.Column(db.Integer, primary_key=True,
                          nullable=False, autoincrement=True)
    policy_number = db.Column(db.String(50), nullable=False)
    policy_holder_name = db.Column(db.String(100), nullable=False)
    coverage_amount = db.Column(db.Float, nullable=False)
    premium_amount = db.Column(db.Float, nullable=False)

    def __init__(self, policy_number, policy_holder_name, coverage_amount, premium_amount):
        self.policy_number = policy_number
        self.policy_holder_name = policy_holder_name
        self.coverage_amount = coverage_amount
        self.premium_amount = premium_amount


class PolicySchema(ma.Schema):
    class Meta:
        fields = ('policy_id', 'policy_number', 'policy_holder_name',
                  'coverage_amount', 'premium_amount')


policy_schema = PolicySchema()
policies_schema = PolicySchema(many=True)


# MongoDB data
class PolicyInfo:
    def __init__(self, policy_id, claims_info, policy_documents):
        self.policy_id = policy_id
        self.claims_info = claims_info
        self.policy_documents = policy_documents


class PolicyInfoSchema(ma.Schema):
    class Meta:
        fields = ('policy_id', 'claims_info', 'policy_documents')


policy_info_schema = PolicyInfoSchema()
policy_infos_schema = PolicyInfoSchema(many=True)


# Routes
@api.route('/get/main infos')
class GetSQLPolicy(Resource):
    def get(self):
        policies_sql = Policy.query.all()
        ordered_policies_sql = [policy_schema.dump(
            policy) for policy in policies_sql]
        return {'SQL policies info list': ordered_policies_sql}


@api.route('/get/secondary infos')
class GetMongoDBPolicy(Resource):
    def get(self):
        policies_mongo = policy_info_collection.find()
        ordered_policies_mongo = [policy_info_schema.dump(
            policy) for policy in policies_mongo]
        return {'MongoDB policies info list': ordered_policies_mongo}


@api.route('/get/exhaustive list')
class GetCombinedPolicy(Resource):
    def get(self):
        policies_sql = Policy.query.all()
        ordered_policies_sql = [policy_schema.dump(
            policy) for policy in policies_sql]
        policies_mongo = policy_info_collection.find()
        ordered_policies_mongo = [policy_info_schema.dump(
            policy) for policy in policies_mongo]
        combined_policies = []
        for policy_sql in ordered_policies_sql:
            policy_id = policy_sql['policy_id']
            policy_mongo = next(
                (policy for policy in ordered_policies_mongo if policy['policy_id'] == policy_id), None)
            if policy_mongo:
                combined_policy = {**policy_sql, **policy_mongo}
                combined_policies.append(combined_policy)
        return {'Combined policies info list': combined_policies}


@api.route('/post')
class PostPolicy(Resource):
    @api.expect(api.model('Policy', {
        'policy_number': fields.String(description='Enter Policy Number'),
        'policy_holder_name': fields.String(description='Enter Policy Holder Name'),
        'coverage_amount': fields.Float(description='Enter Coverage Amount'),
        'premium_amount': fields.Float(description='Enter Premium Amount'),
        'claims_info': fields.String(description='Enter Claims Info'),
        'policy_documents': fields.String(description='Enter Policy Documents'),
        'add_to_mongodb': fields.Boolean(description='Add to MongoDB'),
    }))
    def post(self):
        policy_number = request.json['policy_number']
        policy_holder_name = request.json['policy_holder_name']
        coverage_amount = request.json['coverage_amount']
        premium_amount = request.json['premium_amount']
        claims_info = request.json.get('claims_info', None)
        policy_documents = request.json.get('policy_documents', None)
        add_to_mongodb = request.json.get('add_to_mongodb', True)

        policy = Policy(
            policy_number=policy_number,
            policy_holder_name=policy_holder_name,
            coverage_amount=coverage_amount,
            premium_amount=premium_amount
        )

        db.session.add(policy)
        db.session.commit()

        if add_to_mongodb:
            policy_id = policy.policy_id  # Get the auto-generated policy ID
            policy_info = PolicyInfo(
                policy_id=policy_id,
                claims_info=claims_info,
                policy_documents=policy_documents
            )
            policy_info_collection.insert_one(
                policy_info_schema.dump(policy_info))

        return {'message': 'Policy added to database successfully'}


@api.route('/put/<int:policy_id>')
class PutPolicy(Resource):
    @api.expect(api.model('Policy', {
        'policy_number': fields.String(description='Enter Policy Number'),
        'policy_holder_name': fields.String(description='Enter Policy Holder Name'),
        'coverage_amount': fields.Float(description='Enter Coverage Amount'),
        'premium_amount': fields.Float(description='Enter Premium Amount'),
        'claims_info': fields.String(description='Enter Claims Info'),
        'policy_documents': fields.String(description='Enter Policy Documents')
    }))
    def put(self, policy_id):
        with app.app_context():
            policy = Policy.query.get(policy_id)
            if not policy:
                return {'message': 'Policy not found'}, 404

            policy.policy_number = request.json['policy_number']
            policy.policy_holder_name = request.json['policy_holder_name']
            policy.coverage_amount = request.json['coverage_amount']
            policy.premium_amount = request.json['premium_amount']

            db.session.commit()

            policy_info_collection.update_one(
                {'policy_id': policy_id},
                {'$set': {
                    'claims_info': request.json.get('claims_info', policy_info_collection.find_one({'policy_id': policy_id}).get('claims_info')),
                    'policy_documents': request.json.get('policy_documents', policy_info_collection.find_one({'policy_id': policy_id}).get('policy_documents'))
                }}
            )

            return {'message': 'Policy updated successfully'}


@api.route('/delete/<int:policy_id>')
class DeletePolicy(Resource):
    def delete(self, policy_id):
        with app.app_context():
            policy = Policy.query.get(policy_id)
            if not policy:
                return {'message': 'Policy not found'}, 404

            db.session.delete(policy)
            db.session.commit()

            policy_info_collection.delete_one({'policy_id': policy_id})

            return {'message': 'Policy deleted successfully'}




@api.route('/upload')
class FileUpload(Resource):
    @api.expect(file_upload_model, validate=True)
    def post(self):  # Rename method to 'post_file'
        try:
            # Check if the file is uploaded in the request
            if 'file' not in request.files:
                return {'error': 'No file uploaded'}, 400
            
            file = request.files['file']

            # Read the file into a pandas DataFrame based on file type
            if file.filename.endswith('.csv'):
                df = pd.read_csv(file)
            elif file.filename.endswith('.xlsx'):
                df = pd.read_excel(file, engine='openpyxl')
            else:
                return {'error': 'Invalid file format. Only CSV or XLSX files are supported'}, 400

            # Convert DataFrame to dictionary
            data_dict = df.to_dict(orient='records')

            return {'data': data_dict}, 200

        except Exception as e:
            return {'error': str(e)}, 500



if __name__ == "__main__":
    app.run()
