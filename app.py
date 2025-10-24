import os
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file, render_template_string
import sqlite3
from datetime import datetime
import json
import base64
from io import BytesIO
import pdfkit
from functools import wraps

# Ensure pdfkit is installed and configured if needed for PDF generation.
# On some systems, you might need to install wkhtmltopdf:
# sudo apt-get install wkhtmltopdf

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# In-memory database setup (for demo purposes)
def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    
    # Create tables
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT NOT NULL,
                  email TEXT UNIQUE NOT NULL,
                  password TEXT NOT NULL,
                  phone TEXT,
                  address TEXT,
                  role TEXT DEFAULT 'user',
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS bookings
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  tour_id INTEGER,
                  tour_name TEXT NOT NULL,
                  tour_date TEXT NOT NULL,
                  participants INTEGER DEFAULT 1,
                  total_price REAL NOT NULL,
                  status TEXT DEFAULT 'pending',
                  admin_confirmed BOOLEAN DEFAULT 0,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY (user_id) REFERENCES users (id),
                  FOREIGN KEY (tour_id) REFERENCES tours (id))''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS tours
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT NOT NULL,
                  description TEXT,
                  price REAL NOT NULL,
                  image BLOB,
                  region TEXT,
                  duration TEXT,
                  difficulty TEXT,
                  featured INTEGER DEFAULT 0,
                  tour_type TEXT DEFAULT 'private',
                  available_seats INTEGER DEFAULT 0,
                  group_start_date TEXT,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS support_tickets
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  subject TEXT NOT NULL,
                  message TEXT NOT NULL,
                  status TEXT DEFAULT 'open',
                  admin_response TEXT,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY (user_id) REFERENCES users (id))''')
    
    # Check if admin user exists
    c.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)", 
                 ('Admin User', 'admin@northtripsandtravel.com', 'admin786', 'admin'))
    
    # Check if tours already exist
    c.execute("SELECT COUNT(*) FROM tours")
    if c.fetchone()[0] == 0:
        # Sample tours with placeholder images - prices in PKR
        sample_tours = [
    ('Skardu Adventure Escape', 'Discover the beauty of Skardu with visits to Shangrila Lake, Shigar Fort, and breathtaking mountain views.', 38000, 'Pakistan', '6 days', 'Moderate', 1, 'private', 0, None),
    ('Swat Serenity Retreat', 'Enjoy the green valleys and rivers of Swat with cultural walks, waterfalls, and peaceful stays in natural surroundings.', 26000, 'Pakistan', '4 days', 'Easy', 1, 'private', 0, None),
    ('Kalam Valley Expedition', 'Explore the pine forests and rivers of Kalam, visit Ushu Forest, and experience local hospitality.', 27000, 'Pakistan', '5 days', 'Moderate', 1, 'group', 12, '2025-06-20'),
    ('Khaplu Heritage Journey', 'Visit the historic Khaplu Palace, hike in surrounding valleys, and enjoy traditional Balti cuisine.', 49000, 'Pakistan', '6 days', 'Moderate', 1, 'group', 10, '2025-07-05'),
    ('Basho Valley Trek', 'Experience untouched nature in Basho Valley with scenic treks, camping by rivers, and star-filled nights.', 55000, 'Pakistan', '7 days', 'Challenging', 0, 'private', 0, None)
        ]
        
        for tour in sample_tours:
            c.execute("INSERT INTO tours (name, description, price, region, duration, difficulty, featured, tour_type, available_seats, group_start_date) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", tour)
    
    conn.commit()
    conn.close()

# Initialize database
init_db()

# Helper functions
def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

def is_admin():
    return 'user_role' in session and session['user_role'] == 'admin'

def require_admin(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_admin():
            flash('Admin access required', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def format_currency(amount):
    """Format amount as PKR currency"""
    return "PKR {:,.0f}".format(amount)

# --- Routes (Refactored to use render_template) ---

@app.route('/')
def index():
    conn = get_db_connection()
    featured_tours = conn.execute('''
        SELECT * FROM tours 
        WHERE featured = 1 
        ORDER BY created_at DESC 
        LIMIT 6
    ''').fetchall()
    
    # Convert image blobs to base64 for display
    tours_with_images = []
    for tour in featured_tours:
        tour_dict = dict(tour)
        if tour_dict['image']:
            tour_dict['image_base64'] = base64.b64encode(tour_dict['image']).decode('utf-8')
        else:
            tour_dict['image_base64'] = None
        tours_with_images.append(tour_dict)
    
    conn.close()
    
    return render_template('index.html', tours=tours_with_images, is_admin=is_admin())

@app.route('/tours')
def tours():
    conn = get_db_connection()
    all_tours = conn.execute('SELECT * FROM tours ORDER BY created_at DESC').fetchall()
    
    tours_with_images = []
    for tour in all_tours:
        tour_dict = dict(tour)
        if tour_dict['image']:
            tour_dict['image_base64'] = base64.b64encode(tour_dict['image']).decode('utf-8')
        else:
            tour_dict['image_base64'] = None
        tours_with_images.append(tour_dict)
    
    conn.close()
    return render_template('tours.html', tours=tours_with_images, is_admin=is_admin())

@app.route('/tour/<int:tour_id>')
def tour_detail(tour_id):
    conn = get_db_connection()
    tour = conn.execute('SELECT * FROM tours WHERE id = ?', (tour_id,)).fetchone()
    conn.close()
    
    if tour is None:
        flash('Tour not found.', 'error')
        return redirect(url_for('tours'))

    tour_dict = dict(tour)
    if tour_dict['image']:
        tour_dict['image_base64'] = base64.b64encode(tour_dict['image']).decode('utf-8')
    else:
        tour_dict['image_base64'] = None
    
    return render_template('tour_detail.html', tour=tour_dict, format_currency=format_currency)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE email = ? AND password = ?', (email, password)).fetchone()
        conn.close()
        
        if user:
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            session['user_role'] = user['role']
            flash('Logged in successfully!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid email or password.', 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        phone = request.form.get('phone')
        address = request.form.get('address')
        
        conn = get_db_connection()
        try:
            conn.execute('INSERT INTO users (name, email, password, phone, address) VALUES (?, ?, ?, ?, ?)',
                         (name, email, password, phone, address))
            conn.commit()
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Email already registered.', 'error')
        finally:
            conn.close()
            
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('user_name', None)
    session.pop('user_role', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session:
        flash('Please log in to view your profile.', 'warning')
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    
    if request.method == 'POST':
        name = request.form['name']
        phone = request.form.get('phone')
        address = request.form.get('address')
        
        conn.execute('UPDATE users SET name = ?, phone = ?, address = ? WHERE id = ?',
                     (name, phone, address, user_id))
        conn.commit()
        session['user_name'] = name # Update session name
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('profile'))
    
    bookings = conn.execute('''
        SELECT * FROM bookings 
        WHERE user_id = ? 
        ORDER BY created_at DESC
    ''', (user_id,)).fetchall()
    
    conn.close()
    
    return render_template('profile.html', user=user, bookings=bookings)

@app.route('/book/<int:tour_id>', methods=['GET', 'POST'])
def book_tour(tour_id):
    if 'user_id' not in session:
        flash('Please log in to book a tour.', 'warning')
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    conn = get_db_connection()
    tour = conn.execute('SELECT * FROM tours WHERE id = ?', (tour_id,)).fetchone()
    
    if tour is None:
        conn.close()
        flash('Tour not found.', 'error')
        return redirect(url_for('tours'))
    
    tour_dict = dict(tour)
    
    if request.method == 'POST':
        try:
            participants = int(request.form['participants'])
            if participants <= 0:
                flash('Number of participants must be greater than zero.', 'error')
                return redirect(url_for('book_tour', tour_id=tour_id))
            
            tour_date = request.form['tour_date']
            total_price = participants * tour_dict['price']
            
            # Basic validation for group tours
            if tour_dict['tour_type'] == 'group':
                if tour_dict['available_seats'] > 0 and participants > tour_dict['available_seats']:
                    flash(f"Only {tour_dict['available_seats']} seats available for this group tour.", 'error')
                    return redirect(url_for('book_tour', tour_id=tour_id))
                
                if tour_date != tour_dict['group_start_date']:
                    flash(f"Group tour must be booked for the specified start date: {tour_dict['group_start_date']}", 'error')
                    return redirect(url_for('book_tour', tour_id=tour_id))
            
            conn.execute('''
                INSERT INTO bookings (user_id, tour_id, tour_name, tour_date, participants, total_price) 
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, tour_id, tour_dict['name'], tour_date, participants, total_price))
            
            # Deduct seats for group tours
            if tour_dict['tour_type'] == 'group' and tour_dict['available_seats'] > 0:
                new_seats = max(0, tour_dict['available_seats'] - participants)
                conn.execute('UPDATE tours SET available_seats = ? WHERE id = ?', (new_seats, tour_id))
                
            conn.commit()
            flash('Tour booked successfully! Check your profile for details.', 'success')
            return redirect(url_for('profile'))
            
        except ValueError:
            flash('Invalid number of participants.', 'error')
        except Exception as e:
            flash(f'An error occurred during booking: {e}', 'error')
        finally:
            conn.close()
            
    conn.close()
    
    # Convert image for display on GET request
    if tour_dict['image']:
        tour_dict['image_base64'] = base64.b64encode(tour_dict['image']).decode('utf-8')
    else:
        tour_dict['image_base64'] = None
        
    return render_template('book_tour.html', tour=tour_dict, format_currency=format_currency)

@app.route('/cancel_booking/<int:booking_id>')
def cancel_booking(booking_id):
    if 'user_id' not in session:
        flash('Please log in.', 'warning')
        return redirect(url_for('login'))
        
    user_id = session['user_id']
    conn = get_db_connection()
    booking = conn.execute('SELECT * FROM bookings WHERE id = ? AND user_id = ?', (booking_id, user_id)).fetchone()
    
    if booking:
        if booking['status'] == 'pending' and not booking['admin_confirmed']:
            # Refund seats for group tours
            tour = conn.execute('SELECT id, available_seats, tour_type FROM tours WHERE id = ?', (booking['tour_id'],)).fetchone()
            if tour and tour['tour_type'] == 'group':
                new_seats = tour['available_seats'] + booking['participants']
                conn.execute('UPDATE tours SET available_seats = ? WHERE id = ?', (new_seats, tour['id']))
                
            conn.execute('DELETE FROM bookings WHERE id = ?', (booking_id,))
            conn.commit()
            flash('Booking cancelled successfully.', 'success')
        else:
            flash('Cannot cancel confirmed or processed bookings.', 'error')
    else:
        flash('Booking not found or you do not have permission.', 'error')
        
    conn.close()
    return redirect(url_for('profile'))

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        if 'user_id' not in session:
            flash('Please log in to submit a support ticket.', 'warning')
            return redirect(url_for('login'))
            
        user_id = session['user_id']
        subject = request.form['subject']
        message = request.form['message']
        
        conn = get_db_connection()
        conn.execute('INSERT INTO support_tickets (user_id, subject, message) VALUES (?, ?, ?)',
                     (user_id, subject, message))
        conn.commit()
        conn.close()
        flash('Support ticket submitted successfully. We will respond soon.', 'success')
        return redirect(url_for('contact'))
        
    return render_template('contact.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/admin_dashboard')
@require_admin
def admin_dashboard():
    conn = get_db_connection()
    total_users = conn.execute('SELECT COUNT(*) FROM users WHERE role = "user"').fetchone()[0]
    total_tours = conn.execute('SELECT COUNT(*) FROM tours').fetchone()[0]
    pending_bookings = conn.execute('SELECT COUNT(*) FROM bookings WHERE status = "pending"').fetchone()[0]
    open_tickets = conn.execute('SELECT COUNT(*) FROM support_tickets WHERE status = "open"').fetchone()[0]
    
    recent_bookings = conn.execute('''
        SELECT b.*, u.name as user_name, t.name as tour_name 
        FROM bookings b
        JOIN users u ON b.user_id = u.id
        JOIN tours t ON b.tour_id = t.id
        ORDER BY b.created_at DESC LIMIT 5
    ''').fetchall()
    
    conn.close()
    return render_template('admin/dashboard.html', 
                           total_users=total_users, 
                           total_tours=total_tours, 
                           pending_bookings=pending_bookings, 
                           open_tickets=open_tickets,
                           recent_bookings=recent_bookings)

@app.route('/admin_tours', methods=['GET', 'POST'])
@require_admin
def admin_tours():
    conn = get_db_connection()
    
    if request.method == 'POST':
        # Add new tour logic
        name = request.form['name']
        description = request.form['description']
        price = float(request.form['price'])
        region = request.form['region']
        duration = request.form['duration']
        difficulty = request.form['difficulty']
        featured = 1 if request.form.get('featured') == 'on' else 0
        tour_type = request.form['tour_type']
        available_seats = int(request.form.get('available_seats', 0))
        group_start_date = request.form.get('group_start_date')
        
        image_file = request.files.get('image')
        image_blob = None
        if image_file and image_file.filename != '':
            image_blob = image_file.read()
            
        conn.execute('''
            INSERT INTO tours (name, description, price, region, duration, difficulty, featured, tour_type, available_seats, group_start_date, image) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (name, description, price, region, duration, difficulty, featured, tour_type, available_seats, group_start_date, image_blob))
        conn.commit()
        flash('New tour added successfully!', 'success')
        return redirect(url_for('admin_tours'))

    tours = conn.execute('SELECT * FROM tours ORDER BY created_at DESC').fetchall()
    conn.close()
    return render_template('admin/tours.html', tours=tours)

@app.route('/admin_edit_tour/<int:tour_id>', methods=['GET', 'POST'])
@require_admin
def admin_edit_tour(tour_id):
    conn = get_db_connection()
    tour = conn.execute('SELECT * FROM tours WHERE id = ?', (tour_id,)).fetchone()
    
    if tour is None:
        conn.close()
        flash('Tour not found.', 'error')
        return redirect(url_for('admin_tours'))
        
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        price = float(request.form['price'])
        region = request.form['region']
        duration = request.form['duration']
        difficulty = request.form['difficulty']
        featured = 1 if request.form.get('featured') == 'on' else 0
        tour_type = request.form['tour_type']
        available_seats = int(request.form.get('available_seats', 0))
        group_start_date = request.form.get('group_start_date')
        
        image_file = request.files.get('image')
        image_blob = None
        
        update_fields = [name, description, price, region, duration, difficulty, featured, tour_type, available_seats, group_start_date]
        update_query = '''
            UPDATE tours SET 
                name = ?, description = ?, price = ?, region = ?, duration = ?, 
                difficulty = ?, featured = ?, tour_type = ?, available_seats = ?, 
                group_start_date = ?
        '''
        
        if image_file and image_file.filename != '':
            image_blob = image_file.read()
            update_query += ', image = ?'
            update_fields.append(image_blob)
            
        update_query += ' WHERE id = ?'
        update_fields.append(tour_id)
        
        conn.execute(update_query, tuple(update_fields))
        conn.commit()
        conn.close()
        flash('Tour updated successfully!', 'success')
        return redirect(url_for('admin_tours'))
        
    conn.close()
    return render_template('admin/edit_tour.html', tour=tour)

@app.route('/admin_delete_tour/<int:tour_id>')
@require_admin
def admin_delete_tour(tour_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM tours WHERE id = ?', (tour_id,))
    conn.commit()
    conn.close()
    flash('Tour deleted successfully.', 'success')
    return redirect(url_for('admin_tours'))

@app.route('/admin_bookings')
@require_admin
def admin_bookings():
    conn = get_db_connection()
    bookings = conn.execute('''
        SELECT b.*, u.name as user_name, u.email as user_email, t.name as tour_name 
        FROM bookings b
        JOIN users u ON b.user_id = u.id
        JOIN tours t ON b.tour_id = t.id
        ORDER BY b.created_at DESC
    ''').fetchall()
    conn.close()
    return render_template('admin/bookings.html', bookings=bookings)

@app.route('/admin_confirm_booking/<int:booking_id>')
@require_admin
def admin_confirm_booking(booking_id):
    conn = get_db_connection()
    conn.execute('UPDATE bookings SET status = "confirmed", admin_confirmed = 1 WHERE id = ?', (booking_id,))
    conn.commit()
    conn.close()
    flash('Booking confirmed.', 'success')
    return redirect(url_for('admin_bookings'))

@app.route('/admin_cancel_booking/<int:booking_id>')
@require_admin
def admin_cancel_booking(booking_id):
    conn = get_db_connection()
    booking = conn.execute('SELECT * FROM bookings WHERE id = ?', (booking_id,)).fetchone()
    
    if booking:
        # Refund seats for group tours
        tour = conn.execute('SELECT id, available_seats, tour_type FROM tours WHERE id = ?', (booking['tour_id'],)).fetchone()
        if tour and tour['tour_type'] == 'group':
            new_seats = tour['available_seats'] + booking['participants']
            conn.execute('UPDATE tours SET available_seats = ? WHERE id = ?', (new_seats, tour['id']))
            
        conn.execute('UPDATE bookings SET status = "cancelled", admin_confirmed = 0 WHERE id = ?', (booking_id,))
        conn.commit()
        flash('Booking cancelled.', 'info')
    else:
        flash('Booking not found.', 'error')
        
    conn.close()
    return redirect(url_for('admin_bookings'))

@app.route('/admin_tickets', methods=['GET', 'POST'])
@require_admin
def admin_tickets():
    conn = get_db_connection()
    
    if request.method == 'POST':
        ticket_id = request.form['ticket_id']
        response = request.form['response']
        
        conn.execute('UPDATE support_tickets SET admin_response = ?, status = "closed" WHERE id = ?', 
                     (response, ticket_id))
        conn.commit()
        flash(f'Ticket #{ticket_id} closed and response sent.', 'success')
        return redirect(url_for('admin_tickets'))
        
    tickets = conn.execute('''
        SELECT s.*, u.name as user_name, u.email as user_email 
        FROM support_tickets s
        JOIN users u ON s.user_id = u.id
        ORDER BY s.created_at DESC
    ''').fetchall()
    conn.close()
    return render_template('admin/tickets.html', tickets=tickets)

@app.route('/admin_users')
@require_admin
def admin_users():
    conn = get_db_connection()
    users = conn.execute('SELECT * FROM users ORDER BY created_at DESC').fetchall()
    conn.close()
    return render_template('admin/users.html', users=users)

@app.route('/admin_delete_user/<int:user_id>')
@require_admin
def admin_delete_user(user_id):
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    
    if user and user['role'] != 'admin':
        conn.execute('DELETE FROM users WHERE id = ?', (user_id,))
        conn.commit()
        flash(f"User {user['name']} deleted successfully.", 'success')
    else:
        flash('Cannot delete admin user or user not found.', 'error')
        
    conn.close()
    return redirect(url_for('admin_users'))

@app.route('/download_invoice/<int:booking_id>')
def download_invoice(booking_id):
    if 'user_id' not in session:
        flash('Please log in to download invoices.', 'warning')
        return redirect(url_for('login'))
        
    user_id = session['user_id']
    conn = get_db_connection()
    booking = conn.execute('''
        SELECT b.*, u.name as user_name, u.email as user_email, u.address as user_address, u.phone as user_phone
        FROM bookings b
        JOIN users u ON b.user_id = u.id
        WHERE b.id = ? AND b.user_id = ?
    ''', (booking_id, user_id)).fetchone()
    conn.close()
    
    if booking is None:
        flash('Invoice not found or you do not have permission.', 'error')
        return redirect(url_for('profile'))
        
    # Generate HTML content for the invoice
    # This is the only place where render_template_string is used to generate the PDF content
    invoice_html = render_template_string("""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <title>Invoice - Booking #{{ booking.id }}</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 0; padding: 0; }
                .invoice-container { width: 80%; margin: 50px auto; border: 1px solid #ccc; padding: 20px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }
                .header { text-align: center; margin-bottom: 30px; }
                .header h1 { color: #2c3e50; }
                .details { margin-bottom: 30px; display: flex; justify-content: space-between; }
                .details div { width: 45%; }
                .details h3 { border-bottom: 1px solid #eee; padding-bottom: 5px; margin-bottom: 10px; color: #3498db; }
                table { width: 100%; border-collapse: collapse; margin-bottom: 30px; }
                th, td { border: 1px solid #ddd; padding: 10px; text-align: left; }
                th { background-color: #f2f2f2; }
                .total-row td { font-weight: bold; background-color: #eaf2f8; }
                .footer { text-align: center; margin-top: 50px; font-size: 0.9em; color: #777; }
            </style>
        </head>
        <body>
            <div class="invoice-container">
                <div class="header">
                    <h1>North Trips and Travel</h1>
                    <p>Invoice for Tour Booking</p>
                </div>
                
                <div class="details">
                    <div>
                        <h3>Invoice Details</h3>
                        <p><strong>Invoice ID:</strong> INV-{{ booking.id }}-{{ booking.created_at | replace(' ', '-') | replace(':', '-') }}</p>
                        <p><strong>Date:</strong> {{ booking.created_at.split(' ')[0] }}</p>
                        <p><strong>Status:</strong> {{ booking.status | capitalize }}</p>
                    </div>
                    <div>
                        <h3>Customer Details</h3>
                        <p><strong>Name:</strong> {{ booking.user_name }}</p>
                        <p><strong>Email:</strong> {{ booking.user_email }}</p>
                        <p><strong>Phone:</strong> {{ booking.user_phone or 'N/A' }}</p>
                        <p><strong>Address:</strong> {{ booking.user_address or 'N/A' }}</p>
                    </div>
                </div>
                
                <table>
                    <thead>
                        <tr>
                            <th>Description</th>
                            <th>Tour Date</th>
                            <th>Participants</th>
                            <th>Unit Price (PKR)</th>
                            <th>Total (PKR)</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td>{{ booking.tour_name }}</td>
                            <td>{{ booking.tour_date }}</td>
                            <td>{{ booking.participants }}</td>
                            <td>{{ "{:,.0f}".format(booking.total_price / booking.participants) }}</td>
                            <td>{{ "{:,.0f}".format(booking.total_price) }}</td>
                        </tr>
                    </tbody>
                    <tfoot>
                        <tr class="total-row">
                            <td colspan="4" style="text-align: right;">GRAND TOTAL</td>
                            <td>{{ "{:,.0f}".format(booking.total_price) }} PKR</td>
                        </tr>
                    </tfoot>
                </table>
                
                <div class="footer">
                    <p>Thank you for booking with North Trips and Travel!</p>
                    <p>Contact us at admin@northtripsandtravel.com for support.</p>
                </div>
            </div>
        </body>
        </html>
    """, booking=booking)

    # Use pdfkit to convert HTML to PDF
    try:
        pdf = pdfkit.from_string(invoice_html, False)
        
        # Send the PDF file
        return send_file(
            BytesIO(pdf),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'invoice_booking_{booking_id}.pdf'
        )
    except Exception as e:
        flash(f'Could not generate PDF invoice. Ensure wkhtmltopdf is installed. Error: {e}', 'error')
        return redirect(url_for('profile'))

# --- Main Run Block ---
if __name__ == '__main__':
    app.run(debug=True)

