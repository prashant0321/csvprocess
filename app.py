from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
import csv
import io
import uuid
import os
import requests
from PIL import Image
from io import BytesIO
import threading

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///products.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['OUTPUT_DIR'] = 'output'

db = SQLAlchemy(app)

# Create output directory
os.makedirs(app.config['OUTPUT_DIR'], exist_ok=True)

# Database Models
class ProcessingRequest(db.Model):
    id = db.Column(db.String(36), primary_key=True)
    status = db.Column(db.String(20), default='pending')
    product = db.relationship('Product', backref='request', lazy=True)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    serial_number = db.Column(db.Integer)
    product_name = db.Column(db.String(100))
    input_urls = db.Column(db.JSON)
    output_urls = db.Column(db.JSON)
    request_id = db.Column(db.String(36), db.ForeignKey('processing_request.id'))

# Helper Functions
def compress_image(url):
    try:
        response = requests.get(url)
        img = Image.open(BytesIO(response.content))
        img = img.convert('RGB')
        
        # Compress and save
        output = BytesIO()
        img.save(output, format='JPEG', quality=50)
        filename = f"compressed_{uuid.uuid4().hex}.jpg"
        output_path = os.path.join(app.config['OUTPUT_DIR'], filename)
        
        with open(output_path, 'wb') as f:
            f.write(output.getvalue())
            
        return f"http://localhost:5000/output/{filename}"
    except Exception as e:
        return f"error: {str(e)}"

def process_csv(request_id, csv_data):
    with app.app_context():
        req = ProcessingRequest.query.get(request_id)
        req.status = 'processing'
        db.session.commit()
        
        try:
            reader = csv.DictReader(io.StringIO(csv_data))
            for row in reader:
                input_urls = [url.strip() for url in row['Input Image Urls'].split(',')]
                output_urls = [compress_image(url) for url in input_urls]
                
                product = Product(
                    serial_number=row['Serial Number'],
                    product_name=row['Product Name'],
                    input_urls=input_urls,
                    output_urls=output_urls,
                    request_id=request_id
                )
                db.session.add(product)
            
            req.status = 'completed'
        except Exception as e:
            req.status = 'failed'
        
        db.session.commit()

# Routes
@app.route('/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        return {'error': 'No file uploaded'}, 400
    
    file = request.files['file'].stream.read().decode('utf-8')
    request_id = str(uuid.uuid4())
    
    # Create new request
    new_request = ProcessingRequest(id=request_id)
    db.session.add(new_request)
    db.session.commit()
    
    # Start processing in background thread
    thread = threading.Thread(target=process_csv, args=(request_id, file))
    thread.start()
    
    return {'request_id': request_id}, 202

@app.route('/status/<request_id>', methods=['GET'])
def status(request_id):
    req = ProcessingRequest.query.get(request_id)
    if not req:
        return {'error': 'Invalid request ID'}, 404
    
    return {
        'request_id': req.id,
        'status': req.status
    }

@app.route('/output/<filename>')
def serve_image(filename):
    return send_from_directory(app.config['OUTPUT_DIR'], filename)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5000, debug=True)