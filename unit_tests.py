import unittest
import time
import requests
import sys
import random

class WeatherAPITestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base_url = "http://127.0.0.1:8000"
        print("\nChecking connection to the server")
        max_retries = 5
        for i in range(max_retries):
            try:
                response = requests.get(f"{cls.base_url}/health", timeout=5)
                if response.status_code == 200:
                    print("Server is running successfully")
                    return
            except requests.exceptions.RequestException as e:
                print(f"Attempt {i + 1}/{max_retries}: server is not responding")
                time.sleep(2)
        print("ERROR: Server isn't running or isn't responding")
        print("Please launch the server in a separate terminal:")
        print("python3 script.py")
        sys.exit(1)

    #Подготовка перед каждым тестом
    def setUp(self):
        random_suffix = random.randint(10000, 99999)
        timestamp = int(time.time())
        username = f'test_user_{timestamp}_{random_suffix}'
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                response = requests.post(
                    f"{self.base_url}/register",
                    json={'username': username},
                    timeout=10
                )
                if response.status_code == 201:
                    self.user_data = response.json()
                    self.user_id = self.user_data['user_id']
                    self.username = self.user_data['username']
                    break
                elif response.status_code == 400 and "already exists" in response.text:
                    username = f'test_user_{timestamp}_{random_suffix}_{attempt}'
                    continue
                else:
                    self.fail(f"Failed to register user: {response.status_code} - {response.text}")
            except requests.exceptions.RequestException as e:
                if attempt == max_attempts - 1:
                    self.fail(f"Failed to register user after {max_attempts} attempts: {e}")
                time.sleep(1)
        else:
            self.fail("Failed to register user")
        for attempt in range(max_attempts):
            try:
                response = requests.post(
                    f"{self.base_url}/cities",
                    json={
                        'user_id': self.user_id,
                        'name': 'Tomsk',
                        'latitude': 56.4846,
                        'longitude': 84.9479
                    },
                    timeout=10
                )
                if response.status_code == 201:
                    print(f"\nTest is running for the user {self.username} (ID: {self.user_id})")
                    return
                elif response.status_code == 400 and "already exists" in response.text:
                    city_name = f'Tomsk_{random_suffix}'
                    response = requests.post(
                        f"{self.base_url}/cities",
                        json={
                            'user_id': self.user_id,
                            'name': city_name,
                            'latitude': 56.4846,
                            'longitude': 84.9479
                        },
                        timeout=10
                    )
                    if response.status_code == 201:
                        self.city_name = city_name
                        print(
                            f"\nTest is running for the user {self.username} (ID: {self.user_id}) with city {city_name}")
                        return
                else:
                    self.fail(f"Failed to add city: {response.status_code} - {response.text}")
            except requests.exceptions.RequestException as e:
                if attempt == max_attempts - 1:
                    self.fail(f"Failed to add city after {max_attempts} attempts: {e}")
                time.sleep(1)
        self.fail("Failed to add city")

    #Тест работоспособности сервера
    def test_health(self):
        response = requests.get(f"{self.base_url}/health", timeout=5)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'ok')

    #Тест регистрации пользователя
    def test_register_user(self):
        username = f'new_user_{int(time.time())}_{random.randint(1000, 9999)}'
        response = requests.post(
            f"{self.base_url}/register",
            json={'username': username},
            timeout=10
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertIn('user_id', data)
        self.assertEqual(data['username'], username)

    #Тест регистрации дублирующегося пользователя
    def test_register_duplicate_user(self):
        username = f'dup_user_{int(time.time())}_{random.randint(1000, 9999)}'
        response = requests.post(
            f"{self.base_url}/register",
            json={'username': username},
            timeout=10
        )
        self.assertEqual(response.status_code, 201)
        response = requests.post(
            f"{self.base_url}/register",
            json={'username': username},
            timeout=10
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('error', data)

    #Тест получения погоды
    def test_current_weather(self):
        response = requests.get(
            f"{self.base_url}/weather/current?latitude=56.4846&longitude=84.9479",
            timeout=15
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('temperature', data)
        self.assertIn('windspeed', data)
        self.assertIn('pressure', data)

    #Тест получения погоды по неправильным координатам
    def test_current_weather_invalid_coords(self):
        response = requests.get(
            f"{self.base_url}/weather/current?latitude=abc&longitude=def",
            timeout=10
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('error', data)

    #Тест добавления города
    def test_add_city(self):
        city_name = f'City_{int(time.time())}_{random.randint(1000, 9999)}'
        response = requests.post(
            f"{self.base_url}/cities",
            json={
                'user_id': self.user_id,
                'name': city_name,
                'latitude': 59.9343,
                'longitude': 30.3351
            },
            timeout=15
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertIn('city_id', data)

    #Тест добавления дублирующегося города
    def test_add_city_duplicate(self):
        city_name = f'DupCity_{int(time.time())}_{random.randint(1000, 9999)}'
        response = requests.post(
            f"{self.base_url}/cities",
            json={
                'user_id': self.user_id,
                'name': city_name,
                'latitude': 55.7558,
                'longitude': 37.6173
            },
            timeout=15
        )
        self.assertEqual(response.status_code, 201)
        response = requests.post(
            f"{self.base_url}/cities",
            json={
                'user_id': self.user_id,
                'name': city_name,
                'latitude': 55.7558,
                'longitude': 37.6173
            },
            timeout=10
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('error', data)

    #Тест получения списка городов
    def test_get_cities(self):
        response = requests.get(
            f"{self.base_url}/cities?user_id={self.user_id}",
            timeout=10
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0)

    #Тест получения списка городов без указания пользователя
    def test_get_cities_no_user(self):
        response = requests.get(f"{self.base_url}/cities", timeout=10)
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('error', data)

    #Тест получения прогноза
    def test_forecast(self):
        time.sleep(5)
        response = requests.get(
            f"{self.base_url}/cities?user_id={self.user_id}",
            timeout=10
        )
        self.assertEqual(response.status_code, 200)
        cities = response.json()
        self.assertGreater(len(cities), 0)
        city_name = cities[0]['name']
        response = requests.get(
            f"{self.base_url}/weather/forecast?user_id={self.user_id}&city_name={city_name}&time=12:00&params=temperature,windspeed",
            timeout=15
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('temperature', data)
        self.assertIn('windspeed', data)
        self.assertIn('time', data)
        self.assertEqual(data['city'], city_name)

    #Тест получения прогноза по неправильному времени
    def test_forecast_invalid_time(self):
        response = requests.get(
            f"{self.base_url}/cities?user_id={self.user_id}",
            timeout=10
        )
        self.assertEqual(response.status_code, 200)
        cities = response.json()
        self.assertGreater(len(cities), 0)
        city_name = cities[0]['name']
        response = requests.get(
            f"{self.base_url}/weather/forecast?user_id={self.user_id}&city_name={city_name}&time=25:00&params=temperature",
            timeout=10
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('error', data)

    #Тест получения прогноза для неправильного города
    def test_forecast_invalid_city(self):
        response = requests.get(
            f"{self.base_url}/weather/forecast?user_id={self.user_id}&city_name=InvalidCity&time=12:00&params=temperature",
            timeout=10
        )
        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertIn('error', data)

    #Тест получения прогноза без указания параметров
    def test_forecast_no_params(self):
        time.sleep(3)
        response = requests.get(
            f"{self.base_url}/cities?user_id={self.user_id}",
            timeout=10
        )
        self.assertEqual(response.status_code, 200)
        cities = response.json()
        self.assertGreater(len(cities), 0)
        city_name = cities[0]['name']
        response = requests.get(
            f"{self.base_url}/weather/forecast?user_id={self.user_id}&city_name={city_name}&time=12:00",
            timeout=15
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        expected_params = ['temperature', 'windspeed', 'pressure', 'humidity', 'precipitation']
        for param in expected_params:
            self.assertIn(param, data)

    #Тест добавления города для неправильного пользователя
    def test_add_city_invalid_user(self):
        response = requests.post(
            f"{self.base_url}/cities",
            json={
                'user_id': 99999,
                'name': 'Berlin',
                'latitude': 52.5200,
                'longitude': 13.4050
            },
            timeout=10
        )
        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertIn('error', data)

if __name__ == '__main__':
    try:
        response = requests.get("http://127.0.0.1:8000/health", timeout=3)
        if response.status_code == 200:
            print("Server is running successfully\n")
            # Запускаем тесты с увеличенным таймаутом
            unittest.main(verbosity=2)
        else:
            print("Server responds, but with an error")
            sys.exit(1)
    except requests.ConnectionError:
        print("ERROR: Server isn't running or isn't responding")
        print("Please launch the server in a separate terminal:")
        print("python3 script.py")
        sys.exit(1)
    except requests.Timeout:
        print("ERROR: The server is not responding (timeout)")
        print("Check that the server is running and listening on port 8000")
        sys.exit(1)