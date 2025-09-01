import nltk
import ssl
from nltk.tokenize import word_tokenize
from nltk.tag import pos_tag
from flask import Flask, request, render_template, jsonify
import requests
import re
from fuzzywuzzy import fuzz
from data.places import city_names, test_data

nltk.download('punkt')
nltk.download('averaged_perceptron_tagger')

try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context

app = Flask(__name__)

API_KEY = ""
BASE_URL = "http://api.openweathermap.org/data/2.5/weather"

# Custom list of Kannada stopwords
kannada_stopwords = set([' ನಲ್ಲಿ', 'ಗೆ', 'ಮತ್ತು', 'ಆದರೆ', 'ಆದ್ದರಿಂದ', 'ಈ', 'ಇದು', 'ಈಗ', 'ಇಲ್ಲ', 'ಎಂದು', 'ಒಂದು', 'ನಾನು', 'ನೀವು', 'ನಮ್ಮ', 'ನಿಮ್ಮ', 'ಅವರು', 'ಅದು', 'ಯಾರು', 'ಏನು', 'ಎಲ್ಲಿ', 'ಯಾವ', 'ಹೇಗೆ', 'ಯಾವಾಗ', 'ಎಷ್ಟು', 'ಆ', 'ಇ', 'ಉ', 'ಎ', 'ಒ'])

# Function to preprocess user text (tokenize, remove stopwords, and filter Kannada words)
def preprocess_text(text):
    tokens = word_tokenize(text)
    tokens = [token for token in tokens if token.lower() not in kannada_stopwords and re.match(r'[\u0C80-\u0CFF]+', token)]
    return tokens

# Extract city name using fuzzy matching
def extract_city_name(tokens):
    potential_cities = [word for word in tokens]
    for token in potential_cities:
        for kannada_city, variations in city_names.items():
            if fuzz.partial_ratio(token.lower(), kannada_city.lower()) > 80 or any(fuzz.partial_ratio(token.lower(), city.lower()) > 80 for city in variations):
                return variations[0]
    return None

# Convert Kelvin to Celsius
def kelvin_to_celsius(kelvin):
    return round(kelvin - 273.15, 1)

# Fetch weather data from OpenWeather API
def get_weather_data(location):
    try:
        params = {
            'q': location,
            'appid': API_KEY,
            'lang': 'kn'
        }
        response = requests.get(BASE_URL, params=params)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error fetching weather data: {e}")
        return None

# Format weather response in Kannada
def format_weather_response(weather_data):
    if weather_data is None:
        return "ಕ್ಷಮಿಸಿ, ಹವಾಮಾನ ಮಾಹಿತಿಯನ್ನು ಪಡೆಯಲು ಸಾಧ್ಯವಾಗಲಿಲ್ಲ."

    try:
        city = weather_data['name']
        temp = kelvin_to_celsius(weather_data['main']['temp'])
        feels_like = kelvin_to_celsius(weather_data['main']['feels_like'])
        humidity = weather_data['main']['humidity']
        wind_speed = weather_data['wind']['speed']
        description = weather_data['weather'][0]['description']

        weather_descriptions = {
            "clear sky": "ಸ್ಪಷ್ಟ ಆಕಾಶ",
            "few clouds": "ಚಿಂಟು ಮೋಡ",
            "scattered clouds": "ವಿತರಿತ ಮೋಡ",
            "broken clouds": "ಬಿರುಕು ಮೂಡಿದ ಮೋಡ",
            "shower rain": "ಮಳೆಯ ತೋಳ",
            "rain": "ಮಳೆ",
            "thunderstorm": "ಮಳೆಯ ತೋಳ",
            "snow": "ಹಿಮ",
            "haze": "ಮಬ್ಬು",
            "dust": "ಮಾಟ್ಟು",
            "fog": "ಮಾಟ್ಟು",
            "overcast clouds": "ಮೋಡ ಕವಿದ ಮೋಡಗಳು",
            "mist": "ಮಿಸ್ಟ್"
        }

        description_kannada = weather_descriptions.get(description, description)

        response_lines = [
            f"{city} ನಲ್ಲಿ ಪ್ರಸ್ತುತ ಹವಾಮಾನ:",
            f"🌡️ ತಾಪಮಾನ: {temp}°C",
            f"🤔 ಅನುಭವಿಸುವ ತಾಪಮಾನ: {feels_like}°C",
            f"💧 ಆರ್ದ್ರತೆ: {humidity}%",
            f"🌬️ ಗಾಳಿಯ ವೇಗ: {wind_speed} m/s",
            f"🌤️ ವಿವರಣೆ: {description_kannada}"
        ]

        return "\n".join(response_lines)

    except KeyError as e:
        print(f"Error formatting weather data: {e}")
        return "ಕ್ಷಮಿಸಿ, ಹವಾಮಾನ ಮಾಹಿತಿಯನ್ನು ಸರಿಯಾಗಿ ಪ್ರಕ್ರಿಯೆಗೊಳಿಸಲು ಸಾಧ್ಯವಾಗಲಿಲ್ಲ."

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/get_weather', methods=['POST'])
def get_weather():
    try:
        user_input = request.form['location']

        tokens = preprocess_text(user_input)
        city = extract_city_name(tokens)

        if city:
            weather_data = get_weather_data(city)
            if weather_data:
                response = format_weather_response(weather_data)
                accuracy = 100  # 100% if we get a valid weather response
            else:
                response = "ಕ್ಷಮಿಸಿ, ನಾನು ಹವಾಮಾನ ಮಾಹಿತಿಯನ್ನು ಪಡೆಯಲು ಸಾಧ್ಯವಾಗಲಿಲ್ಲ."
                accuracy = 0  # 0% if no valid data returned
        else:
            # Fallback: query API with raw input
            weather_data = get_weather_data(user_input)
            if weather_data:
                response = format_weather_response(weather_data)
                accuracy = 100  # 100% if valid weather data is returned
            else:
                response = "ಕ್ಷಮಿಸಿ, ನಾನು ಹವಾಮಾನ ಮಾಹಿತಿಯನ್ನು ಪಡೆಯಲು ಸಾಧ್ಯವಾಗಲಿಲ್ಲ."
                accuracy = 0  # 0% if no valid data returned

        print(f"Real-time accuracy: {accuracy}%")  # Log accuracy
        return jsonify({'response': response, 'accuracy': accuracy})
    except Exception as e:
        print(f"Error in get_weather: {e}")
        return jsonify({'response': "ಕ್ಷಮಿಸಿ, ತಾಂತ್ರಿಕ ತೊಂದರೆ ಇದೆ. ದಯವಿಟ್ಟು ನಂತರ ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ."}), 500

if __name__ == '__main__':
    app.run(debug=True)


