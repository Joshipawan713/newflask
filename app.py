import os
from flask import Flask, render_template, request, redirect, url_for, current_app, session, flash
import mysql.connector
from mysql.connector import Error
from werkzeug.security import generate_password_hash, check_password_hash
import secrets
from datetime import datetime, timedelta
import re
from werkzeug.utils import secure_filename
import calendar
from datetime import datetime

app = Flask(__name__)
# app.secret_key = secrets.token_hex(16)
app.secret_key = 'you_secret_key'

def get_db_connection():
    try:
        conn = mysql.connector.connect(
            host='localhost',
            user='root',
            password='Sdk@1259',
            database='flask_python'
        )
        if conn.is_connected():
            print("Connected Successfully")
        return conn
    except mysql.connector.Error as err:
        print(f"Error: {err}")
        return None
    

# custom login_required 
# use @login_required('login')
# def login_required(login_url='login'):
#     def decorator(f):
#         def wrapper(*args, **kwargs):
#             if 'user_id' not in session:  # Check if user is in session
#                 return redirect(url_for(login_url))  # Redirect to the provided login URL
#             return f(*args, **kwargs)  # If authenticated, continue with the request
#         return wrapper
#     return decorator
    
def get_current_date_time():
    now = datetime.now()
    return now.strftime('%Y-%m-%d'), now.strftime('%I:%M:%S %p')

@app.route('/')
def index():
    conn = get_db_connection()

    #if you can not use this dictionary=True then html page use data[0]
    #if you can use this dictionary=True then html page use data.id
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM books ORDER BY RAND() LIMIT 6')
    data = cursor.fetchall()
    covers_folder = os.path.join(current_app.static_folder, 'coverimage')
    
    for book in data:
        image_filename = book.get('coverpage')
        image_path = os.path.join(covers_folder, image_filename)
        
        if not image_filename or image_filename.strip() == "":
            book['coverpage'] = 'imagesnotfound.jpg'
        
        if not os.path.exists(image_path):
            book['coverpage'] = 'imagesnotfound.jpg'
    
    cursor.close()
    conn.close()

    return render_template('index.html', data=data)

@app.route('/register', methods=['GET', 'POST'])
def register():
    add_date, add_time = get_current_date_time()
    
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        mobile = request.form['mobile']
        account_type = request.form['account_type']
        password = request.form['password']
        repeat_password = request.form['repeat_password']
        
        # Check for empty fields
        if not all([name, email, mobile, account_type, password, repeat_password]):
            flash('All fields are required!', 'danger')
            return redirect(url_for('register'))
        
        # Password match check
        if password != repeat_password:
            flash('Passwords do not match!', 'danger')
            return redirect(url_for('register'))
        
        # Basic validation of email and mobile
        email_regex = r"(^\w|[a-zA-Z0-9._%+-]+)@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        mobile_regex = r"^\d{10}$"  # Assuming 10-digit mobile numbers
        
        if not re.match(email_regex, email):
            flash('Invalid email format!', 'danger')
            return redirect(url_for('register'))
        
        if not re.match(mobile_regex, mobile):
            flash('Invalid mobile number format! Must be 10 digits.', 'danger')
            return redirect(url_for('register'))
        
        hashed_password = generate_password_hash(password)
        
        status = 'Active'
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if email already exists
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        check_email = cursor.fetchone()
        if check_email:
            flash('Email already exists!', 'danger')
            conn.close()
            return redirect(url_for('register'))
        
        # Insert new user into the database
        cursor.execute("INSERT INTO users (name, email, mobile, password, account_type, status, add_date, add_time) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)", (name, email, mobile, hashed_password, account_type, status, add_date, add_time))
        
        conn.commit()
        conn.close()
        
        flash('Registration successful!', 'success')
        # return redirect(url_for('login'))  # Redirect to login after registration
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email= %s && status='Active'", (email,))
        user = cursor.fetchone()
        if user:
            if check_password_hash(user[4], password):
                session['logged_in'] = True
                session['user_id'] = user[0]
                session['name'] = user[1]
                session['email'] = user[2]
                return redirect(url_for('index'))
            else:
                flash('Invalid password!', 'danger')
        else:
            flash('Email not found!', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/admin/', methods=['GET', 'POST'])
def adminLogin():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM admin WHERE email = %s ", (username,))
        adminuser = cursor.fetchone()
        if adminuser:
            if check_password_hash(adminuser[4], password):
                session['admin_logged_in'] = True
                session['admin_user_id'] = adminuser[0]
                session['admin_name'] = adminuser[1]
                session['admin_email'] = adminuser[2]
                return redirect(url_for('adminDashboard'))
            else:
                flash('Invalid password!', 'danger')
        else:
            flash('Admin not found!', 'danger')
    return render_template('admin/index.html')

@app.route('/admin/dashboard')
def adminDashboard():
    if 'admin_logged_in' in session:
        now = datetime.now()
        year = now.year
        month = now.month
        current_date = now.day
        
        if request.args.get('year'):
            year = int(request.args.get('year'))
        if request.args.get('month'):
            month = int(request.args.get('month'))
        cal = calendar.monthcalendar(year, month)
        
        return render_template('admin/dashboard.html', calendar=cal, year=year, month=month, current_date=current_date)
    else:
        return redirect(url_for('adminLogin'))

@app.route('/admin/logout')
def adminLogout():
    session.pop('admin_logged_in', None)
    session.pop('admin_user_id', None)
    session.pop('admin_name', None)
    session.pop('admin_email', None)
    return redirect(url_for('adminLogin'))

@app.route('/admin/profile', methods=['GET', 'POST'])
def adminProfile():
    if 'admin_logged_in' in session:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM admin WHERE id = %s", (session['admin_user_id'],))
        data = cursor.fetchone()
        if request.method == 'POST':
            name = request.form['name']
            mobile = request.form['mobile']
            
            if not all([name, mobile]):
                return flash('All Fields are required', 'danger')
            
            mobile_regex = r"^\d{10}$"
            if not re.match(mobile_regex, mobile):
                flash('Mobile Number format! Must be 10 digits.', 'danger')
                return redirect(url_for('adminProfile'))
            
            cursor.execute("UPDATE admin SET name = %s , mobile= %s WHERE id = %s", (name, mobile, session['admin_user_id']))
            
            conn.commit()
            
            flash('Profile Update Successfully', 'success')
        cursor.close()
        conn.close()
            
        return render_template('admin/profile.html', data=data)
    else:
        return redirect(url_for('adminLogin'))


@app.route('/admin/changepassword', methods=['GET', 'POST'])
def adminChangePassword():
    if 'admin_logged_in' in session:
        add_date, add_time = get_current_date_time()
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM admin WHERE id = %s", (session['admin_user_id'],))
        data = cursor.fetchone()
        if request.method == 'POST':
            old_pass = request.form['old_pass']
            new_pass = request.form['new_pass']
            conf_pass = request.form['conf_pass']
            if new_pass == conf_pass:
                if check_password_hash(data[4], old_pass):
                    hashed_password = generate_password_hash(new_pass)
                    cursor.execute("UPDATE admin SET password = %s WHERE id = %s", (hashed_password, session['admin_user_id']))
                    conn.commit()
                    flash('Password Changed Successfully', 'success')
                else:
                    flash('Old Password Not Matched', 'danger')
            else:
                flash('New or Confirm Password Not Matched', 'danger')
                
        cursor.close()
        conn.close()
        
        return render_template('admin/changepassword.html')
    else:
        return redirect(url_for('adminLogin'))


@app.route('/admin/adduser', methods=['GET', 'POST'])
def adminAddUser():

    add_date, add_time = get_current_date_time()
    
    if 'admin_logged_in' in session:
        if request.method == 'POST':
            
            name = request.form['name']
            email = request.form['email']
            mobile = request.form['mobile']
            password = request.form['password']
            account_type = request.form['account_type']
            status = request.form['status']
            
            if not all([name, email, mobile, password, account_type, status]):
                flash('All fields are required!', 'danger')
                return redirect(url_for('adminAddUser'))
            
            
            email_regex = r"(^\w|[a-zA-Z0-9._%+-]+)@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
            mobile_regex = r"^\d{10}$"  # Assuming 10-digit mobile numbers
        
            if not re.match(email_regex, email):
                flash('Invalid email format!', 'danger')
                return redirect(url_for('adminAddUser'))
        
            if not re.match(mobile_regex, mobile):
                flash('Invalid mobile number format! Must be 10 digits.', 'danger')
                return redirect(url_for('adminAddUser'))
            
            hashed_password = generate_password_hash(password)
            
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE email = %s ", (email,))
            check_email = cursor.fetchone()
            
            if check_email:
                flash('Email already exists!', 'danger')
                conn.close()
                return redirect(url_for('adminAddUser'))
            
            cursor.execute("INSERT INTO users (name, email, mobile, password, account_type, status, add_date, add_time) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)", (name, email, mobile, hashed_password, account_type, status, add_date, add_time))
            
            conn.commit()
            conn.close()
            
            flash('User added successful!', 'success')
            
    return render_template('admin/adduser.html')

@app.route('/admin/showuser')
def adminShowUsers():
    if 'admin_logged_in' in session:
        conn = get_db_connection()
        #if you can not use this dictionary=True then html page use data[0]
        #if you can use this dictionary=True then html page use data.id
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users")
        users = cursor.fetchall()
        cursor.close()
        conn.close()
        return render_template('admin/showusers.html', users=users)
    else:
        return redirect(url_for('adminLogin'))
    
@app.route('/admin/edituser/<int:user_id>', methods=['GET', 'POST'])
def adminEditUser(user_id):
    if 'admin_logged_in' in session:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        
        if request.method == 'POST':
            name = request.form['name']
            password = request.form['password']
            account_type = request.form['account_type']
            status = request.form['status']
            
            if not all([name, password, account_type, status]):
                flash('Please fill all fields!', 'danger')
                return render_template('admin/edituser.html', user=user)
            
            cursor.execute("UPDATE users SET name = %s , password = %s, account_type = %s, status = %s WHERE id = %s ", (name, password, account_type, status, user_id))
            conn.commit()
            cursor.close()
            conn.close()
            
            flash('User updated successful!', 'success')
        
        return render_template('admin/editusers.html', user=user)
    else:
        return redirect(url_for('adminLogin'))

@app.route('/admin/deleteuser/<int:user_id>', methods=['GET', 'POST'])
def adminDeleteUser(user_id):
    if 'admin_logged_in' in session:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for('adminShowUsers'))
    else:
        return redirect(url_for('adminLogin'))

@app.route('/admin/addbook', methods=['GET', 'POST'])
def adminAddBooks():
    add_date, add_time = get_current_date_time()

    if 'admin_logged_in' in session:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        if request.method == 'POST':
            title = request.form['title']
            editor = request.form['editor']
            publisher_year = request.form['publisher_year']
            subject = request.form['subject']
            isbn = request.form['isbn']
            pages = request.form['pages']
            language = request.form['language']
            actual_price = request.form['actual_price']
            discounted_price = request.form['discounted_price']
            descr = request.form['descr']

            if not all([title, editor, publisher_year, subject, isbn, pages, language, actual_price, discounted_price, descr]):
                flash('All fields are required!', 'danger')
                return redirect(url_for('adminAddBooks'))

            pusg_year_regex = r"^\d{4}$"
            if not re.match(pusg_year_regex, publisher_year):
                flash('Invalid Publisher year format! Must be 4 digits.', 'danger')
                return redirect(url_for('adminAddBooks'))

            if not (pages.isdigit() and actual_price.isdigit() and discounted_price.isdigit()):
                flash('Pages, Actual Price, and Discounted Price must be valid integers.', 'danger')
                return redirect(url_for('adminAddBooks'))

            if "image" not in request.files or request.files['image'].filename == '':
                flash('Book cover image is required!', 'danger')
                return redirect(url_for('adminAddBooks'))

            image = request.files['image']
            filename = secure_filename(image.filename)
            image_path = os.path.join(current_app.static_folder, 'coverimage', filename)
            image.save(image_path)

            cursor.execute("SELECT * FROM books WHERE title = %s or isbn = %s", (title, isbn))
            existing_book = cursor.fetchone()

            if existing_book:
                flash('This book with the same title and ISBN already exists!', 'danger')
                return redirect(url_for('adminAddBooks'))

            cursor.execute("""
                INSERT INTO books (coverpage, title, editor, publisher_year, subject, isbn, pages, language, actual_price, discounted_price, descr, add_date, add_time)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (filename, title, editor, publisher_year, subject, isbn, pages, language, actual_price, discounted_price, descr, add_date, add_time))

            conn.commit()

            # Fetch the ID of the newly inserted book
            book_id = cursor.lastrowid

            # Rename the image with the book ID
            file_extension = filename.split('.')[-1]
            new_filename = f"CIIL{book_id}.{file_extension}"
            new_image_path = os.path.join(current_app.static_folder, 'coverimage', new_filename)

            # Rename the file on disk
            os.rename(image_path, new_image_path)

            # Update the database with the new image filename
            cursor.execute("""
                UPDATE books
                SET coverpage = %s
                WHERE id = %s
            """, (new_filename, book_id))

            conn.commit()

            cursor.close()
            conn.close()

            flash('Book added successfully!', 'success')
            return redirect(url_for('adminAddBooks'))
        return render_template('admin/addbooks.html')
    else:
        return redirect(url_for('adminLogin'))

@app.route('/admin/showbooks')
def adminShowBooks():
    if 'admin_logged_in' in session:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM books")
        data = cursor.fetchall()
        cursor.close()
        conn.close()
        return render_template('admin/showbooks.html', data=data)
    else:
        return redirect(url_for('adminLogin'))
    
@app.route('/admin/editbooks/<int:books_id>', methods=['GET', 'POST'])
def adminEditBooks(books_id):
    if 'admin_logged_in' in session:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM books WHERE id = %s", (books_id,))
        books = cursor.fetchone()
        if request.method == 'POST':
            title = request.form['title']
            editor = request.form['editor']
            publisher_year = request.form['publisher_year']
            subject = request.form['subject']
            isbn = request.form['isbn']
            pages = request.form['pages']
            language = request.form['language']
            actual_price = request.form['actual_price']
            discounted_price = request.form['discounted_price']
            descr = request.form['descr']
            if not all([title, editor, publisher_year, subject, isbn, pages, language, actual_price, discounted_price, descr]):
                flash('All fields are required!', 'danger')
                return redirect(url_for('adminEditBooks'))
            
            new_image_path = books['coverpage']
            if "image" in request.files and request.files['image'].filename != '':
                image = request.files['image']
                filename = secure_filename(image.filename)
                
                # Validate file type (only allow images)
                if filename.split('.')[-1].lower() not in ['jpg', 'jpeg', 'png', 'gif']:
                    flash('Invalid file type for cover image!', 'danger')
                    return redirect(url_for('adminEditBooks', books_id=books_id))

                image_path = os.path.join(current_app.static_folder, 'coverimage', filename)
                image.save(image_path)
                file_extension = filename.split('.')[-1]
                new_filename = f"CIIL{books_id}.{file_extension}"
                new_image_path = os.path.join(current_app.static_folder, 'coverimage', new_filename)
                os.rename(image_path, new_image_path)
            
            cursor.execute("""UPDATE books SET coverpage = %s, title = %s, editor = %s, publisher_year = %s, subject = %s, isbn = %s, pages = %s, language = %s, actual_price = %s, discounted_price = %s, descr = %s WHERE id = %s""", 
                           (new_filename, title, editor, publisher_year, subject, isbn, pages, language, actual_price, discounted_price, descr, books_id))
            conn.commit()
            cursor.close()
            conn.close()
            
            flash('Book Updated Successfully', 'success')
            
        return render_template('admin/editbooks.html', books=books)
    else:
        return redirect(url_for('adminLogin'))
    
@app.route('/admin/deletebook/<int:books_id>', methods=['GET', 'POST'])
def adminDeleteBook(books_id):
    if 'admin_logged_in' in session:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM books WHERE id = %s", (books_id,))
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for('adminShowBooks'))
    else:
        return redirect(url_for('adminLogin'))
    
@app.route('/admin/inventory/<int:books_id>', methods=['GET','POST'])
def adminInventoryBook(books_id):
    if 'admin_logged_in' in session:
        add_date, add_time = get_current_date_time()
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM books WHERE id = %s", (books_id,))
        data = cursor.fetchone()
        stock = data['stock']
        if request.method == 'POST':
            in_out_stock = request.form['in_out_stock']
            total_stock = int(stock) + int(in_out_stock)
            if not all([in_out_stock, total_stock]):
                flash('All fields are required!', 'danger')
                return redirect(url_for('adminInventoryBook'))
            stock_type = 'Inward'
            cursor.execute("UPDATE books SET stock = %s WHERE id = %s", (total_stock,books_id))
            cursor.execute("INSERT INTO inventory (book_id, old_stock, in_out_stock, total_stock, stock_type, add_by_name, add_by_email, add_date, add_time) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)", (books_id, stock, in_out_stock, total_stock, stock_type, session['admin_name'], session['admin_email'], add_date, add_time))
            conn.commit()
            return redirect(url_for('adminShowBooks'))
        cursor.close()
        conn.close()
        return render_template('admin/inventory.html', stock=stock)
    else:
        return redirect(url_for('adminLogin'))
    
@app.route('/admin/historybook/<int:books_id>', methods=['GET', 'POST'])
def adminHistoryBook(books_id):
    if 'admin_logged_in' in session:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT inventory.*, books.id, books.title, books.editor FROM inventory  JOIN books ON inventory.book_id = books.id  WHERE inventory.book_id = %s", (books_id,))
        inven = cursor.fetchall()
        cursor.close()
        conn.close()
        return render_template('admin/historybook.html', books_id=books_id, inven=inven)
    else:
        return redirect(url_for('adminLogin'))

@app.route('/admin/manageinventory', methods=['GET','POST'])
def adminManageInventory():
    if 'admin_logged_in' in session:
        add_date, add_time = get_current_date_time()
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        if request.method == 'POST':
            book_id = request.form['book_id']
            in_out_stock = request.form['in_out_stock']
            if not all([book_id, in_out_stock]):
                flash('All fields are required!', 'danger')
                return redirect(url_for('adminManageInventory'))
            cursor.execute("SELECT * FROM books WHERE id = %s", (book_id,))
            data = cursor.fetchone()

            if not data:
                flash('No book found with that ID.', 'danger')
                return redirect(url_for('adminManageInventory'))
            else:
                stock = int(data['stock'])
                total_stock = int(stock) + int(in_out_stock)
                stock_type = 'Inward'
                cursor.execute("UPDATE books SET stock = %s WHERE id = %s", (total_stock,book_id))
                cursor.execute("INSERT INTO inventory (book_id, old_stock, in_out_stock, total_stock, stock_type, add_by_name, add_by_email, add_date, add_time) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)", (book_id, stock, in_out_stock, total_stock, stock_type, session['admin_name'], session['admin_email'], add_date, add_time))
                conn.commit()
                flash('Stock Updated Successfuly', 'success')
                return redirect(url_for('adminManageInventory'))

        cursor.close()
        conn.close()
        return render_template('admin/manageinventory.html')
    else:
        return redirect(url_for('adminLogin'))

@app.route('/admin/addtocart')
def adminAddToCart():
    if 'admin_logged_in' in session:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM books')
        data = cursor.fetchall()
        covers_folder = os.path.join(current_app.static_folder, 'coverimage')
        
        for book in data:
            image_filename = book.get('coverpage')
            image_path = os.path.join(covers_folder, image_filename)
            
            if not image_filename or image_filename.strip() == "":
                book['coverpage'] = 'imagesnotfound.jpg'
            
            if not os.path.exists(image_path):
                book['coverpage'] = 'imagesnotfound.jpg'
        
        cursor.close()
        conn.close()
        return render_template('admin/addtocart.html', data=data)
    else:
        return redirect(url_for('adminLogin'))

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

if __name__ == '__main__':
    app.run(debug=True, port=5000)