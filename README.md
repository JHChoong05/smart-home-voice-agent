# 🏠 Smart Home Voice Agent (SHVA)

An AI-powered Smart Home Voice Agent that enables users to control home appliances using natural voice commands. The system integrates **Whisper AI**, **Qwen LLM**, **ESP32**, **MQTT**, and a **Flask Web Dashboard** to provide intelligent voice interaction, real-time device monitoring, and remote smart home control.

---

## 📖 Overview

Smart Home Voice Agent (SHVA) is an intelligent home automation system capable of understanding natural language commands and converting them into hardware control instructions.

Instead of relying only on fixed commands such as:

> Turn on the light

the system also understands contextual requests like:

> It's getting dark here.

and automatically determines the correct action.

The system combines Artificial Intelligence with IoT to create a natural human-computer interaction experience.

---

## ✨ Features

- 🎤 Voice command recognition using Whisper AI
- 🧠 Natural language understanding using Qwen AI
- 🏡 Intelligent control of home appliances
- 💡 Light control
- 🌬️ Fan control
- 📺 Television control
- 🎵 Music playback support
- 🔊 Voice feedback through ESP32 speaker
- 📡 MQTT communication between Python and ESP32
- 🌡️ Temperature & humidity monitoring
- 📱 Modern Flask Web Dashboard
- 🌍 Remote access using Cloudflare Tunnel
- 🎙️ Wake-word detection ("Hey Home")
- 📋 Real-time activity logging
- 🌙 Multiple dashboard themes (Sunrise / Dark / Light)

# 🏗 System Architecture
<img width="1536" height="1024" alt="Architecture Diagrams" src="https://github.com/user-attachments/assets/4b6613b0-91b3-4366-80d5-beae33c5650f" />

# ⚙ Technologies Used

## Artificial Intelligence

- Whisper AI
- Qwen LLM

## Backend

- Python 3.11
- Flask

## IoT

- ESP32
- MQTT (Mosquitto)

## Frontend

- HTML
- CSS
- JavaScript

## Communication

- MQTT
- HTTP REST API

---

# 🛠 Hardware Components

- ESP32 Development Board
- DHT22 Temperature & Humidity Sensor
- INMP441 I2S Microphone
- MAX98357 Audio Amplifier
- Speaker
- LCD I2C Display
- Relay Module
- LED
- DC Fan
- TIP31C Transistor

# 📂 Project Structure
SHVA/
│
├── app.py
├── smart_home_voice.py
│
├── esp32/
│   └── smart_home_voice_agent.ino
│
├── requirements.txt
└── README.md

# 🚀 Workflow

1. User speaks a voice command.
2. Whisper converts speech into text.
3. Qwen interprets the user's intent.
4. Python generates a device command.
5. MQTT sends the command to ESP32.
6. ESP32 controls connected appliances.
7. Dashboard updates in real time.
8. ESP32 provides voice feedback.

---

# 📸 Dashboard Features

The Flask dashboard provides:

- Manual voice recording
- Wake-word activation
- Device status monitoring
- Live activity log
- Text command input
- Volume adjustment
- Theme switching
- Remote device control

---

# 🌍 Remote Access

The dashboard can be securely accessed outside the local network using **Cloudflare Tunnel**.

```
Internet
     │
Cloudflare Tunnel
     │
Flask Dashboard
     │
Python Backend
     │
ESP32
```

---

# 📦 Installation

## 1. Clone Repository

```bash
git clone https://github.com/yourusername/shva.git
cd shva
```

---

## 2. Create Virtual Environment

```bash
python -m venv whisper_env
```

Activate:

Windows

```bash
whisper_env\Scripts\activate
```

Linux/Mac

```bash
source whisper_env/bin/activate
```

---

## 3. Install Dependencies

```bash
pip install -r requirements.txt
```

or

```bash
pip install flask
pip install faster-whisper
pip install paho-mqtt
pip install scipy
pip install numpy
pip install sounddevice
pip install pydub
pip install pyaudio
pip install openai
pip install dashscope openai
```

---

## 4. Install MQTT Broker

Install Mosquitto MQTT Broker.

Run:

```bash
mosquitto -v
```

---

## 5. Configure API Key

Set your Qwen API key:

Windows

```bash
setx DASHSCOPE_API_KEY "YOUR_API_KEY"
```

---

## 6. Upload ESP32 Code

Configure:

- WiFi SSID
- WiFi Password
- MQTT Broker IP

Upload the Arduino sketch.

---

## 7. Start System

Run MQTT

```bash
mosquitto -v
```

Run backend

```bash
python app.py
```

Open browser

```
http://localhost:5000
```

---

# 🎙 Example Commands

```
Turn on the light

Turn off the fan

Play music

It's getting hot here

It's too dark

Turn everything off

Increase the volume

What's the temperature?
```

---

# 📊 Current Supported Devices

| Device | Status |
|---------|--------|
| Light | ✅ |
| Fan | ✅ |
| Television | ✅ |
| Speaker | ✅ |
| Temperature Sensor | ✅ |
| Humidity Sensor | ✅ |

---

# 🔮 Future Improvements

- Face Recognition
- Home Security System
- Mobile Application
- Multi-room Support
- Home Automation Scheduling
- Energy Consumption Analytics
- Camera Integration
- Smart Plug Support
- Home Assistant Integration

---

# 👨‍💻 Author

**JHChoong**

Smart Home Voice Agent (SHVA)

---

## 📄 License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
