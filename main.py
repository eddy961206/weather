# main.py
import os
import requests
from dotenv import load_dotenv
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

# 환경 변수 로드
load_dotenv()
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_CHANNEL = os.getenv("SLACK_CHANNEL")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
CITY_NAME = os.getenv("CITY_NAME")

# 슬랙 클라이언트 초기화
slack_client = WebClient(token=SLACK_BOT_TOKEN)

def get_weather_data(city_name, api_key):
    # 현재 날씨 데이터 가져오기
    url = f"http://api.openweathermap.org/data/3.0/weather?q={city_name}&appid={api_key}&units=metric"
    response = requests.get(url)
    current_data = response.json()

    # 시간별 예보 데이터 가져오기
    forecast_url = f"http://api.openweathermap.org/data/3.0/forecast?q={city_name}&appid={api_key}&units=metric"
    forecast_response = requests.get(forecast_url)
    forecast_data = forecast_response.json()

    # 미세먼지 데이터 가져오기
    air_quality_url = f"http://api.openweathermap.org/data/3.0/air_pollution?lat={current_data['coord']['lat']}&lon={current_data['coord']['lon']}&appid={api_key}"
    air_quality_response = requests.get(air_quality_url)
    air_quality_data = air_quality_response.json()

    return current_data, forecast_data, air_quality_data

def parse_weather_data(current_data, forecast_data, air_quality_data):
    # 현재 날씨
    main_weather = current_data["weather"][0]["main"]
    temp_min = forecast_data["list"][0]["main"]["temp_min"]
    temp_max = forecast_data["list"][0]["main"]["temp_max"]
    temp_min_time = forecast_data["list"][0]["dt_txt"]
    temp_max_time = forecast_data["list"][0]["dt_txt"]

    print(forecast_data)

    # 강수확률
    precipitation = []
    for forecast in forecast_data["list"]:
        rain = forecast.get("rain", {}).get("3h", 0)  # "rain" 키가 없으면 0으로 설정
        if rain > 0:
            precipitation.append((forecast["dt_txt"], forecast["pop"]))

    highest_precipitation = max(precipitation, key=lambda x: x[1]) if precipitation else None

    # 미세먼지
    pm10 = air_quality_data["list"][0]["components"]["pm10"]
    pm2_5 = air_quality_data["list"][0]["components"]["pm2_5"]

    return main_weather, temp_min, temp_max, temp_min_time, temp_max_time, highest_precipitation, pm10, pm2_5

def send_slack_message(channel, message):
    try:
        slack_client.chat_postMessage(channel=channel, text=message)
        print(f"Message sent to Slack: {message}")
    except SlackApiError as e:
        print(f"Error sending message: {e.response['error']}")

def main():
    current_data, forecast_data, air_quality_data = get_weather_data(CITY_NAME, OPENWEATHER_API_KEY)
    main_weather, temp_min, temp_max, temp_min_time, temp_max_time, highest_precipitation, pm10, pm2_5 = parse_weather_data(current_data, forecast_data, air_quality_data)

    message = (
        f"오늘의 날씨: {main_weather}\n"
        f"최저 기온: {temp_min}°C (시간: {temp_min_time})\n"
        f"최고 기온: {temp_max}°C (시간: {temp_max_time})\n"
    )
    if highest_precipitation:
        message += f"강수확률이 가장 높은 시간: {highest_precipitation[0]}, 확률: {highest_precipitation[1]*100}%\n"

    message += (
        f"미세먼지 (PM10): {pm10} µg/m³\n"
        f"초미세먼지 (PM2.5): {pm2_5} µg/m³\n"
    )

    send_slack_message(SLACK_CHANNEL, message)

if __name__ == "__main__":
    main()
