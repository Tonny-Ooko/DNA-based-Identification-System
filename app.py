from flask import Flask, render_template, request, redirect, url_for, jsonify, session, g
from flask_mysqldb import MySQL
from werkzeug.utils import secure_filename
from flask_apscheduler import APScheduler
import os
import uuid
import datetime
import json
import random
import hashlib

app = Flask(__name__)
# Configure MySQL
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'dna_registration'
#app.config['MYSQL_TIMEOUT'] = 300  # Set connection timeout (in seconds)
# MySQL Configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'dna_identification'
#app.config['MYSQL_TIMEOUT'] = 300  # Set connection timeout (in seconds)


mysql = MySQL(app)
scheduler = APScheduler()
mysql = MySQL(app)

@app.route('/')
def home():
    return render_template('home.html')


# File upload configuration
UPLOAD_FOLDER = 'uploads/'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Home route
#@app.route('/')
#def index():
    #return render_template('index.html')

# Registration route
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Fetch form data
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        family_name = request.form['family_name']
        date_of_birth = request.form['date_of_birth']
        age = request.form['age']
        email = request.form['email']
        phone_number = request.form['phone_number']
        address = request.form['address']
        birth_certificate_number = request.form['birth_certificate_number']
        driving_license_number = request.form.get('driving_license_number', None)
        national_id = request.form.get('national_id', None)
        social_security_number = request.form.get('social_security_number', None)
        marriage_status = request.form['marriage_status']

        # Handle file uploads
        fingerprint_file = request.files['fingerprint_file']
        genetic_marker_file = request.files['genetic_marker_file']

        fingerprint_path = None
        genetic_marker_path = None

        if fingerprint_file:
            fingerprint_filename = secure_filename(fingerprint_file.filename)
            fingerprint_path = os.path.join(app.config['UPLOAD_FOLDER'], fingerprint_filename)
            fingerprint_file.save(fingerprint_path)

        if genetic_marker_file:
            genetic_marker_filename = secure_filename(genetic_marker_file.filename)
            genetic_marker_path = os.path.join(app.config['UPLOAD_FOLDER'], genetic_marker_filename)
            genetic_marker_file.save(genetic_marker_path)

        # Generate unique DNA ID
        immutable_dna_id = str(uuid.uuid4())

        # Insert user data into the database
        cursor = mysql.connection.cursor()
        cursor.execute("""
            INSERT INTO users (first_name, last_name, family_name, date_of_birth, age, email, phone_number, address,
                               birth_certificate_number, driving_license_number, national_id, social_security_number,
                               immutable_dna_id, fingerprint_file)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (first_name, last_name, family_name, date_of_birth, age, email, phone_number, address,
              birth_certificate_number, driving_license_number, national_id, social_security_number,
              immutable_dna_id, fingerprint_path))

        user_id = cursor.lastrowid

        # Insert genetic markers into the database
        if genetic_marker_path:
            with open(genetic_marker_path, 'r') as f:
                marker_data = f.read()
            cursor.execute("""
                INSERT INTO genetic_markers (user_id, marker_data) VALUES (%s, %s)
            """, (user_id, marker_data))

        mysql.connection.commit()
        cursor.close()

        return redirect(url_for('home'))
    return render_template('register.html')

# AI function to compare genetic markers and determine relationships
def match_relationships():
    cursor = mysql.connection.cursor()

    # Retrieve all users and their genetic markers
    cursor.execute("SELECT users.id, users.first_name, users.last_name, genetic_markers.marker_data FROM users JOIN genetic_markers ON users.id = genetic_markers.user_id")
    users = cursor.fetchall()

    # Simulate genetic similarity calculations (AI placeholder logic)
    relationships = []
    for i in range(len(users)):
        for j in range(i + 1, len(users)):
            user1 = users[i]
            user2 = users[j]

            # Mock similarity percentage (replace with actual AI comparison logic)
            similarity = random.randint(10, 100)

            # Determine relationship type based on similarity (basic example)
            if similarity > 90:
                relationship_type = 'parent' if random.choice([True, False]) else 'child'
            elif similarity > 75:
                relationship_type = 'sibling'
            elif similarity > 50:
                relationship_type = 'cousin'
            else:
                relationship_type = None

            if relationship_type:
                relationships.append((user1[0], user2[0], relationship_type))

    # Update family_relationships table
    for rel in relationships:
        cursor.execute("""
            INSERT INTO family_relationships (user_id, related_user_id, relationship_type)
            VALUES (%s, %s, %s) ON DUPLICATE KEY UPDATE relationship_type = VALUES(relationship_type)
        """, rel)

    mysql.connection.commit()
    cursor.close()

@app.route('/search_family', methods=['GET', 'POST'])
def search_family():
    if request.method == 'POST':
        user_id = request.form['user_id']

        # Fetch relationships from the database
        cursor = mysql.connection.cursor()
        cursor.execute("""
            SELECT u.first_name, u.last_name, fr.relationship_type
            FROM family_relationships fr
            JOIN users u ON fr.related_user_id = u.id
            WHERE fr.user_id = %s
        """, (user_id,))
        relationships = cursor.fetchall()

        # Format results
        formatted_relationships = [{'name': f"{row[0]} {row[1]}", 'relationship_type': row[2]} for row in relationships]

        cursor.close()
        return render_template('family_search.html', relationships=formatted_relationships)

    return render_template('family_search.html', relationships=None)

@scheduler.task('interval', id='run_family_matching', seconds=3600)  # Runs every hour
def scheduled_family_matching():
    match_relationships()

# Route for Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        dna_hash = hashlib.sha256(request.form['dna'].encode()).hexdigest()
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE dna_hash=%s", (dna_hash,))
        user = cur.fetchone()
        cur.close()
        if user:
            session['loggedin'] = True
            session['id'] = user[0]
            return redirect(url_for('dashboard'))
        else:
            return 'Access Denied!'
    return render_template('login.html')

# Before request function to establish a connection
@app.before_request
def before_request():
    g.mysql_db = mysql.connect

@app.route('/dashboard')
def dashboard():
    try:
        # Create a cursor and execute queries within a try block
        cur = mysql.connection.cursor()

        # Fetching devices data
        cur.execute("SELECT * FROM devices")
        devices = cur.fetchall()

        # Fetching activity logs
        cur.execute("SELECT * FROM activity_logs")
        logs = cur.fetchall()

        # Closing the cursor after use
        cur.close()

        # Return the template with the fetched data
        return render_template('dashboard.html', devices=devices, logs=logs)

    except Exception as e:
        # Handle any exception, log it and show a generic error
        print(f"Error occurred: {e}")
        return "An error occurred while fetching data from the database."

    finally:
        # Ensure the connection is properly closed
        if mysql.connection.open:
            mysql.connection.close()

    # if 'loggedin' in session:
    #     # Handle case for logged in user
    #     pass
    # else:
    #     return redirect(url_for('login'))


# Ensuring proper handling of the database connection on shutdown
@app.teardown_appcontext
def close_db(error=None):
    if hasattr(g, 'mysql_db'):
        g.mysql_db.close()

# Route for Logs
@app.route('/logs')
def logs():
    if 'loggedin' in session:
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM activity_logs ORDER BY timestamp DESC")
        logs = cur.fetchall()
        cur.close()
        return render_template('logs.html', logs=logs)
    return redirect(url_for('login'))

# Route for Settings
@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if 'loggedin' in session:
        cur = mysql.connection.cursor()
        if request.method == 'POST':
            action = request.form['action']
            device_id = request.form['device_id']
            if action == 'grant':
                cur.execute("UPDATE devices SET status='active' WHERE id=%s", (device_id,))
            elif action == 'revoke':
                cur.execute("UPDATE devices SET status='inactive' WHERE id=%s", (device_id,))
            mysql.connection.commit()
        cur.execute("SELECT * FROM devices")
        devices = cur.fetchall()
        cur.close()
        return render_template('settings.html', devices=devices)
    return redirect(url_for('login'))

# Route for Analytics
@app.route('/analytics')
def analytics():
    if 'loggedin' in session:
        return render_template('analytics.html')
    return redirect(url_for('login'))

# Logout
@app.route('/logout')
def logout():
    session.pop('loggedin', None)
    session.pop('id', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    scheduler.init_app(app)
    scheduler.start()
    app.run(debug=True)