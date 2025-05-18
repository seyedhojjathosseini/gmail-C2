## 🔍 Overview

Gmail Remote Controller is a powerful, lightweight Python application that allows you to remotely control your computer using Gmail. Send commands via email and receive responses with system information, screenshots, files, and more. Perfect for remote administration or accessing your computer when you're away.

> ⚠️ **Educational Purpose Notice**: This tool is designed for educational purposes and legitimate personal use only, such as remotely accessing your own devices. Always use responsibly and ethically. The authors are not responsible for any misuse of this software.

## ✨ Features

- **Complete Remote Control**: Execute system commands remotely
- **File Operations**: Upload and download files from your system
- **System Monitoring**: View processes, system info, and screenshots
- **Device Control**: Webcam capture, audio recording, and more
- **Network Tools**: Check WiFi networks and approximate location
- **Persistence**: Optional automatic startup configuration
- **Security**: Commands only accepted from your own email address
- **Cross-Platform**: Works on Windows, macOS, and Linux

## 🚀 Getting Started

### Prerequisites

- Python 3.7 or higher
- Google account
- Required Python packages (see Installation)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/seyedhojjathosseini/gmail-C2.git
cd gmail-C2
```

2. Install required packages:
```bash
pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib psutil pillow requests opencv-python pyaudio pynput
```

3. Set up Gmail API:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project
   - Enable the Gmail API
   - Create OAuth 2.0 credentials (Desktop application)
   - Download the credentials JSON file
   - Rename it to `credentials.json` and place it in the project directory

4. Obtain the authentication token:
```bash
python get_token.py
```
   - This will open a browser window to authorize the application
   - Follow the prompts to allow access to your Gmail account
   - A `token.json` file will be created in your project directory

5. Configure the application:
   - Open `remote_control.py` and update the `CONFIG` dictionary with your email

6. Run the application:
```bash
python remote_control.py
```

## 📝 Usage

### Available Commands

Send an email to yourself with one of these commands in the body:

| Command | Description | Example |
|---------|-------------|---------|
| `help` | Show available commands | `help` |
| `exec [command]` | Execute a shell command | `exec dir` |
| `screenshot` | Capture a screenshot | `screenshot` |
| `upload [path]` | Upload a file from the system | `upload C:\file.txt` |
| `download [search_term]` | Download attachment from email | `download myfile` |
| `sysinfo` | Get detailed system information | `sysinfo` |
| `processes` | List running processes | `processes` |
| `kill [pid/name]` | Kill a process | `kill chrome.exe` |
| `webcam` | Capture an image from webcam | `webcam` |
| `audio [seconds]` | Record audio | `audio 10` |
| `browse [path]` | List files in directory | `browse C:\Users` |
| `keylog [start/stop]` | Start or stop keylogger | `keylog start` |
| `networks` | List available WiFi networks | `networks` |
| `location` | Get approximate location based on IP | `location` |
| `shutdown` | Shutdown the system | `shutdown` |
| `restart` | Restart the system | `restart` |
| `persist` | Setup persistence mechanism | `persist` |

## 📋 Example Workflow

1. Start the application on your computer
2. From your phone or another device, send an email to yourself with the command `sysinfo`
3. Within a minute, you'll receive an email with detailed system information
4. Send `screenshot` to get a current view of your desktop
5. Use `exec [command]` to run specific programs or commands

## 🛠️ Customization

You can extend and customize this project in many ways:

- Add new commands by extending the `commands` dictionary in the `RemoteController` class
- Modify the check interval in the `CONFIG` dictionary
- Implement additional security features
- Create a web interface for easier command sending

## 🔒 Security Considerations

- The application only accepts commands from your own email address
- All communication happens through your personal Gmail account
- Consider using an app-specific password for better security
- The `token.json` file contains sensitive information - keep it secure

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📞 Contact

Your Name - [@_Hojjat_](https://twitter.com/_Hojjat_) - seyedhojjathosseini@gmail.com

Project Link: [https://github.com/seyedhojjathosseini/gmail-C2](https://github.com/seyedhojjathosseini/gmail-C2)

## 🙏 Acknowledgements

- [Google Gmail API](https://developers.google.com/gmail/api)
- [Python psutil library](https://github.com/giampaolo/psutil)
- [All other used libraries and their maintainers]
