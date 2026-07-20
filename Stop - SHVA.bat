@echo off
echo Shutting down Smart Home Infrastructure...
taskkill /F /IM python.exe
taskkill /F /IM mosquitto.exe