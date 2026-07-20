@echo off
color 0b
echo ==========================================
echo   Starting Smart Home Infrastructure...
echo ==========================================

:: 1. Start the Mosquitto MQTT Broker in the background
echo [1/3] Booting MQTT Broker...
start /b "" "C:\Program Files\Mosquitto\mosquitto.exe" -c "C:\Program Files\Mosquitto\mosquitto.conf"

:: Wait 2 seconds to ensure the broker is fully online
timeout /t 2 /nobreak > nul

:: 2. Navigate to your project directory
echo [2/3] Loading Python Environment...
cd /d C:\Whisper311

:: 3. Open the web browser automatically
echo [3/3] Launching Dashboard UI...
start http://127.0.0.1:5000

:: 4. Activate the virtual environment and run the app
call whisper_env\Scripts\activate
python app.py
