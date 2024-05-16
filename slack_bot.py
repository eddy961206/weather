import requests
from datetime import datetime

# 환경 설정
OPENWEATHER_API_KEY = 'your_openweather_api_key'  # OpenWeatherMap API 키
LATITUDE = '37.5665'  # 예: 서울의 위도
LONGITUDE = '126.9780'  # 예: 서울의 경도
SLACK_WEBHOOK_URL = 'your_slack_webhook_url'  # Slack 웹후크 URL

def get_weather():
    # OpenWeatherMap API를 사용하여 날씨 데이터 가져오기
    url = f"http://api.openweathermap.org/data/2.5/weather?lat={LATITUDE}&lon={LONGITUDE}&appid={OPENWEATHER_API_KEY}&units=metric"
    response = requests.get(url)
    data = response.json()
    
    # 날씨 데이터 파싱
    temp = data['main']['temp']
    weather_id = data['weather'][0]['id']
    weather_main = data['weather'][0]['main']
    
    # 날씨 상태에 따른 이모지 결정
    if weather_id >= 200 and weather_id <= 232:
        weather_emoji = "⛈"  # 뇌우
    elif weather_id >= 300 and weather_id <= 321:
        weather_emoji = "🌧"  # 이슬비
    elif weather_id >= 500 and weather_id <= 531:
        weather_emoji = "🌧"  # 비
    elif weather_id >= 600 and weather_id <= 622:
        weather_emoji = "❄️"  # 눈
    elif weather_id >= 701 and weather_id <= 781:
        weather_emoji = "🌫"  # 안개
    elif weather_id == 800:
        weather_emoji = "☀️"  # 맑음
    elif weather_id >= 801 and weather_id <= 804:
        weather_emoji = "☁️"  # 구름
    else : 
        weather_emoji = "❓"
    
    # Slack 메시지 포맷
    message = f"{weather_emoji} {temp:.1f}°C"
    
    return message

def send_slack_message(message):
    # 슬랙에 메시지 보내기
    payload = {
        'text': message,
        'username': 'WeatherBot',
        'icon_emoji': ':sun_with_face:'
    }
    response = requests.post(SLACK_WEBHOOK_URL, json=payload)
    print('Message sent to Slack', response.text)

# 메인 함수
def main():
    weather_message = get_weather()
    send_slack_message(weather_message)

if __name__ == "__main__":
    main()