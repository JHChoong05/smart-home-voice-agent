import os
import socket
import struct
import time
import wave
import re
import datetime
from pathlib import Path
 
import numpy as np
import paho.mqtt.client as mqtt
from faster_whisper import WhisperModel
from openai import OpenAI
from scipy.io.wavfile import write
from scipy.signal import butter, resample_poly, sosfiltfilt
 
try:
    import pyttsx3
except ImportError:
    pyttsx3 = None
 
# --- CONFIGURATIONS ---
BROKER = "10.194.186.2"
ESP32_IP = "10.194.186.48"
ESP32_MIC_PORT = 3333
ESP32_SPEAKER_PORT = 3334
 
API_KEY = os.getenv("QWEN_API_KEY")
if not API_KEY:
    raise RuntimeError(
        'Missing QWEN_API_KEY. Set it in CMD with: setx QWEN_API_KEY "your-qwen-api-key"'
    )
 
SAMPLE_RATE = 16000
RECORD_SECONDS = 4.0 
TEMP_WAV = Path("temp_esp32_mic.wav")
RAW_MIC_WAV = Path("temp_esp32_mic_raw.wav")
TTS_WAV = Path("assistant_reply.wav")

MUSIC_DIR = Path(r"C:\Users\zun4\Downloads\Smart Home Voice Agent\Smart Home Voice Agent\music")
MUSIC_EXTENSIONS = (".wav", ".mp3")
MUSIC_SECONDS = 30
current_volume = 0.25

latest_temperature = None
latest_humidity = None

def set_volume(vol):
    global current_volume
    current_volume = max(0.0, min(1.0, float(vol)))

# --- MQTT SETUP WITH SENSOR LISTENER ---
def on_connect(client, userdata, flags, rc):
    client.subscribe("home/temperature")

def on_message(client, userdata, msg):
    global latest_temperature, latest_humidity
    if msg.topic == "home/temperature":
        try:
            payload = msg.payload.decode('utf-8')
            temp, hum = payload.split(',')
            latest_temperature = float(temp)
            latest_humidity = float(hum)
        except Exception:
            pass

client_mqtt = mqtt.Client()
client_mqtt.on_connect = on_connect
client_mqtt.on_message = on_message
client_mqtt.connect(BROKER, 1883, 60)
client_mqtt.loop_start()
 

# ==============================================================================
# ALIBABA CLOUD INTEGRATION (QWEN CLOUD) - TRACK 5: EdgeAgent
# ==============================================================================
# PROOF OF CLOUD USAGE:
# This client connects the local Edge IoT hardware to Alibaba Cloud's DashScope 
# API infrastructure to utilize the Qwen 3.7 Max multimodal model.
# ==============================================================================
# Updated for Malaysia/Singapore Region
# Ensure this is the base_url in your script
# TEMPORARY HARDCODED AUTHENTICATION FOR TESTING
# UPDATE THIS TO MATCH YOUR SCREENSHOT EXACTLY
client_qwen = OpenAI(
    api_key = os.getenv("DASHSCOPE_API_KEY"), # Ensure this environment variable is set
    base_url = "https://ws-i0b2ww1xdquq2lg9.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1"
)

model = WhisperModel(
    "base",
    device="cpu",
    compute_type="int8",
)

def edge_local_fallback_parser(command):
    """
    TRACK 5 REQUIREMENT: GRACEFUL DEGRADATION
    If the connection to Alibaba Cloud drops, the EdgeAgent falls back to this 
    local, rule-based parser. This ensures the physical hardware (lights, fans) 
    can still be operated locally without internet access.
    """
    cmd = command.lower()
    intents = []
    
    if "light" in cmd: intents.append("LIGHT_ON" if "on" in cmd else "LIGHT_OFF")
    if "fan" in cmd: intents.append("FAN_ON" if "on" in cmd else "FAN_OFF")
    if "tv" in cmd or "television" in cmd: intents.append("TELEVISION_ON" if "on" in cmd else "TELEVISION_OFF")
    if "music" in cmd or "play" in cmd: intents.append("MUSIC_PLAY")
        
    if not intents:
        return "INTENTS: NONE\nREPLY: Alibaba Cloud connection is unavailable. I am operating in limited offline edge mode."
        
    intent_str = ",".join(intents)
    return f"INTENTS: {intent_str}\nREPLY: Cloud disconnected. Executing locally via Edge fallback."

def ask_qwen(command):
    now = datetime.datetime.now()
    dt_string = now.strftime("%A, %B %d, %Y - %I:%M %p")
    
    try:
        # ALIBABA CLOUD DASHSCOPE API CALL
        response = client_qwen.chat.completions.create(
            model="qwen3.7-plus",
            messages=[
                {
                    "role": "system",
                    "content": f"""You are a highly capable, conversational smart home AI assistant.
Current Date and Time: {dt_string}
 
You MUST respond in exactly this two-line format:
INTENTS: [comma-separated intents, or NONE]
REPLY: [Your natural, conversational spoken reply]

Available intents:
LIGHT_ON, LIGHT_OFF, FAN_ON, FAN_OFF, TELEVISION_ON, TELEVISION_OFF, ALL_OFF
MUSIC_PLAY, MUSIC_PLAY_<song_name>, GET_TEMPERATURE, GET_HUMIDITY
SET_VOLUME_<0-100>, VOLUME_UP, VOLUME_DOWN

Rules:
1. If asked for the time, date, or a general knowledge question, output INTENTS: NONE and answer conversationally in the REPLY.
2. VOLUME_UP means increase volume by 10%. VOLUME_DOWN means decrease volume by 10%.
3. If the user asks to play a specific song, return MUSIC_PLAY_ followed by the song name (e.g., MUSIC_PLAY_hall of fame). If no specific song, return MUSIC_PLAY.
4. For hardware actions, output the correct intent and acknowledge it naturally in the REPLY.
5. For temperature/humidity, use the intent and set REPLY to "Checking the sensors."
"""
                },
                {"role": "user", "content": command},
            ],
            timeout=10.0 # Force a timeout so edge degradation kicks in if cloud drops
        )
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        # Change the print to show the actual error message
        print(f"[EDGE FALLBACK] Alibaba Cloud API unreachable: {type(e).__name__} - {e}")
        return edge_local_fallback_parser(command)
# ==============================================================================
 
def parse_ai_response(response_text):
    intents = []
    reply = "I have processed your request."
    
    for line in response_text.split('\n'):
        if line.startswith("INTENTS:"):
            intent_part = line.replace("INTENTS:", "").strip()
            if intent_part != "NONE":
                intents = [x.strip().upper() for x in intent_part.split(",")]
        elif line.startswith("REPLY:"):
            reply = line.replace("REPLY:", "").strip()
            
    valid = {"LIGHT_ON", "LIGHT_OFF", "FAN_ON", "FAN_OFF", "TELEVISION_ON", 
             "TELEVISION_OFF", "ALL_OFF", "MUSIC_PLAY", "GET_TEMPERATURE", 
             "GET_HUMIDITY", "VOLUME_UP", "VOLUME_DOWN"}
             
    cleaned_intents = [
        i for i in intents 
        if i in valid or i.startswith("SET_VOLUME_") or i.startswith("MUSIC_PLAY_")
    ]
 
    if "ALL_OFF" in cleaned_intents:
        cleaned_intents = ["LIGHT_OFF", "FAN_OFF", "TELEVISION_OFF"] + [x for x in cleaned_intents if x != "ALL_OFF"]
 
    return cleaned_intents, reply

def get_sensor_replies(intents):
    replies = []
    if "GET_TEMPERATURE" in intents or "GET_HUMIDITY" in intents:
        time.sleep(0.5) 
        
    if "GET_TEMPERATURE" in intents:
        if latest_temperature is not None:
            replies.append(f"The temperature is {latest_temperature:.1f} degrees Celsius.")
        else:
            replies.append("Sensor data is currently unavailable.")
            
    if "GET_HUMIDITY" in intents:
        if latest_humidity is not None:
            replies.append(f"The humidity is {latest_humidity:.0f} percent.")
        else:
            replies.append("Sensor data is currently unavailable.")
            
    return " ".join(replies)

def reply_for_intent(intent):
    if intent == "LIGHT_ON": return "Turning on the light."
    if intent == "LIGHT_OFF": return "Turning off the light."
    if intent == "FAN_ON": return "Turning on the fan."
    if intent == "FAN_OFF": return "Turning off the fan."
    if intent == "TELEVISION_ON": return "Turning on the television."
    if intent == "TELEVISION_OFF": return "Turning off the television."
    return ""
 
def publish_intent(intent):
    if intent == "LIGHT_ON": client_mqtt.publish("home/light", "ON")
    elif intent == "LIGHT_OFF": client_mqtt.publish("home/light", "OFF")
    elif intent == "FAN_ON": client_mqtt.publish("home/fan", "ON")
    elif intent == "FAN_OFF": client_mqtt.publish("home/fan", "OFF")
    elif intent == "TELEVISION_ON": client_mqtt.publish("home/tv", "ON")
    elif intent == "TELEVISION_OFF": client_mqtt.publish("home/tv", "OFF")
    elif intent in ["GET_TEMPERATURE", "GET_HUMIDITY"]:
        client_mqtt.publish("home/request", "temperature")
    elif intent == "VOLUME_UP":
        set_volume(current_volume + 0.10)
    elif intent == "VOLUME_DOWN":
        set_volume(current_volume - 0.10)
    elif intent.startswith("SET_VOLUME_"):
        try:
            vol_val = int(intent.split("_")[2])
            set_volume(vol_val / 100.0)
        except:
            pass

# --- WAKE WORD LOGIC ---
def play_ack_beep():
    duration = 0.2
    frequency = 1200
    t = np.arange(int(SAMPLE_RATE * duration)) / SAMPLE_RATE
    audio = np.sin(2 * np.pi * frequency * t) * (10000 * current_volume)
    pcm = audio.astype(np.int16).tobytes()
    send_pcm_to_esp32(pcm)

def detect_wakeword():
    record_seconds = 4.5
    target_bytes = int(SAMPLE_RATE * record_seconds * 2)
    audio = bytearray()

    try:
        with socket.create_connection((ESP32_IP, ESP32_MIC_PORT), timeout=3) as sock:
            while len(audio) < target_bytes:
                data = sock.recv(4096)
                if not data:
                    break
                audio.extend(data)
    except Exception:
        return False, ""

    if len(audio) < target_bytes:
        audio.extend(b"\x00" * (target_bytes - len(audio)))

    raw = np.frombuffer(audio[:target_bytes], dtype=np.int16).copy()
    
    audio_f = raw.astype(np.float32)
    audio_f -= float(np.mean(audio_f)) 
    peak_volume = float(np.max(np.abs(audio_f)))
    
    if peak_volume < 800:  
        return False, ""
        
    cleaned = clean_mic_audio(raw)
    
    wake_wav = Path("temp_wake.wav")
    write(wake_wav, SAMPLE_RATE, cleaned)

    segments, _ = model.transcribe(str(wake_wav))
    text = " ".join([seg.text for seg in segments]).lower()
    clean_text = re.sub(r'[^\w\s]', '', text)
    
    if clean_text.strip():
        print(f"[Background Engine Heard]: {text} (Peak Vol: {int(peak_volume)})")
    
    triggers = [
        "hey home", "hi home", "smart home", 
        "hey holm", "a home", "hey hon", "high home",
        "hey ho", "hey hom" 
    ]
    
    for t in triggers:
        if t in clean_text:
            return True, text
            
    return False, text

def record_from_esp32():
    target_bytes = int(SAMPLE_RATE * RECORD_SECONDS * 2)
    audio = bytearray()
 
    print("\nConnecting to ESP32 INMP441 microphone...")
    with socket.create_connection((ESP32_IP, ESP32_MIC_PORT), timeout=10) as sock:
        while len(audio) < target_bytes:
            data = sock.recv(4096)
            if not data:
                break
            audio.extend(data)
 
    if len(audio) < target_bytes:
        audio.extend(b"\x00" * (target_bytes - len(audio)))
 
    raw = np.frombuffer(audio[:target_bytes], dtype=np.int16).copy()
    write(RAW_MIC_WAV, SAMPLE_RATE, raw)
 
    cleaned = clean_mic_audio(raw)
    write(TEMP_WAV, SAMPLE_RATE, cleaned)
 
def clean_mic_audio(audio):
    audio_f = audio.astype(np.float32)
    audio_f -= float(np.mean(audio_f))
 
    sos = butter(4, [100, 3800], btype="bandpass", fs=SAMPLE_RATE, output="sos")
    audio_f = sosfiltfilt(sos, audio_f)
 
    peak = float(np.max(np.abs(audio_f)))
    if peak > 1:
        target_peak = 14000.0
        audio_f *= target_peak / peak
 
    return audio_f.clip(-32768, 32767).astype(np.int16)
 
def listen():
    record_from_esp32()
 
    segments, _ = model.transcribe(str(TEMP_WAV))
    text = ""
    for segment in segments:
        text += segment.text
    return text.strip()

def make_tts_wav(text):
    if pyttsx3 is None:
        return False
 
    try:
        import pythoncom
        pythoncom.CoInitialize()
    except ImportError:
        pass
 
    if TTS_WAV.exists():
        TTS_WAV.unlink()
 
    try:
        engine = pyttsx3.init()
        engine.setProperty("rate", 165)
        engine.save_to_file(text, str(TTS_WAV))
        engine.runAndWait()
    except Exception as e:
        print(f"TTS Engine Error: {e}")
        return False
 
    for _ in range(30):
        if TTS_WAV.exists() and TTS_WAV.stat().st_size > 44:
            return True
        time.sleep(0.1)
    return False
 
def wav_to_16k_pcm_bytes(path, max_seconds=None):
    with wave.open(str(path), "rb") as wav:
        channels = wav.getnchannels()
        sample_width = wav.getsampwidth()
        rate = wav.getframerate()
        frame_count = wav.getnframes()
        if max_seconds is not None:
            frame_count = min(frame_count, int(rate * max_seconds))
        frames = wav.readframes(frame_count)
 
    audio = np.frombuffer(frames, dtype=np.int16)
    if channels > 1:
        audio = audio.reshape(-1, channels).mean(axis=1).astype(np.int16)
 
    if rate != SAMPLE_RATE:
        audio = resample_poly(audio, SAMPLE_RATE, rate).astype(np.int16)
 
    audio = (audio.astype(np.float32) * current_volume).clip(-32768, 32767).astype(np.int16)
    return audio.tobytes()
 
def audio_file_to_16k_pcm_bytes(path, max_seconds=None):
    if path.suffix.lower() == ".wav":
        return wav_to_16k_pcm_bytes(path, max_seconds=max_seconds)
 
    from pydub import AudioSegment
    audio = AudioSegment.from_file(str(path))
    if max_seconds is not None:
        audio = audio[: int(max_seconds * 1000)]
    audio = audio.set_channels(1).set_frame_rate(SAMPLE_RATE).set_sample_width(2)
    samples = np.frombuffer(audio.raw_data, dtype=np.int16)
    
    samples = (samples.astype(np.float32) * current_volume).clip(-32768, 32767).astype(np.int16)
    return samples.tobytes()
 
def send_pcm_to_esp32(pcm):
    with socket.create_connection((ESP32_IP, ESP32_SPEAKER_PORT), timeout=10) as sock:
        sock.sendall(struct.pack("<I", 0))
        for i in range(0, len(pcm), 1024):
            sock.sendall(pcm[i:i + 1024])
        sock.shutdown(socket.SHUT_WR)
        time.sleep(0.2)
 
def beep_pcm_bytes():
    duration = 0.5
    frequency = 880
    t = np.arange(int(SAMPLE_RATE * duration)) / SAMPLE_RATE
    audio = np.sin(2 * np.pi * frequency * t) * (10000 * current_volume)
    return audio.astype(np.int16).tobytes()
 
def find_music_file(requested_name=None):
    if not MUSIC_DIR.exists():
        return None
        
    files = []
    for extension in MUSIC_EXTENSIONS:
        files.extend(MUSIC_DIR.glob(f"*{extension}"))
        
    if not files:
        return None
        
    if requested_name:
        req_lower = requested_name.lower().strip()
        for f in files:
            if req_lower in f.stem.lower():
                return f
                
    return files[0]
 
def play_music_on_esp32(requested_name=None):
    music_file = find_music_file(requested_name)
    if music_file is None: return
    try:
        pcm = audio_file_to_16k_pcm_bytes(music_file, max_seconds=MUSIC_SECONDS)
        send_pcm_to_esp32(pcm)
    except Exception as exc: pass
 
def speak_on_esp32(text):
    if make_tts_wav(text):
        pcm = wav_to_16k_pcm_bytes(TTS_WAV)
    else:
        pcm = beep_pcm_bytes()
    send_pcm_to_esp32(pcm)