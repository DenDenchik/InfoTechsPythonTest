# ТЕСТОВОЕ ЗАДАНИЕ

HTTP-сервер для предоставления информации о погоде с использованием Open-Meteo API.

## Установка и запуск

1.  Установите зависимости:
    pip install -r requirements.txt

2. Запустите сервер:
    python3 script.py

Сервер будет доступен по адресу: http://127.0.0.1:8000

## API Методы

Синтаксис запросов указан для Windows PowerShell

1. Регистрация пользователя (POST /register)
    Invoke-RestMethod -Uri "http://127.0.0.1:8000/register" -Method POST -Body '{"username":"*имя пользователя*"}' -ContentType "application/json"
Пример:
    Invoke-RestMethod -Uri "http://127.0.0.1:8000/register" -Method POST -Body '{"username":"test_user"}' -ContentType "application/json"

2. Получение текущей погоды по координатам (GET /weather/current?latitude={lat}&longitude={lon})
    Invoke-RestMethod -Uri "http://127.0.0.1:8000/weather/current?latitude=*широта*&longitude=*долгота*"
Пример:
    Invoke-RestMethod -Uri "http://127.0.0.1:8000/weather/current?latitude=56.4846&longitude=84.9479"

3. Добавление города (POST /cities)
    Invoke-RestMethod -Uri "http://127.0.0.1:8000/cities" -Method POST -Body '{"user_id":*айди пользователя*,"name":"*название города*","latitude":*широта*,"longitude":*долгота*}' -ContentType "application/json"
Пример:
    Invoke-RestMethod -Uri "http://127.0.0.1:8000/cities" -Method POST -Body '{"user_id":1,"name":"Tomsk","latitude":56.4846,"longitude":84.9479}' -ContentType "application/json"

4. Получение списка городов пользователя (GET /cities?user_id={user_id})
    Invoke-RestMethod -Uri "http://127.0.0.1:8000/cities?user_id=*айди пользователя*"
Пример:
    Invoke-RestMethod -Uri "http://127.0.0.1:8000/cities?user_id=1"

5. Получение прогноза погоды для города на указанное время (GET /weather/forecast?user_id={user_id}&city_name={name}&time={HH:MM}&params={param1,param2,...})
    Invoke-RestMethod -Uri "http://127.0.0.1:8000/weather/forecast?user_id=*айди пользователя*&city_name=*название города*&time=*время*&params=*параметры**"
Примеры:
Получение всех параметров:
    Invoke-RestMethod -Uri "http://127.0.0.1:8000/weather/forecast?user_id=1&city_name=Tomsk&time=12:00"
Получение только температуры и скорости ветра:
    Invoke-RestMethod -Uri "http://127.0.0.1:8000/weather/forecast?user_id=1&city_name=Tomsk&time=12:00&params=temperature,windspeed"

## Запуск тестов

Для запуска юнит-тестов выполните команду:

    python3 test_script.py
