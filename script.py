import sqlite3
import threading
import time
from datetime import datetime
from flask import Flask, request, jsonify
import requests
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

#Инициализация базы данных
def init_db():
    conn = sqlite3.connect('weather.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id),
            UNIQUE(user_id, name)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS weather_forecasts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            city_id INTEGER NOT NULL,
            timestamp INTEGER NOT NULL,
            temperature REAL,
            windspeed REAL,
            pressure REAL,
            humidity REAL,
            precipitation REAL,
            forecast_time TEXT,
            FOREIGN KEY (city_id) REFERENCES cities (id),
            UNIQUE(city_id, forecast_time)
        )
    ''')
    conn.commit()
    conn.close()
    print("Database initialised")

init_db()

weather_cache = {}
cache_lock = threading.Lock()

#Получение погоды
def get_weather(lat, lon):
    cache_key = f"{lat:.4f},{lon:.4f}"
    with cache_lock:
        if cache_key in weather_cache:
            cached_data, cache_time = weather_cache[cache_key]
            if time.time() - cache_time < 300:
                return cached_data
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current_weather": True,
        "hourly": "temperature_2m,relativehumidity_2m,windspeed_10m,pressure_msl,precipitation",
        "timezone": "auto"
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        current = data.get('current_weather', {})
        hourly = data.get('hourly', {})
        current_time = datetime.now().strftime("%Y-%m-%dT%H:00")
        try:
    	    time_index = hourly['time'].index(current_time)
        except (ValueError, KeyError):
            time_index = 0
        result = {
            'temperature': current.get('temperature'),
            'windspeed': current.get('windspeed'),
            'pressure': hourly.get('pressure_msl', [None])[time_index] if hourly.get('pressure_msl') else None,
            'humidity': hourly.get('relativehumidity_2m', [None])[time_index] if hourly.get('relativehumidity_2m') else None,
            'precipitation': hourly.get('precipitation', [None])[time_index] if hourly.get('precipitation') else None
        }
        with cache_lock:
            weather_cache[cache_key] = (result, time.time())
        return result
    except Exception as e:
        print(f"Error getting weather: {e}")
        return None

#Обновление прогноза
def update_forecasts():
    conn = sqlite3.connect('weather.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, name, latitude, longitude FROM cities')
    cities = cursor.fetchall()
    for city_id, name, lat, lon in cities:
        weather_data = get_weather(lat, lon)
        if weather_data:
            today = datetime.now().strftime("%Y-%m-%d")
            cursor.execute('''
                INSERT OR REPLACE INTO weather_forecasts 
                (city_id, timestamp, temperature, windspeed, pressure, humidity, precipitation, forecast_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                city_id,
                int(time.time()),
                weather_data.get('temperature'),
                weather_data.get('windspeed'),
                weather_data.get('pressure'),
                weather_data.get('humidity'),
                weather_data.get('precipitation'),
                today
            ))
    conn.commit()
    conn.close()
    print("Forecasts updated")

#Фоновое обновление
def background_updater():
    print("Background forecast update started")
    while True:
        time.sleep(900)  # 15 минут
        update_forecasts()

update_thread = threading.Thread(target=background_updater, daemon=True)
update_thread.start()

#Метод 1
@app.route('/weather/current', methods=['GET'])
def get_current_weather():
    lat = request.args.get('latitude')
    lon = request.args.get('longitude')
    if not lat or not lon:
        return jsonify({'error': 'latitude and longitude are required'}), 400
    try:
        lat = float(lat)
        lon = float(lon)
    except ValueError:
        return jsonify({'error': 'Invalid coordinates'}), 400
    weather = get_weather(lat, lon)
    if weather:
        return jsonify(weather)
    else:
        return jsonify({'error': 'Failed to get weather'}), 500

#Метод 2
@app.route('/cities', methods=['POST'])
def add_city():
    data = request.get_json()
    user_id = data.get('user_id')
    name = data.get('name')
    latitude = data.get('latitude')
    longitude = data.get('longitude')
    if not all([user_id, name, latitude, longitude]):
        return jsonify({'error': 'user_id, name, latitude and longitude are required'}), 400
    conn = sqlite3.connect('weather.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM users WHERE id = ?', (user_id,))
    if not cursor.fetchone():
        conn.close()
        return jsonify({'error': 'User not found'}), 404
    try:
        cursor.execute('''
            INSERT INTO cities (user_id, name, latitude, longitude)
            VALUES (?, ?, ?, ?)
        ''', (user_id, name, float(latitude), float(longitude)))
        conn.commit()
        city_id = cursor.lastrowid
        weather_data = get_weather(float(latitude), float(longitude))
        if weather_data:
            today = datetime.now().strftime("%Y-%m-%d")
            cursor.execute('''
                INSERT OR REPLACE INTO weather_forecasts 
                (city_id, timestamp, temperature, windspeed, pressure, humidity, precipitation, forecast_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                city_id,
                int(time.time()),
                weather_data.get('temperature'),
                weather_data.get('windspeed'),
                weather_data.get('pressure'),
                weather_data.get('humidity'),
                weather_data.get('precipitation'),
                today
            ))
            conn.commit()
        conn.close()
        return jsonify({'message': 'City added successfully', 'city_id': city_id}), 201
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({'error': 'City already exists for this user'}), 400

#Метод 3
@app.route('/cities', methods=['GET'])
def get_cities():
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'error': 'user_id is required'}), 400
    conn = sqlite3.connect('weather.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, name, latitude, longitude 
        FROM cities 
        WHERE user_id = ?
    ''', (user_id,))
    cities = cursor.fetchall()
    conn.close()
    result = [{'id': c[0], 'name': c[1], 'latitude': c[2], 'longitude': c[3]} for c in cities]
    return jsonify(result)

#Метод 4
@app.route('/weather/forecast', methods=['GET'])
def get_forecast():
    user_id = request.args.get('user_id')
    city_name = request.args.get('city_name')
    time_str = request.args.get('time')
    params_str = request.args.get('params', '')
    if not all([user_id, city_name, time_str]):
        return jsonify({'error': 'user_id, city_name and time are required'}), 400
    try:
        datetime.strptime(time_str, "%H:%M")
    except ValueError:
        return jsonify({'error': 'Invalid time format. Use HH:MM'}), 400
    if params_str:
        params = [p.strip() for p in params_str.split(',') if p.strip()]
    else:
        params = []
    conn = sqlite3.connect('weather.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT c.id, c.name, c.latitude, c.longitude 
        FROM cities c
        WHERE c.user_id = ? AND c.name = ?
    ''', (user_id, city_name))
    city = cursor.fetchone()
    if not city:
        conn.close()
        return jsonify({'error': 'City not found for this user'}), 404
    today = datetime.now().strftime("%Y-%m-%d")
    cursor.execute('''
        SELECT temperature, windspeed, pressure, humidity, precipitation
        FROM weather_forecasts
        WHERE city_id = ? AND forecast_time = ?
    ''', (city[0], today))
    forecast = cursor.fetchone()
    conn.close()
    if not forecast:
        return jsonify({'error': 'Weather forecast not available for today'}), 404
    param_mapping = {
        'temperature': forecast[0],
        'windspeed': forecast[1],
        'pressure': forecast[2],
        'humidity': forecast[3],
        'precipitation': forecast[4]
    }
    if not params:
        result = param_mapping.copy()
    else:
        result = {}
        for param in params:
            if param in param_mapping:
                result[param] = param_mapping[param]
    result['time'] = time_str
    result['city'] = city_name
    return jsonify(result)

#Регистрация пользователя
@app.route('/register', methods=['POST'])
def register_user():
    data = request.get_json()
    username = data.get('username')
    if not username:
        return jsonify({'error': 'username is required'}), 400
    conn = sqlite3.connect('weather.db')
    cursor = conn.cursor()
    try:
        cursor.execute('INSERT INTO users (username) VALUES (?)', (username,))
        conn.commit()
        user_id = cursor.lastrowid
        conn.close()
        return jsonify({'user_id': user_id, 'username': username}), 201
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({'error': 'Username already exists'}), 400

#Проверка работоспособности сервера
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'ok'}), 200

if __name__ == '__main__':
    print("Server is available at http://127.0.0.1:8000")
    app.run(host='127.0.0.1', port=8000, debug=False, threaded=True)