import requests
import json
from datetime import datetime
import pytz
from collections import defaultdict
import os
from serverchan_sdk import sc_send

# 常量定义
TARGET_LEAGUES = {'LPL', 'LCK'}
CHINA_TZ = pytz.timezone("Asia/Shanghai")
GRAPHQL_URL = 'https://esports.op.gg/matches/graphql/__query__ListUpcomingMatchesBySerie'
SendKey = os.environ['SEND_KEY']


def utc_to_china(utc_str: str) -> datetime:
    """时间转换函数"""
    dt_utc = datetime.strptime(utc_str, "%Y-%m-%dT%H:%M:%S.000Z")
    dt_utc = dt_utc.replace(tzinfo=pytz.utc)
    return dt_utc.astimezone(CHINA_TZ)


def fetch_upcoming_matches():
    """请求比赛数据"""
    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'Mozilla/5.0',
    }
    payload = {
        'query': '''
        query {
            upcomingMatches {
                id
                name
                status
                scheduledAt
                tournament {
                    serie {
                        league {
                            shortName
                        }
                    }
                }
            }
        }
        '''
    }

    try:
        response = requests.post(GRAPHQL_URL, json=payload, headers=headers)
        response.raise_for_status()
        return response.json().get('data', {}).get('upcomingMatches', [])
    except requests.RequestException as e:
        print(f"[错误] 请求失败：{e}")
        return []


def filter_today_matches(matches):
    """处理并筛选比赛数据"""
    today = datetime.now(CHINA_TZ).date()
    result = defaultdict(list)

    for match in matches:
        try:
            league = match['tournament']['serie']['league']['shortName']
            if league not in TARGET_LEAGUES:
                continue

            match_time = utc_to_china(match['scheduledAt'])
            if match_time.date() == today:
                result[league].append((match['name'], match_time.strftime("%Y-%m-%d %H:%M:%S")))
        except (KeyError, TypeError):
            continue  # 安全跳过格式不完整的数据

    return result


def display_matches(match_data):
    """输出比赛信息"""
    content = ''
    for league, matches in match_data.items():
        # print(f"\n赛区：{league}")
        content += f"\n赛区：{league}"
        for name, time in matches:
            # print(f"比赛：{name}")
            # print(f"开始时间：{time}")
            content += f"\n比赛：{name}\n开始时间：{time}"
    return content


def generate_markdown(match_data):
    """生成 Markdown 格式内容"""
    date_str = datetime.now(CHINA_TZ).date()
    md = f"## 🏆 今日赛程（{date_str}）\n\n"
    region_flags = {
        "LCK": "🇰🇷",
        "LPL": "🇨🇳"
    }
    for region, games in match_data.items():
        flag = region_flags.get(region, "")
        md += f"### {flag} **{region} 赛区**\n"
        md += "| 时间（北京时间） | 对阵           |\n"
        md += "|------------------|----------------|\n"
        for name, b_time in games:
            time = datetime.strptime(b_time, "%Y-%m-%d %H:%M:%S").strftime("%H:%M")
            md += f"| {time}            | {name}      |\n"
        md += "\n---\n\n"
    md += "> ✅ 所有时间均为北京时间（UTC+8）\n"
    return md


def send_message(content):
    """发送消息"""
    try:
        # 发送请求
        response = sc_send(SendKey, "LOL赛事信息", content)
        # 检查响应状态码
        if response['code'] == 0:
            print("消息发送成功:", response)
        else:
            print("消息发送失败:", response.get('error'))
    except requests.exceptions.RequestException as e:
        print("请求异常:", e)


def main():
    """主程序"""
    matches = fetch_upcoming_matches()
    today_matches = filter_today_matches(matches)
    if today_matches:
        markdown_output = generate_markdown(today_matches)
        send_message(markdown_output)


if __name__ == "__main__":
    main()
