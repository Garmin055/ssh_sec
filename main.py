import os
import subprocess
import re
import requests
import json
from datetime import datetime

# 웹훅 URL 가져오기
def get_webhook_url():
    try:
        with open('webhook.txt', 'r') as file:
            webhook_url = file.read().strip()
        return webhook_url
    except FileNotFoundError:
        print("webhook.txt 파일을 찾을 수 없습니다.")
        return None

# IP 정보 조회 함수 (ipinfo.io 사용)
def get_ip_info(ip_address):
    try:
        response = requests.get(f'https://ipinfo.io/{ip_address}/json')
        if response.status_code == 200:
            data = response.json()
            country = data.get('country', '알 수 없음')
            org = data.get('org', '')

            # VPN 여부 확인 (ISP나 호스팅 업체의 이름을 이용해 대략적으로 확인 가능)
            is_vpn = "VPN 사용" if "vpn" in org.lower() or "hosting" in org.lower() else "VPN 미사용"

            return {
                "ip_address": ip_address,
                "country": country,
                "is_vpn": is_vpn
            }
        else:
            print(f"IP 정보 조회 실패: {response.status_code}")
            return None
    except Exception as e:
        print(f"IP 정보 조회 중 오류 발생: {e}")
        return None

# 명령어 기록 가져오기
def get_command_history():
    try:
        with open(os.path.expanduser('~/.bash_history'), 'r') as file:
            commands = file.readlines()
        return commands[-10:]  # 최근 10개의 명령어를 가져옴
    except FileNotFoundError:
        print(".bash_history 파일을 찾을 수 없습니다.")
        return []

# 웹훅 알림 보내기
def send_webhook_notification(username, ip_info, commands=None):
    webhook_url = get_webhook_url()
    if not webhook_url:
        return
    
    login_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # 로그아웃 시 명령어 전달
    if commands:
        data = {
            "username": username,
            "logout_time": login_time,
            "commands": commands
        }
    # 로그인 시 IP 정보 전달
    else:
        data = {
            "username": username,
            "ip_address": ip_info.get('ip_address', '알 수 없음'),
            "국가": ip_info.get('country', '알 수 없음'),
            "VPN 여부": ip_info.get('is_vpn', '알 수 없음'),
            "login_time": login_time
        }
    
    headers = {'Content-Type': 'application/json; charset=utf-8'}
    response = requests.post(webhook_url, data=json.dumps(data, ensure_ascii=False), headers=headers)
    
    if response.status_code == 200:
        print("웹훅 전송 성공")
    else:
        print(f"웹훅 전송 실패: {response.status_code}")

# SSH 로그인 감지 및 처리
def monitor_ssh_logins():
    process = subprocess.Popen(['journalctl', '-u', 'ssh', '-f'], stdout=subprocess.PIPE)
    
    while True:
        output = process.stdout.readline()
        if output:
            line = output.decode('utf-8').strip()
            match = re.search(r'Accepted \S+ for (\S+) from (\S+)', line)
            
            if match:
                username = match.group(1)
                ip_address = match.group(2)
                print(f"SSH 로그인 감지: {username} from {ip_address}")
                
                # IP 정보 조회
                ip_info = get_ip_info(ip_address)
                if ip_info:
                    send_webhook_notification(username, ip_info)

# 사용자가 로그아웃할 때 명령어 기록 전송
def on_logout():
    username = os.getlogin()
    commands = get_command_history()
    send_webhook_notification(username, None, commands=commands)

if __name__ == "__main__":
    # SSH 로그인 모니터링
    monitor_ssh_logins()
