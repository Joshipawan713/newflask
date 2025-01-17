import os
from flask import Flask, render_template, request, redirect, url_for, current_app, session, flash # type: ignore
import mysql.connector # type: ignore
from mysql.connector import Error # type: ignore
from werkzeug.security import generate_password_hash, check_password_hash # type: ignore
import secrets

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

def get_db_connection():
    try:
        conn = mysql.connector.connect(
            host='localhost',
            user='localhost',
            password='Sdk@1259',
            database='flask_proj'
        )
        if conn.is_connected():
            print("Connected Successfully")
        return conn
    except mysql.connector.Error as err:
        print(f"Error: {err}")
        return None

@app.route('/')
def index():
    conn = get_db_connection()
    if not conn:
        return "Database connection failed.", 500

    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM books ORDER BY RAND() LIMIT 6')
    data = cursor.fetchall()
    
    covers_folder = os.path.join(current_app.static_folder, 'coverimage')
    
    for book in data:
        image_filename = book.get('coverpage')
        image_path = os.path.join(covers_folder, image_filename)
        
        if not os.path.exists(image_path):
            book['coverpage'] = 'imagesnotfound.jpg'
    
    cursor.close()
    conn.close()

    return render_template('index.html', data=data)

@app.route('/register', methods=['GET', 'POST'])
def register():
    
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        mobile = request.form['mobile']
        account_type = request.form['account_type']
        password = request.form['password']
        repeat_password = request.form['repeat_password']
        
        if password != repeat_password:
            flash('Passwords do not match!', 'danger')
            return redirect(url_for('register'))
        
        status = 'Active'
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM user WHERE email = %s", (email,))
        check_email = cursor.fetchone()
        if check_email:
            flash('Email already exists', 'danger')
            conn.close()
            return redirect(url_for('register'))
        
        cursor.execute(
            "INSERT INTO user (name, email, mobile, password, account_type, status) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (name, email, mobile, password, account_type, status)
        )
        
        conn.commit()
        conn.close()
        
        flash('Registration successful!', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login')
def login():
    return render_template('login.html')

if __name__ == '__main__':
    app.run(debug=True, port=5000)