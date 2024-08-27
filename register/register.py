from flask import Flask, request, jsonify
from werkzeug.security import generate_password_hash
from flask_cors import CORS
from flask_mail import Mail, Message
import MySQLdb
from py_eureka_client.eureka_client import EurekaClient
import asyncio
import os

app = Flask(__name__)
CORS(app)

# MySQL configurations
dcfg = {
    "mysql": {
        "host": "127.0.0.1",
        "user": "root",
        "password": "D@qwertyuiop",
        "db": "ielts_database",
        "port": 3306
    }
}

# Email configurations
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USERNAME'] = 'datasparkaisolutions@gmail.com'  # Update with your email
app.config['MAIL_PASSWORD'] = 'mrgnqanvdwzlkcae'  # Update with your email password or app password
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False

mail = Mail(app)

# Eureka client configurations
eureka_client = EurekaClient(
    app_name="register-service",
    eureka_server="http://localhost:8761/eureka",  # Replace with your Eureka server URL
    instance_port=5002,  # Update as needed
    instance_ip="127.0.0.1",  # Replace with your actual instance IP if necessary
    instance_host="register-service"  # The name you want to register this instance under
)

def mysqlconnect():
    try:
        db_connection = MySQLdb.connect(
            host=dcfg["mysql"]["host"],
            user=dcfg["mysql"]["user"],
            passwd=dcfg["mysql"]["password"],
            db=dcfg["mysql"]["db"],
            port=dcfg["mysql"]["port"]
        )
        return db_connection
    except MySQLdb.Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None

@app.route('/db-check', methods=['GET'])
def db_check():
    db_connection = mysqlconnect()
    if db_connection is None:
        return jsonify({"message": "Database connection failed"}), 500
    
    try:
        cursor = db_connection.cursor()
        cursor.execute("SELECT 1")
        cursor.close()
        return jsonify({"message": "Database connection successful"}), 200
    except MySQLdb.Error as e:
        return jsonify({"message": "Database query failed", "error": str(e)}), 500
    finally:
        db_connection.close()

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    email = data.get('email')
    username = data.get('username')
    password = data.get('password')
    phone_number = data.get('phone_number')

    if not email or not username or not password or not phone_number:
        return jsonify({"message": "Missing email, username, password, or phone number"}), 400

    hashed_password = generate_password_hash(password)

    db_connection = mysqlconnect()
    if db_connection is None:
        return jsonify({"message": "Database connection failed"}), 500

    try:
        cursor = db_connection.cursor()

        # Check if the email or username already exists
        cursor.execute("SELECT * FROM users WHERE email = %s OR username = %s", (email, username))
        user = cursor.fetchone()

        if user:
            cursor.close()
            return jsonify({"message": "Email or username already exists"}), 400

        # Insert new user
        cursor.execute("INSERT INTO users (email, username, password, phone_number) VALUES (%s, %s, %s, %s)",
                       (email, username, hashed_password, phone_number))
        db_connection.commit()
        cursor.close()

        # Send confirmation email
        msg = Message('Registration Successful',
                      sender='datasparkaisolutions@gmail.com',
                      recipients=[email])
        msg.body = f'Hello {username},\n\nYour registration was successful!\n\nThank you for registering.'
        mail.send(msg)

        # Include the port number in the response to identify the instance
        return jsonify({"message": "User registered successfully", "instance": os.getenv('INSTANCE_PORT', '5002')}), 201
    except MySQLdb.Error as e:
        return jsonify({"message": "User registration failed", "error": str(e)}), 500
    finally:
        db_connection.close()

async def start_eureka_client():
    await eureka_client.start()

if __name__ == '__main__':
    asyncio.run(start_eureka_client())  # Register with Eureka
    app.run(host='0.0.0.0', port=int(os.getenv('INSTANCE_PORT', '5002')), debug=True)  # Bind to all interfaces
