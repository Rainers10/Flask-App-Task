from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3
import os
import uuid
from werkzeug.utils import secure_filename
from config import Config
import csv
from io import StringIO
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

app = Flask(__name__)
app.config.from_object(Config)

def get_db_connection():
    conn = sqlite3.connect('instance/database.db')
    conn.row_factory = sqlite3.Row
    return conn

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def generate_random_filename(filename):
    ext = filename.rsplit('.', 1)[1].lower()
    random_id = uuid.uuid4().hex
    return f"{random_id}.{ext}"

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

        if user is None:
            flash('User not found')
            return redirect(url_for('login'))

        if user['password'] == password:
            session['username'] = username
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid password')
            return redirect(url_for('login'))

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
@app.route('/add_fuel_entry/<int:car_id>', methods=['GET', 'POST'])
def add_fuel_entry(car_id=None):
    if 'username' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    user = conn.execute('SELECT id FROM users WHERE username = ?', (session['username'],)).fetchone()

    if request.method == 'POST':
        car_id = car_id or request.form.get('car_id')
        mileage = request.form['mileage']
        fuel_amount_liters = request.form['fuel_amount_liters']

        conn.execute('''
            INSERT INTO fuel_entries (car_id, mileage, fuel_amount_liters)
            VALUES (?, ?, ?)
        ''', (car_id, mileage, fuel_amount_liters))
        conn.commit()
        conn.close()

        flash('Fuel entry added successfully!')
        return redirect(url_for('car_details', car_id=car_id))

    car = None
    if car_id:
        car = conn.execute('SELECT * FROM cars WHERE id = ?', (car_id,)).fetchone()

    cars = conn.execute('SELECT * FROM cars WHERE user_id = ?', (user['id'],)).fetchall()
    conn.close()

    return render_template('add_fuel_entry.html', cars=cars, selected_car=car)

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

@app.route('/car/<int:car_id>/download_csv')
def download_csv(car_id):
    if 'username' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    car = conn.execute('SELECT * FROM cars WHERE id = ?', (car_id,)).fetchone()
    fuel_entries = conn.execute('''
        SELECT * FROM fuel_entries WHERE car_id = ? ORDER BY mileage
    ''', (car_id,)).fetchall()
    conn.close()

    if not car:
        flash('Car not found', 'danger')
        return redirect(url_for('dashboard'))

    output = StringIO()
    writer = csv.writer(output)

    writer.writerow(['Mileage (km)', 'Fuel (L)', 'Economy (km/L)'])

    for i in range(1, len(fuel_entries)):
        mileage = fuel_entries[i]["mileage"]  # Use dictionary-style access
        fuel = fuel_entries[i - 1]["fuel_amount_liters"]  # Use dictionary-style access
        economy = (fuel_entries[i]["mileage"] - fuel_entries[i - 1]["mileage"]) / fuel_entries[i - 1]["fuel_amount_liters"]
        writer.writerow([mileage, fuel, round(economy, 2)])

    output.seek(0)
    response = app.response_class(
        output,
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename={car["make"]}_{car["model"]}_fuel_data.csv'}
    )

    return response


    if 'username' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    user = conn.execute('SELECT id FROM users WHERE username = ?', (session['username'],)).fetchone()
    cars = conn.execute('SELECT * FROM cars WHERE user_id = ?', (user['id'],)).fetchall()

    selected_car_ids = []  # Initialize as an empty list
    car_data = []  # Initialize as an empty list

    if request.method == 'POST':
        selected_car_ids = request.form.getlist('car_ids')  # Get selected car IDs from the form
        selected_cars = [car for car in cars if str(car['id']) in selected_car_ids]

        # Fetch fuel entries for selected cars
        for car in selected_cars:
            fuel_entries = conn.execute('''
                SELECT * FROM fuel_entries WHERE car_id = ? ORDER BY mileage
            ''', (car['id'],)).fetchall()
            car_data.append({
                'car': car,
                'fuel_entries': fuel_entries
            })

    conn.close()
    return render_template('compare_cars.html', cars=cars, car_data=car_data, selected_car_ids=selected_car_ids)


@app.route('/compare_cars', methods=['GET', 'POST'])
def compare_cars():
    if 'username' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    user = conn.execute('SELECT id FROM users WHERE username = ?', (session['username'],)).fetchone()
    cars = conn.execute('SELECT * FROM cars WHERE user_id = ?', (user['id'],)).fetchall()

    selected_car_ids = request.form.getlist('car_ids') if request.method == 'POST' else []
    selected_cars = [car for car in cars if str(car['id']) in selected_car_ids]

    car_data = []
    for car in selected_cars:
        fuel_entries = conn.execute('''
            SELECT * FROM fuel_entries WHERE car_id = ? ORDER BY mileage
        ''', (car['id'],)).fetchall()
        car_data.append({
            'car': car,
            'fuel_entries': fuel_entries
        })

    conn.close()

    car_economy = []
    for car in car_data:
        if len(car['fuel_entries']) >= 2:
            economy_values = []
            for i in range(1, len(car['fuel_entries'])):
                km = car['fuel_entries'][i]['mileage'] - car['fuel_entries'][i - 1]['mileage']
                liters = car['fuel_entries'][i - 1]['fuel_amount_liters']
                economy_values.append(km / liters)
            avg_economy = sum(economy_values) / len(economy_values)
            car_economy.append({
                'car': car['car'],
                'avg_economy': avg_economy
            })

    car_economy.sort(key=lambda x: x['avg_economy'], reverse=True)

    if car_economy:
        car_names = [f"{car['car']['make']} {car['car']['model']}" for car in car_economy]
        avg_economy_values = [car['avg_economy'] for car in car_economy]

        plt.figure(figsize=(6, 4))
        plt.barh(car_names, avg_economy_values, color='skyblue')
        plt.xlabel('Average Fuel Economy (km/L)')
        plt.title('Average Fuel Economy by Car')
        plt.gca().invert_yaxis()

        chart_path = os.path.join(app.static_folder, 'images', 'fuel_economy_chart.png')
        plt.savefig(chart_path, bbox_inches='tight')
        plt.close()
    else:
        chart_path = None

    return render_template('compare_cars.html', cars=cars, selected_car_ids=selected_car_ids, chart_path=chart_path)

if __name__ == '__main__':
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    app.run(debug=True)
