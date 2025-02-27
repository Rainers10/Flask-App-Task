import sqlite3
import random
from datetime import datetime, timedelta

def init_main_db():
    conn = sqlite3.connect('instance/database.db')
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cars (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            make TEXT NOT NULL,
            model TEXT NOT NULL,
            year INTEGER NOT NULL,
            image_path TEXT,  -- New column for image path
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS fuel_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            car_id INTEGER NOT NULL,
            mileage INTEGER NOT NULL,
            fuel_amount_liters REAL NOT NULL,
            entry_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (car_id) REFERENCES cars (id)
        )
    ''')

    try:
        cursor.execute('''
            INSERT INTO users (username, password)
            VALUES (?, ?)
        ''', ('testuser', 'testpassword'))  # Username: test, Password: test
        print("Test user created: username='testuser', password='testpassword'")
    except sqlite3.IntegrityError:
        print("Test user already exists.")

    conn.commit()
    conn.close()

def init_example_db():

    conn = sqlite3.connect('instance/example_cars.db')
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cars (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            make TEXT NOT NULL,
            model TEXT NOT NULL,
            year INTEGER NOT NULL,
            image_path TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS fuel_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            car_id INTEGER NOT NULL,
            mileage INTEGER NOT NULL,
            fuel_amount_liters REAL NOT NULL,
            entry_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (car_id) REFERENCES cars (id)
        )
    ''')

    example_cars = [
        {'make': 'Honda', 'model': 'Civic', 'year': 2020, 'image_path': 'images/Honda_CIVV.png'},
        {'make': 'Toyota', 'model': 'Corolla', 'year': 2018, 'image_path': 'images/Toyota_Corr.png'},
        {'make': 'Ford', 'model': 'Mustang', 'year': 2021, 'image_path': 'images/Ford_Must.png'}
    ]

    for car in example_cars:
        cursor.execute('''
            INSERT INTO cars (make, model, year, image_path)
            VALUES (?, ?, ?, ?)
        ''', (car['make'], car['model'], car['year'], car['image_path']))
        print(f"Car added: {car['make']} {car['model']} ({car['year']})")

    cursor.execute('SELECT id FROM cars')
    car_ids = [row[0] for row in cursor.fetchall()]

    for car_id in car_ids:
        mileage = 10000
        fuel_amount = 40
        entry_date = datetime.now() - timedelta(days=30)

        for _ in range(10):

            mileage += random.randint(400, 600)

            fuel_amount += random.uniform(4, 6)

            entry_date += timedelta(days=random.randint(2, 4))

            cursor.execute('''
                INSERT INTO fuel_entries (car_id, mileage, fuel_amount_liters, entry_date)
                VALUES (?, ?, ?, ?)
            ''', (car_id, mileage, fuel_amount, entry_date.strftime('%Y-%m-%d %H:%M:%S')))

        print(f"Added 10 fuel entries for car ID {car_id}")

    conn.commit()
    conn.close()

if __name__ == '__main__':
    print("Initializing main database...")
    init_main_db()

    print("\nInitializing example database...")
    init_example_db()

    print("\nDatabase initialization complete.")
