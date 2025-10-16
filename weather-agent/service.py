import os
import json

def get_weather_data(date):

    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(script_dir, "weather_data.json")
    
    with open(file_path, "r") as file:
        data = json.load(file)
    
    weather_data = [d for d in data if d["date"] == date]

    return weather_data.pop() if weather_data else {"error": "No data found for the given date."}