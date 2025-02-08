import mysql.connector

db = mysql.connector.connect(
    host="Paras789789.mysql.pythonanywhere-services.com",
    user="Paras789789",
    password="12345@Paras@12345",
    database="Paras789789$default"
)

cursor = db.cursor()

# Path to your SQL file (change this to the correct path)
sql_file_path = '/home/Paras789789/mysite/flask_python.sql'

# Read the SQL file
with open(sql_file_path, 'r') as file:
    sql_script = file.read()

# Execute the SQL commands from the file
try:
    # Execute multiple queries from the script
    cursor.execute(sql_script, multi=True)
    db.commit()  # Commit changes to the database
    print("SQL file executed successfully.")
except mysql.connector.Error as err:
    print(f"Error: {err}")
    db.rollback()  # In case of an error, rollback the changes

# Close the connection
cursor.close()
db.close()