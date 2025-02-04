import os
from flask import Flask, render_template, request, redirect, url_for, current_app, session, flash
import mysql.connector
from mysql.connector import Error
from werkzeug.security import generate_password_hash, check_password_hash
import secrets
import re
from werkzeug.utils import secure_filename
import calendar
from datetime import datetime, timedelta

app = Flask(__name__)
# app.secret_key = secrets.token_hex(16)
app.secret_key = 'you_secret_key'


# database connection start
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

# database connection end

# # custom login_required 
# # use @login_required('login')
# def login_required(login_url='login'):
#     def decorator(f):
#         def wrapper(*args, **kwargs):
#             if 'user_id' not in session:  # Check if user is in session
#                 return redirect(url_for(login_url))  # Redirect to the provided login URL
#             return f(*args, **kwargs)  # If authenticated, continue with the request
#         return wrapper
#     return decorator
    
# add date and add time start
def get_current_date_time():
    now = datetime.now()
    return now.strftime('%Y-%m-%d'), now.strftime('%I:%M:%S %p')

# add date and add time end

# user start
@app.context_processor
def inject_cart_count():
    if 'user_logged_in' in session and 'user_id' in session and 'email' in session:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT COUNT(id) as cart_count FROM user_cart WHERE user_id = %s and email = %s", (session['user_id'], session['email']))
        result = cursor.fetchone()
        conn.close()
        return {'cart_count': result['cart_count']}
    else:
        return {'cart_count': 0}


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

@app.route('/bookstore')
def bookstore():
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
    
    return render_template('bookstore.html', data=data)

@app.route('/bookdetails/<int:book_id>', methods=['GET', 'POST'])
def bookDetails(book_id):
    add_date, add_time = get_current_date_time()
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM books WHERE id = %s', (book_id,))
    data = cursor.fetchone()
    
    covers_folder = os.path.join(current_app.static_folder, 'coverimage')

    image_filename = data.get('coverpage')
    image_path = os.path.join(covers_folder, image_filename)
    if not image_filename or image_filename.strip() == "":
        data['coverpage'] = 'imagesnotfound.jpg'
            
    if not os.path.exists(image_path):
        data['coverpage'] = 'imagesnotfound.jpg'

    cursor.execute("SELECT * FROM books WHERE (subject = %s OR language = %s) AND id != %s", (data['subject'], data['language'], book_id))
    reldata = cursor.fetchall()

    for bookdata in reldata:
        relimage_filename = bookdata.get('coverpage')
        relimage_path = os.path.join(covers_folder,relimage_filename)

        if not relimage_filename or relimage_filename.strip() == "":
            bookdata['coverpage'] = 'imagesnotfound.jpg'

        if not os.path.exists(relimage_path):
            bookdata['coverpage'] = 'imagesnotfound.jpg'

    if request.method == 'POST':
        if 'user_logged_in' in session:
            cursor.execute("SELECT * FROM user_cart WHERE user_id = %s and email = %s and book_id = %s", (session['user_id'], session['email'], book_id))
            check_cart = cursor.fetchone()
            print(check_cart)
            if not check_cart:
                qty = 1
                cart_type = 'Cart'
                cursor.execute("INSERT INTO user_cart (user_id, email, book_id, qty, cart_type, add_date, add_time) VALUES (%s, %s, %s, %s, %s, %s, %s)", (session['user_id'], session['email'], book_id, qty, cart_type, add_date, add_time))
                conn.commit()
            else:
                qty = int(check_cart['qty']) + 1
                cursor.execute("UPDATE user_cart SET qty = %s WHERE user_id = %s and email = %s and book_id = %s", (qty, session['user_id'], session['email'], book_id))
                conn.commit()
        else:
            return redirect(url_for('login'))

    cursor.close()
    conn.close()

    return render_template('bookdetails.html', book_id=book_id, data=data, reldata=reldata)

@app.route('/cart', methods=['GET', 'POST'])
def userCart():
    if 'user_logged_in' in session and 'user_id' in session and 'email' in session:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        if request.method == 'POST':
            book_id = request.form.get('less') or request.form.get('add') or request.form.get('delete')
            if book_id:
                cursor.execute("SELECT qty FROM user_cart WHERE book_id = %s AND user_id = %s AND email = %s", (book_id, session['user_id'], session['email']))
                cart_item = cursor.fetchone()

                if cart_item:
                    current_qty = int(cart_item['qty'])

                    if request.form.get('less') and current_qty > 1:
                        new_qty = current_qty - 1
                        cursor.execute("UPDATE user_cart SET qty = %s WHERE book_id = %s AND user_id = %s AND email = %s",(new_qty, book_id, session['user_id'], session['email']))
                        conn.commit()

                    elif request.form.get('add'):
                        new_qty = current_qty + 1
                        cursor.execute("UPDATE user_cart SET qty = %s WHERE book_id = %s AND user_id = %s AND email = %s", (new_qty, book_id, session['user_id'], session['email']))
                        conn.commit()

                    elif request.form.get('delete'):
                        cursor.execute("DELETE FROM user_cart WHERE book_id = %s AND user_id = %s AND email = %s", (book_id, session['user_id'], session['email']))
                        conn.commit()

        cursor.execute("SELECT books.id, books.coverpage, books.title, books.subject, books.publisher_year, books.discounted_price, user_cart.user_id, user_cart.email, user_cart.book_id, user_cart.qty FROM user_cart JOIN books ON books.id = user_cart.book_id WHERE user_cart.user_id = %s and user_cart.email = %s", (session['user_id'], session['email']))
        cart_data = cursor.fetchall()
        total_price = 0
        covers_folder = os.path.join(current_app.static_folder, 'coverimage')
        for books in cart_data:
            image_filename = books.get('coverpage')
            image_path = os.path.join(covers_folder, image_filename)

            if not image_filename or image_filename.strip() == "":
                books['coverpage'] = "imagesnotfound.jpg"

            if not os.path.exists(image_path):
                books['coverpage'] = "imagesnotfound.jpg"

            books['price'] = int(books['discounted_price']) * int(books['qty'])
            
            total_price += int(books['discounted_price']) * int(books['qty'])

        return render_template('cart.html', cart_data=cart_data, total_price=total_price)
    else:
        return redirect(url_for('login'))
    
@app.route('/checkout', methods=['GET', 'POST'])
def userCheckout():
    if 'user_logged_in' in session and 'user_id' in session and 'email' in session:
        add_date, add_time = get_current_date_time()
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT books.id, books.coverpage, books.title, books.subject, books.stock, books.publisher_year, books.discounted_price, user_cart.user_id, user_cart.email, user_cart.book_id, user_cart.qty FROM user_cart JOIN books ON books.id = user_cart.book_id WHERE user_cart.user_id = %s and user_cart.email = %s", (session['user_id'], session['email']))
        data = cursor.fetchall()

        if not data:
            return redirect(url_for('userCart'))

        # first method
        total_price = 0
        total_quantity = 0
        for item in data:
            total_price += int(item['qty']) * int(item['discounted_price'])
            total_quantity += int(item['qty'])

        # # second method
        # total_price = sum(int(item['qty']) * int(item['discounted_price']) for item in data)
        # total_quantity = sum(int(item['qty']) for item in data)

        dis_price = 0
        handling_charges = 40 * total_quantity
        shipping_charges = 150

        new_total_price = total_price + shipping_charges + handling_charges

        if request.method == 'POST':
            name = request.form.get('name')
            email = request.form.get('email')
            mobile = request.form.get('mobile')
            address = request.form.get('address')
            state = request.form.get('state')
            district = request.form.get('district')
            pincode = request.form.get('pincode')
            txn_status=1

            if not all([name, email, mobile, address, state, district, pincode]):
                flash('All Fields are required', 'danger')
                return redirect(url_for('userCheckout'))

            email_regex = r"(^\w|[a-zA-Z0-9._%+-]+)@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
            if not re.match(email_regex, email):
                flash('Invalid email format!', 'danger')
                return redirect(url_for('userCheckout'))
            
            mobile_regex = r"^\d{10}$"
            if not re.match(mobile_regex, mobile):
                flash('Invalid mobile number format! Must be 10 digits.', 'danger')
                return redirect(url_for('userCheckout'))

            pincode_regex = r"^\d{6}$"
            if not re.match(pincode_regex, pincode):
                flash('Invalid pincode format! Must be 6 digits.', 'danger')
                return redirect(url_for('userCheckout'))
            
            current_year = datetime.now().year

            cursor.execute("SELECT order_id FROM orders WHERE order_id LIKE %s ORDER BY order_id DESC LIMIT 1", (f"OR-{current_year}-%",))
            last_order = cursor.fetchone()
            
            if last_order is None:
                order_number = 1
            else:
                last_order_id = last_order['order_id']
                order_number = int(last_order_id.split('-')[2]) + 1

            order_id = f"OR-ON-{current_year}-{order_number}"

            cursor.execute("SELECT invoice_no FROM invoice WHERE invoice_no LIKE %s ORDER BY invoice_no DESC LIMIT 1", (f"IN-{current_year}-%",))
            last_invoice = cursor.fetchone()

            if last_invoice is None:
                invoice_number = 1
            else:
                last_invoice_no = last_invoice['invoice_no']
                invoice_number = int(last_invoice_no.split('-')[2]) + 1

            invoice_no = f"IN-ON-{current_year}-{invoice_number}"

            for orddet in data:
                stock = int(orddet['stock']) - int(orddet['qty'])
                stock_type = 'Online_Sell'
                # stock = 1
                cursor.execute("INSERT INTO order_details (order_id, book_id, user_id, email, qty, add_date, add_time) VALUES (%s, %s, %s, %s, %s, %s, %s)", (order_id, orddet['book_id'], session['user_id'], session['email'], orddet['qty'], add_date, add_time))
                
                cursor.execute("UPDATE books SET stock = %s WHERE id = %s", (stock, orddet['book_id']))
                
                cursor.execute("INSERT INTO inventory (book_id, old_stock, in_out_stock, total_stock, stock_type, add_by_name, add_by_email, add_date, add_time) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)", (orddet['book_id'], orddet['stock'], orddet['qty'], stock, stock_type, session['name'], session['email'], add_date, add_time))

            cursor.execute("INSERT INTO orders (order_id, user_id, user_email, name, email, mobile, address, state, district, pincode, price, dis_price, shipping_charges, handling_charges, total_price, txn_status, add_date, add_time) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)", (order_id, session['user_id'], session['email'], name, email, mobile, address, state, district, pincode, total_price, dis_price, shipping_charges, handling_charges, new_total_price, txn_status, add_date, add_time))

            cursor.execute("INSERT INTO invoice (invoice_no, order_id, user_id, user_email, name, email, mobile, address, state, district, pincode, price, dis_price, shipping_charges, handling_charges, total_price, add_date, add_time) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)", (invoice_no, order_id, session['user_id'], session['email'], name, email, mobile, address, state, district, pincode, total_price, dis_price, shipping_charges, handling_charges, new_total_price, add_date, add_time))

            cursor.execute("DELETE FROM user_cart WHERE user_id = %s and email = %s", (session['user_id'], session['email']))
            
            conn.commit()

            return redirect(url_for('paymentsuccess'))

        cursor.close()
        conn.close()
        
        # # first method
        # return render_template('checkout.html', handling_charges=handling_charges, shipping_charges=shipping_charges, total_price=total_price, new_total_price=new_total_price)
        
        # second method
        context = {
            'handling_charges': handling_charges, 
            'shipping_charges': shipping_charges, 
            'total_price': total_price, 
            'new_total_price':new_total_price
        }

        return render_template('checkout.html', **context)
    else:
        return redirect(url_for('login'))
    
@app.route('/success')
def paymentsuccess():
    if 'user_logged_in' in session and 'user_id' in session and 'email' in session:
        return render_template('success.html')
    else:
        return redirect(url_for('login'))

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
        
        if not all([email, password]):
            flash('Email and password not empty', 'danger')
            return redirect(url_for('login'))
            
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email= %s", (email,))
        user = cursor.fetchone()
        if user:
            if user[6] == "Active":
                if check_password_hash(user[4], password):
                    session['user_logged_in'] = True
                    session['user_id'] = user[0]
                    session['name'] = user[1]
                    session['email'] = user[2]
                    return redirect(url_for('index'))
                else:
                    flash('Invalid password!', 'danger')
            else:
                flash('Your account is deactive!', 'danger')
        else:
            flash('Email not found!', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/profile', methods=['GET', 'POST'])
def userProfile():
    if 'user_logged_in' in session and 'user_id' in session and 'email' in session:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE id = %s", (session['user_id'],))
        data = cursor.fetchone()
        
        if request.method == 'POST':
            name = request.form['name']
            mobile = request.form['mobile']
            
            if not all([name, mobile]):
                flash('Name and mobile not empty', 'danger')
                return redirect(url_for('userProfile'))
            
            mobile_regex = r"^\d{10}$"
        
            if not re.match(mobile_regex, mobile):
                flash('Invalid mobile number format! Must be 10 digits.', 'danger')
                return redirect(url_for('userProfile'))
            
            cursor.execute("UPDATE users SET name = %s, mobile = %s WHERE id = %s", (name,mobile,session['user_id']))
            conn.commit()
            
            flash('Profile Updated Successfully', 'success')
            return redirect(url_for('userProfile'))
        
        cursor.close()
        conn.close()
        
        return render_template('profile.html', data=data)
    else:
        return redirect(url_for('login'))

@app.route('/changepassword', methods=['GET', 'POST'])
def userChangePassword():
    if 'user_logged_in' in session and 'user_id' in session and 'email' in session:
        if request.method == 'POST':
            old_pass = request.form['old_pass']
            new_pass = request.form['new_pass']
            repeat_pass = request.form['repeat_pass']
            
            if not all([old_pass, new_pass, repeat_pass]):
                flash('All fields are required', 'danger')
                return redirect(url_for('userChangePassword'))
            
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM users WHERE id = %s", (session['user_id'],))
            users = cursor.fetchone()
            if users:
                if new_pass == repeat_pass:
                    if check_password_hash(users['password'], old_pass):
                        hashed_password = generate_password_hash(new_pass)
                        cursor.execute("UPDATE users SET password = %s WHERE id = %s", (hashed_password, session['user_id']))
                        conn.commit()
                        flash('Password Chnage Successfully', 'success')
                        return redirect(url_for('userChangePassword'))
                    else:
                        flash('Old Password are incorrect', 'danger')
                        return redirect(url_for('userChangePassword'))
                else:
                    flash('New and Repeat Password are incorrect', 'danger')
                    return redirect(url_for('userChangePassword'))
            else:
                flash('User Not Exist', 'danger')
                return redirect(url_for('userChangePassword'))
                
            cursor.close()
            conn.close()
        return render_template('changepassword.html')
    else:
        return redirect(url_for('login'))
    
@app.route('/address', methods=['GET', 'POST'])
def userAddress():
    if 'user_logged_in' in session and 'user_id' in session and 'email' in session:
        if request.method == 'POST':
            add_date, add_time = get_current_date_time()
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            # cursor.execute("SELECT * FROM users WHERE id = %s", (session['user_id'],))
            
            name = request.form['name']
            mobile = request.form['mobile']
            email = request.form['email']
            address = request.form['address']
            state = request.form['state']
            district = request.form['district']
            pincode = request.form['pincode']
            
            if not all([name, mobile, email, address, state, district, pincode]):
                flash('All Fields are required', 'danger')
                return redirect(url_for('userAddress'))
            
            email_regex = r"(^\w|[a-zA-Z0-9._%+-]+)@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
            if not re.match(email_regex, email):
                flash('Invalid email format!', 'danger')
                return redirect(url_for('userAddress'))
            
            mobile_regex = r"^\d{10}$"
            if not re.match(mobile_regex, mobile):
                flash('Mobile Number format! Must be 10 digits.', 'danger')
                return redirect(url_for('userAddress'))
            
            pincode_regex = r"^\d{6}$"
            if not re.match(pincode_regex, pincode):
                flash('Pincode Format! Must be 6 digit', 'danger')
                return redirect(url_for('userAddress'))
            
            cursor.execute("INSERT INTO address (user_id, name, mobile, email, address, state, district, pincode, add_date, add_time) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)", (session['user_id'], name, mobile, email, address, state, district, pincode, add_date, add_time))
            
            conn.commit()
            flash('Address added Successfully', 'success')
            
            cursor.close()
            conn.close()
                
        return render_template('address.html')
    else:
        return redirect(url_for('login'))

# user start

# admin start
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

@app.route('/admin/index')
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
        
        return render_template('admin/dashboard.html', calendar=cal, year=year, month=month, current_date=current_date, now=now)
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
            book_ids = request.form.getlist('book_id[]')
            in_out_stocks = request.form.getlist('in_out_stock[]')

            if not all([book_ids, in_out_stocks]) or len(book_ids) != len(in_out_stocks):
                flash('All fields are required for each book!', 'danger')
                return redirect(url_for('adminManageInventory'))

            for book_id, in_out_stock in zip(book_ids, in_out_stocks):
                if not book_id or not in_out_stock:
                    continue  # Skip empty inputs (just in case)

                # Convert stock change to integer
                try:
                    in_out_stock = int(in_out_stock)
                except ValueError:
                    flash('Invalid stock value for book ID: ' + book_id, 'danger')
                    return redirect(url_for('adminManageInventory'))

                # Check if book exists
                cursor.execute("SELECT * FROM books WHERE id = %s", (book_id,))
                data = cursor.fetchone()

                if not data:
                    flash(f'No book found with ID {book_id}.', 'danger')
                    continue  # Skip this book if not found

                # Update stock
                stock = int(data['stock'])
                total_stock = stock + in_out_stock
                stock_type = 'Inward'

                cursor.execute("UPDATE books SET stock = %s WHERE id = %s", (total_stock, book_id))
                cursor.execute("INSERT INTO inventory (book_id, old_stock, in_out_stock, total_stock, stock_type, add_by_name, add_by_email, add_date, add_time) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                               (book_id, stock, in_out_stock, total_stock, stock_type, session['admin_name'], session['admin_email'], add_date, add_time))

            conn.commit()
            return redirect(url_for('adminManageInventory'))

        cursor.close()
        conn.close()
        return render_template('admin/manageinventory.html')
    else:
        return redirect(url_for('adminLogin'))

@app.route('/admin/addtocart', methods=['GET', 'POST'])
def adminAddToCart():
    if 'admin_logged_in' in session:
        add_date, add_time = get_current_date_time()
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT COUNT(id) as count_cart FROM admin_cart")
        cart_result = cursor.fetchone()
        count_cart = cart_result['count_cart']

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
        
        if request.method == 'POST':
            book_id = request.form['book_id']
            cursor.execute("SELECT * FROM admin_cart WHERE book_id = %s", (book_id,))
            check_exist = cursor.fetchone()
            if not check_exist:
                qty = 1
                cursor.execute("INSERT INTO admin_cart (book_id, qty, add_by_name, add_by_email, add_date, add_time) VALUES (%s, %s, %s, %s, %s, %s)", (book_id, qty, session['admin_name'], session['admin_email'], add_date, add_time))
                conn.commit()
            else:
                qty = int(check_exist['qty']) + 1
                cursor.execute("UPDATE admin_cart SET qty = %s WHERE book_id = %s", (qty, book_id))
                conn.commit()
            
            return redirect(url_for('adminAddToCart'))

        cursor.close()
        conn.close()
        return render_template('admin/addtocart.html', data=data,count_cart=count_cart)
    else:
        return redirect(url_for('adminLogin'))

@app.route('/admin/showcart', methods=['GET', 'POST'])
def adminShowCart():
    if 'admin_logged_in' in session:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT COUNT(id) as count_cart FROM admin_cart")
        cart_result = cursor.fetchone()
        count_cart = cart_result['count_cart']

        if count_cart == 0:
            return redirect(url_for('adminAddToCart'))

        total_price = 0

        cursor.execute("SELECT admin_cart.book_id, admin_cart.qty, books.title,books.coverpage,books.editor, books.actual_price, books.discounted_price FROM admin_cart JOIN books ON admin_cart.book_id = books.id")
        show_result = cursor.fetchall()
        covers_folder = os.path.join(current_app.static_folder, 'coverimage')

        for book in show_result:
            image_filename = book.get('coverpage')
            image_path = os.path.join(covers_folder, image_filename)
            
            if not image_filename or image_filename.strip() == "":
                book['coverpage'] = 'imagesnotfound.jpg'
            
            if not os.path.exists(image_path):
                book['coverpage'] = 'imagesnotfound.jpg'
            
            total_price += int(book['qty']) * int(book['discounted_price'])

        if request.method == 'POST':
            books_id = request.form['books_id']
            
            if not books_id:
                flash('Book Id missing', 'danger')
            
            cursor.execute("DELETE FROM admin_cart WHERE book_id = %s", (books_id,))
            conn.commit()
            return redirect(url_for('adminShowCart'))

        cursor.close()
        conn.close()

        return render_template('admin/showcart.html', count_cart=count_cart, show_result=show_result, total_price=total_price)
    else:
        return redirect(url_for('adminLogin'))


@app.route('/admin/checkout', methods=['GET', 'POST'])
def adminCheckout():
    if 'admin_logged_in' in session:
        add_date, add_time = get_current_date_time()
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT admin_cart.book_id, admin_cart.qty, books.stock, books.id, books.actual_price, books.discounted_price FROM admin_cart JOIN books ON admin_cart.book_id = books.id")
        data = cursor.fetchall()

        if not data:
            return redirect(url_for('adminAddToCart'))

        total_price = sum(int(item['qty']) * int(item['discounted_price']) for item in data)
        
        if request.method == 'POST':
            bill_name = request.form['bill_name']
            bill_email = request.form['bill_email']
            bill_mobile = request.form['bill_mobile']
            bill_address = request.form['bill_address']
            bill_state = request.form['bill_state']
            bill_district = request.form['bill_district']
            bill_pincode = request.form['bill_pincode']
            off_name = request.form['off_name']
            off_email = request.form['off_email']
            off_mobile = request.form['off_mobile']
            off_address = request.form['off_address']
            off_state = request.form['off_state']
            off_district = request.form['off_district']
            off_pincode = request.form['off_pincode']
            dis_price = request.form['dis_price']
            shipping_charges = request.form['shipping_charges']

            if not all([bill_name, bill_email, bill_mobile, bill_address, bill_state, bill_district, bill_pincode, off_name, off_email, off_mobile, off_address, off_state, off_district, off_pincode, dis_price, shipping_charges]):
                flash('All fields are required!', 'danger')
                return redirect(url_for('adminCheckout'))
            
            email_regex = r"(^\w|[a-zA-Z0-9._%+-]+)@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
            mobile_regex = r"^\d{10}$"
            pin_regex = r"^\d{6}$"
        
            if not re.match(email_regex, bill_email):
                flash('Invalid billing email format!', 'danger')
                return redirect(url_for('adminCheckout'))

            if not re.match(email_regex, off_email):
                flash('Invalid shipping email format!', 'danger')
                return redirect(url_for('adminCheckout'))

            if not re.match(mobile_regex, bill_mobile):
                flash('Invalid billing mobile number format! Must be 10 digits.', 'danger')
                return redirect(url_for('adminCheckout'))

            if not re.match(mobile_regex, off_mobile):
                flash('Invalid shipping mobile number format! Must be 10 digits.', 'danger')
                return redirect(url_for('adminCheckout'))
            
            if not re.match(pin_regex, bill_pincode):
                flash('Invalid shipping pincode number format! Must be 6 digits.', 'danger')
                return redirect(url_for('adminCheckout'))
            
            if not re.match(pin_regex, off_pincode):
                flash('Invalid shipping pincode number format! Must be 6 digits.', 'danger')
                return redirect(url_for('adminCheckout'))
            
            if not shipping_charges.isdigit():
                flash('Shipping charges is not an digit', 'danger')
                return redirect(url_for('adminCheckout'))
            
            if not dis_price.isdigit():
                flash('Discount price is not an digit', 'danger')
                return redirect(url_for('adminCheckout'))

            new_total_price = int(total_price) + int(shipping_charges) - int(dis_price)

            txn_status = 1

            current_year = datetime.now().year

            cursor.execute("SELECT order_id FROM off_orders WHERE order_id LIKE %s ORDER BY order_id DESC LIMIT 1", (f"OR-{current_year}-%",))
            last_order = cursor.fetchone()
            
            if last_order is None:
                order_number = 1
            else:
                last_order_id = last_order['order_id']
                order_number = int(last_order_id.split('-')[2]) + 1

            order_id = f"OR-{current_year}-{order_number}"

            cursor.execute("SELECT invoice_no FROM off_invoice WHERE invoice_no LIKE %s ORDER BY invoice_no DESC LIMIT 1", (f"IN-{current_year}-%",))
            last_invoice = cursor.fetchone()

            if last_invoice is None:
                invoice_number = 1
            else:
                last_invoice_no = last_invoice['invoice_no']
                invoice_number = int(last_invoice_no.split('-')[2]) + 1

            invoice_no = f"IN-{current_year}-{invoice_number}"

            for ordbook in data:
                stock = int(ordbook['stock']) - int(ordbook['qty'])
                stock_type = 'Offline_Sell'
                cursor.execute("INSERT INTO off_order_details (order_id, book_id, email, qty, add_date, add_time) VALUES(%s, %s, %s, %s, %s, %s)", (order_id, ordbook['book_id'], session['admin_email'], ordbook['qty'], add_date, add_time))
                
                cursor.execute("UPDATE books SET stock = %s WHERE id = %s", (stock, ordbook['book_id']))
                
                cursor.execute("INSERT INTO inventory (book_id, old_stock, in_out_stock, total_stock, stock_type, add_by_name, add_by_email, add_date, add_time) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)", (ordbook['book_id'], ordbook['stock'], ordbook['qty'], stock, stock_type, session['admin_name'], session['admin_email'], add_date, add_time))

            cursor.execute("""INSERT INTO off_orders (order_id, bill_name, bill_email, bill_mobile, bill_address, bill_state, bill_district, bill_pincode, off_name, off_email, off_mobile, off_address, off_state, off_district, off_pincode, price, dis_price, shipping_charges, total_price, txn_status, add_by_name, add_by_email, add_date, add_time) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""", (order_id, bill_name, bill_email, bill_mobile, bill_address, bill_state, bill_district, bill_pincode, off_name, off_email, off_mobile, off_address, off_state, off_district, off_pincode, total_price, dis_price, shipping_charges, new_total_price, txn_status, session['admin_name'], session['admin_email'], add_date, add_time))
            
            cursor.execute("INSERT INTO off_invoice (invoice_no, order_id, name, email, mobile, address, state, district, pincode, price, dis_price, shipping_charges, total_price, add_by_name, add_by_email, add_date, add_time) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)", (invoice_no, order_id, bill_name, bill_email, bill_mobile, bill_address, bill_state, bill_district, bill_pincode, total_price, dis_price, shipping_charges, total_price, session['admin_name'], session['admin_email'], add_date, add_time))
            
            cursor.execute("DELETE FROM admin_cart WHERE add_by_email = %s", (session['admin_email'],))
            
            conn.commit()

            return redirect(url_for('adminAddToCart'))

        cursor.close()
        conn.close()

        return render_template('admin/checkout.html', total_price=total_price)
    else:
        return redirect(url_for('adminLogin'))


@app.route('/admin/offlineorders')
def adminOfflineOrders():
    if 'admin_logged_in' in session:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM off_orders WHERE txn_status = 1")
        data = cursor.fetchall()
        return render_template('admin/offlineorders.html', data=data)
    else:
        return redirect(url_for('adminLogin'))

@app.route('/admin/offlineinvoice')
def adminOfflineInvoice():
    if 'admin_logged_in' in session:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM off_invoice")
        data = cursor.fetchall()
        return render_template('admin/offlineinvoice.html', data=data)
    else:
        return redirect(url_for('adminLogin'))
    
@app.route('/admin/onlineorders')
def adminOnlineOrders():
    if 'admin_logged_in' in session:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM orders WHERE txn_status = 1")
        data = cursor.fetchall()
        return render_template('admin/onlineorders.html', data=data)
    else:
        return redirect(url_for('adminLogin'))

@app.route('/admin/onlineinvoice')
def adminOnlineInvoice():
    if 'admin_logged_in' in session:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM invoice")
        data = cursor.fetchall()
        return render_template('admin/onlineinvoice.html', data=data)
    else:
        return redirect(url_for('adminLogin'))

# admin end

# page not found start
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

# page not found end

if __name__ == '__main__':
    app.run(debug=True, port=5000)