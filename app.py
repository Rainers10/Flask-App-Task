from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3
import os
import uuid
from werkzeug.utils import secure_filename
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def get_db_connection():
    conn = sqlite3.connect('instance/database.db')
    conn.row_factory = sqlite3.Row
    return conn

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def generate_random_filename(filename):
    ext = filename.rsplit('.', 1)[1].lower()
    random_id = uuid.uuid4().hex
    random_filename = f"{random_id}.{ext}"
    return random_filename

@app.route('/')
def index():
    if 'username' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()
        if user and user['password'] == password:
            session['username'] = username
            return redirect(url_for('dashboard'))
        flash('Invalid username or password')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db_connection()
        try:
            conn.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
            conn.commit()
        except sqlite3.IntegrityError:
            flash('Username already exists')
            return redirect(url_for('register'))
        conn.close()
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    user = conn.execute('SELECT id FROM users WHERE username = ?', (session['username'],)).fetchone()
    cars = conn.execute('SELECT * FROM cars WHERE user_id = ?', (user['id'],)).fetchall()
    conn.close()

    return render_template('dashboard.html', username=session['username'], cars=cars)

@app.route('/register_car', methods=['GET', 'POST'])
def register_car():
    if 'username' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        make = request.form['make']
        model = request.form['model']
        year = request.form['year']
        image = request.files['image']

        image_path = None
        if image and allowed_file(image.filename):
            filename = secure_filename(image.filename)
            random_filename = generate_random_filename(filename)
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], random_filename)
            image.save(image_path)
            image_path = random_filename

        conn = get_db_connection()
        user = conn.execute('SELECT id FROM users WHERE username = ?', (session['username'],)).fetchone()
        conn.execute('''
            INSERT INTO cars (user_id, make, model, year, image_path)
            VALUES (?, ?, ?, ?, ?)
        ''', (user['id'], make, model, year, image_path))
        conn.commit()
        conn.close()

        flash('Car registered successfully!')
        return redirect(url_for('dashboard'))

    return render_template('register_car.html')

@app.route('/add_fuel_entry', methods=['GET', 'POST'])
def add_fuel_entry():
    if 'username' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    user = conn.execute('SELECT id FROM users WHERE username = ?', (session['username'],)).fetchone()
    cars = conn.execute('SELECT * FROM cars WHERE user_id = ?', (user['id'],)).fetchall()

    if request.method == 'POST':
        car_id = request.form['car_id']
        mileage = request.form['mileage']
        fuel_amount_liters = request.form['fuel_amount_liters']

        conn.execute('''
            INSERT INTO fuel_entries (car_id, mileage, fuel_amount_liters)
            VALUES (?, ?, ?)
        ''', (car_id, mileage, fuel_amount_liters))
        conn.commit()
        conn.close()

        flash('Fuel entry added successfully!')
        return redirect(url_for('dashboard'))

    conn.close()
    return render_template('add_fuel_entry.html', cars=cars)

@app.route('/car/<int:car_id>')
def car_details(car_id):
    if 'username' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    car = conn.execute('SELECT * FROM cars WHERE id = ?', (car_id,)).fetchone()
    fuel_entries = conn.execute('''
        SELECT * FROM fuel_entries WHERE car_id = ? ORDER BY mileage
    ''', (car_id,)).fetchall()
    conn.close()

    return render_template('car_details.html', car=car, fuel_entries=fuel_entries)

@app.route('/car/<int:entry_id>/edit_fuel_entry', methods=['GET', 'POST'])
def edit_fuel_entry(entry_id):
    if 'username' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    entry = conn.execute('SELECT * FROM fuel_entries WHERE id = ?', (entry_id,)).fetchone()

    if request.method == 'POST':
        mileage = request.form['mileage']
        fuel_amount_liters = request.form['fuel_amount_liters']

        conn.execute('''
            UPDATE fuel_entries
            SET mileage = ?, fuel_amount_liters = ?
            WHERE id = ?
        ''', (mileage, fuel_amount_liters, entry_id))
        conn.commit()
        conn.close()

        flash('Fuel entry updated successfully!')
        return redirect(url_for('car_details', car_id=entry['car_id']))

    conn.close()
    return render_template('edit_fuel_entry.html', entry=entry)

@app.route('/car/<int:entry_id>/delete_fuel_entry', methods=['POST'])
def delete_fuel_entry(entry_id):
    if 'username' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    entry = conn.execute('SELECT * FROM fuel_entries WHERE id = ?', (entry_id,)).fetchone()
    conn.execute('DELETE FROM fuel_entries WHERE id = ?', (entry_id,))
    conn.commit()
    conn.close()

    flash('Fuel entry deleted successfully!')
    return redirect(url_for('car_details', car_id=entry['car_id']))

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('index'))

if __name__ == '__main__':
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    app.run(debug=True)
