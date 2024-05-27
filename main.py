import os
import requests
import time
import schedule
from dotenv import load_dotenv
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from datetime import datetime
from urllib.parse import urlencode

# 환경 변수 로드
load_dotenv()
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_CHANNEL = os.getenv("SLACK_CHANNEL")
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")
AIR_QUALITY_API_KEY = os.getenv("AIR_QUALITY_API_KEY")
NX = os.getenv("NX")
NY = os.getenv("NY")
LOCATION_NAME = os.getenv("LOCATION_NAME")

# 슬랙 클라이언트 초기화
slack_client = WebClient(token=SLACK_BOT_TOKEN)

def get_weather_data(api_key, nx, ny):
    base_date = datetime.now().strftime("%Y%m%d")
    base_time = "0500"  # 05:00 발표 기준 데이터 요청

    # 단기예보 조회
    url = f"http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getVilageFcst"
    params = {
        'serviceKey': api_key,
        'numOfRows': '1000',
        'pageNo': '1',
        'dataType': 'JSON',
        'base_date': base_date,
        'base_time': base_time,
        'nx': nx,
        'ny': ny
    }
    response = requests.get(url, params=params)

    if response.status_code != 200:
        print(f"Error: Unable to fetch weather data, status code: {response.status_code}")
        print(f"Response text: {response.text}")
        return None

    try:
        response_data = response.json()
    except requests.exceptions.JSONDecodeError as e:
        print(f"Error: Unable to parse JSON response. {e}")
        print(f"Response text: {response.text}")
        return None

    return response_data['response']['body']['items']['item']

def get_air_quality_data(api_key, location_name):
    url = f"http://apis.data.go.kr/B552584/ArpltnInforInqireSvc/getMsrstnAcctoRltmMesureDnsty"
    params = {
        'serviceKey': api_key,
        'returnType': 'JSON',
        'numOfRows': '1',
        'pageNo': '1',
        'stationName': location_name,
        'dataTerm': 'DAILY',
        'ver': '1.3'
    }

    # Create the full URL for debugging
    full_url = f"{url}?{urlencode(params)}"
    # print(f"Request URL: {full_url}")

    response = requests.get(full_url)
    # print(response.text)

    if response.status_code != 200:
        print(f"Error: Unable to fetch air quality data, status code: {response.status_code}")
        print(f"Response text: {response.text}")
        return None

    try:
        response_data = response.json()
    except requests.exceptions.JSONDecodeError as e:
        print(f"Error: Unable to parse JSON response. {e}")
        print(f"Response text: {response.text}")
        return None

    if not response_data['response']['body']['items']:
        print("Error: No air quality data available.")
        return None

    return response_data['response']['body']['items'][0]

def get_weather_alerts(api_key):
    base_date = datetime.now().strftime("%Y%m%d")
    base_time = "0600"  # 06:00 발표 기준 데이터 요청

    # 기상 특보 조회
    url = f"http://apis.data.go.kr/1360000/WthrWrnInfoService/getWthrWrnMsg"
    params = {
        'serviceKey': api_key,
        'numOfRows': '10',
        'pageNo': '1',
        'dataType': 'JSON',
        'stnId': '108'  # 서울 지역 코드
    }
    response = requests.get(url, params=params)

    if response.status_code != 200:
        print(f"Error: Unable to fetch weather alert data, status code: {response.status_code}")
        print(f"Response text: {response.text}")
        return None

    try:
        response_data = response.json()
    except requests.exceptions.JSONDecodeError as e:
        print(f"Error: Unable to parse JSON response. {e}")
        print(f"Response text: {response.text}")
        return None

    # 응답 데이터 출력
    print(response_data)

    # 서울 관련 특보 항목만 필터링
    items = response_data['response']['body']['items']['item']
    seoul_keywords = ["서울", "서울특별시"]
    seoul_alerts = [
        item for item in items 
        if any(keyword in (
            str(item.get('t1', '')) + str(item.get('t2', '')) + str(item.get('t3', '')) +
            str(item.get('t4', '')) + str(item.get('t5', '')) + str(item.get('t6', '')) + str(item.get('t7', ''))
        ) for keyword in seoul_keywords)
    ]

    return seoul_alerts


def convert_to_grade(value):
    grade_map = {
        '1': '😊 좋음',
        '2': '😐 보통',
        '3': '😷 나쁨',
        '4': '🤢 매우나쁨'
    }
    return grade_map.get(value, '❓ 정보 없음')


def parse_weather_data(items):
    weather_data = {
        'rain': [],
        'temp_min': None,
        'temp_min_time': None,
        'temp_max': None,
        'temp_max_time': None,
    }

    for item in items:
        category = item['category']
        fcst_time = item['fcstTime']
        fcst_value = item['fcstValue']

        if category == 'POP':  # 강수확률
            weather_data['rain'].append((fcst_time, fcst_value))
        elif category == 'TMN':  # 최저기온
            if weather_data['temp_min'] is None or (fcst_time >= "0800" and weather_data['temp_min_time'] is not None and weather_data['temp_min_time'] < "0800"):  # 0800 이후의 최저 기온
                weather_data['temp_min'] = fcst_value
                weather_data['temp_min_time'] = fcst_time
        elif category == 'TMX':  # 최고기온
            if weather_data['temp_max'] is None or fcst_time == "1500":  # 1500 기준 시간으로 갱신
                weather_data['temp_max'] = fcst_value
                weather_data['temp_max_time'] = fcst_time

    # 강수확률 상위 3개 시간대 추출
    sorted_rain = sorted(weather_data['rain'], key=lambda x: int(x[1]), reverse=True)[:3]
    weather_data['highest_rain'] = sorted_rain

    return weather_data

def parse_air_quality_data(item):
    air_quality_data = {
        'pm10': convert_to_grade(item.get('pm10Grade1h')),
        'pm2_5': convert_to_grade(item.get('pm25Grade1h')),
        'overall': convert_to_grade(item.get('khaiGrade'))
    }
    return air_quality_data

def format_time(time_str):
    return datetime.strptime(time_str, "%H%M").strftime("%H:%M")

def send_slack_message(channel, message):
    try:
        slack_client.chat_postMessage(channel=channel, text=message)
        print(f"Message sent to Slack: {message}")
    except SlackApiError as e:
        print(f"Error sending message: {e.response['error']}")

def main():
    weather_items = get_weather_data(WEATHER_API_KEY, NX, NY)
    if weather_items is None:
        print("No weather data available.")
        return

    air_quality_item = get_air_quality_data(AIR_QUALITY_API_KEY, LOCATION_NAME)
    if air_quality_item is None:
        print("No air quality data available.")
        return

    weather_data = parse_weather_data(weather_items)
    air_quality_data = parse_air_quality_data(air_quality_item)

    message = (
        f"🥶: {weather_data['temp_min']}°C ({format_time(weather_data['temp_min_time'])})\n"
        f"🥵: {weather_data['temp_max']}°C ({format_time(weather_data['temp_max_time'])})\n"
    )
    if weather_data['highest_rain']:
        for idx, (time, pop) in enumerate(weather_data['highest_rain'], start=1):
            message += f"🌧️ {idx}: {pop}% - {format_time(time)} \n"

    message += (
        f"🌫️ PM10: {air_quality_data['pm10']}\n"
        f"🌫️ PM2.5: {air_quality_data['pm2_5']}\n"
        f"🌍 종합: {air_quality_data['overall']}\n"
    )

    weather_alerts = get_weather_alerts(WEATHER_API_KEY)
    if weather_alerts:
        message += "\n기상 특보:\n"
        for alert in weather_alerts:
            message += f"- {alert['t1']}: {alert['t2']} ({alert['t3']})\n"

    send_slack_message(SLACK_CHANNEL, message)


main()
# 스케줄러 설정
schedule.every().day.at("06:00").do(main)

while True:
    schedule.run_pending()
    time.sleep(1)
