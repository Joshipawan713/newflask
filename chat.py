from flask import Flask, render_template
from flask_socketio import SocketIO, emit, send
import mysql.connector
from datetime import datetime

app = Flask(__name__)
socketio = SocketIO(app)

def get_db_connection():
    try:
        conn = mysql.connector.connect(
            host='localhost',
            user='root',
            password='',
            database='flask_python'
        )
        if conn.is_connected():
            pass
        return conn
    except mysql.connector.Error as err:
        print(f"Error: {err}")
        return None
    
def get_current_date_time():
    now = datetime.now()
    return now.strftime('%Y-%m-%d'), now.strftime('%I:%M:%S %p')

@app.route('/')
def chatApplication():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute('SELECT * FROM chat_app ORDER BY add_time DESC')
    messages = cursor.fetchall()
    cursor.close()
    connection.close()
    
    return render_template('chatapplication.html', messages=messages)

@socketio.on('send_message')
def handle_message(data):
    username = data['username']
    email = data['email']
    message = data['message']

    add_date, add_time = get_current_date_time()
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute('INSERT INTO chat_app (name, email, message, add_date, add_time) VALUES (%s, %s, %s, %s, %s)', (username, email, message, add_date, add_time))
    connection.commit()
    cursor.close()
    connection.close()

    # Emit the new message to all connected clients in real time
    emit('receive_message', {'username': username, 'message': message}, broadcast=True)

if __name__ == '__main__':
    app.run(debug=True)