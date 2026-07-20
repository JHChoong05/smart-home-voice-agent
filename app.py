from flask import Flask, render_template_string, request, jsonify
import threading
import time
import re
import smart_home_voice as sh

app = Flask(__name__)

# Device States & Background Logs
device_states = {"LIGHT": "OFF", "FAN": "OFF", "TELEVISION": "OFF"}
backend_logs = []
wake_word_active = False
wake_word_thread = None

def add_log(msg):
    time_str = time.strftime("%H:%M:%S")
    backend_logs.append({"time": time_str, "msg": msg})
    if len(backend_logs) > 50:
        backend_logs.pop(0)

def update_internal_states(intents):
    global device_states
    for intent in intents:
        if intent == "LIGHT_ON": device_states["LIGHT"] = "ON"
        elif intent == "LIGHT_OFF": device_states["LIGHT"] = "OFF"
        elif intent == "FAN_ON": device_states["FAN"] = "ON"
        elif intent == "FAN_OFF": device_states["FAN"] = "OFF"
        elif intent == "TELEVISION_ON": device_states["TELEVISION"] = "ON"
        elif intent == "TELEVISION_OFF": device_states["TELEVISION"] = "OFF"
        elif intent == "ALL_OFF":
            device_states["LIGHT"] = "OFF"
            device_states["FAN"] = "OFF"
            device_states["TELEVISION"] = "OFF"

def execute_command_pipeline(text):
    if not text: return
    add_log(f"<span class='log-normal'>[Processing]: '{text}'</span>")
    
    response_text = sh.ask_qwen(text)
    intents, ai_reply = sh.parse_ai_response(response_text)
    
    music_intent = None
    for intent in intents:
        sh.publish_intent(intent)
        if intent.startswith("MUSIC_PLAY"):
            music_intent = intent
            
    update_internal_states(intents)
    
    sensor_addon = sh.get_sensor_replies(intents)
    final_reply = f"{ai_reply} {sensor_addon}".strip()
    
    add_log(f"<strong class='log-action'>[System Action]:</strong> <span class='log-normal'>{final_reply}</span>")
    sh.speak_on_esp32(final_reply)
    
    # Identify if a specific song was requested
    if music_intent:
        song_name = None
        if music_intent != "MUSIC_PLAY":
            song_name = music_intent.replace("MUSIC_PLAY_", "")
        threading.Thread(target=sh.play_music_on_esp32, args=(song_name,)).start()

def wake_word_loop():
    global wake_word_active
    add_log("<span class='log-system'>[System] Wake Word Engine Started...</span>")
    
    while wake_word_active:
        triggered, full_text = sh.detect_wakeword()
        
        if triggered:
            clean_text = re.sub(r'[^\w\s]', '', full_text.lower())
            
            trigger_used = ""
            for t in ["hey home", "hi home", "smart home", "hey holm", "a home", "hey hon", "high home", "hey ho", "hey hom"]:
                if t in clean_text:
                    trigger_used = t
                    break
            
            command_part = clean_text.split(trigger_used, 1)[-1].strip()
            
            if len(command_part) > 3:
                add_log(f"<span class='log-wakeword'>[Wake Word] One-Breath Command:</span> <span class='log-normal'>'{full_text}'</span>")
                sh.play_ack_beep()
                execute_command_pipeline(command_part)
            else:
                add_log("<span class='log-wakeword'>[Wake Word] Triggered! Listening for command...</span>")
                sh.play_ack_beep()
                
                cmd_text = sh.listen()
                if not cmd_text:
                    add_log("<span class='log-error'>[Wake Word] No command detected after beep.</span>")
                    
                    respond_word = "I'm here. What can I do for you?"
                    add_log(f"<strong class='log-action'>[System Action]:</strong> <span class='log-normal'>{respond_word}</span>")
                    sh.speak_on_esp32(respond_word)
                    
                else:
                    execute_command_pipeline(cmd_text)
                    
            add_log("<span class='log-system'>[System] Resuming Wake Word standby.</span>")
            
        time.sleep(0.1)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en" data-theme="sunrise">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Smart Home Infrastructure</title>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        :root {
            --fluid-easing: cubic-bezier(0.25, 0.8, 0.25, 1);
        }

        /* 1. SUNRISE MODE */
        [data-theme="sunrise"] {
            --bg-grad: linear-gradient(-45deg, #1e133d, #631e50, #b23154, #ee6b51, #f5d47a);
            --shape-1: #fb923c; --shape-2: #e11d48; --shape-3: #fef08a;
            --panel-bg: rgba(255, 255, 255, 0.12); --panel-border: rgba(255, 255, 255, 0.25);
            --panel-shadow: 0 20px 50px rgba(0,0,0,0.15), inset 0 1px 0 rgba(255,255,255,0.3);
            --text-main: #ffffff; --text-muted: rgba(255, 255, 255, 0.75);
            --card-bg: rgba(255, 255, 255, 0.08); --card-hover: rgba(255, 255, 255, 0.15);
            --card-border: rgba(255, 255, 255, 0.15); --card-border-hover: rgba(255, 255, 255, 0.3);
            --icon-off: rgba(255, 255, 255, 0.6);
            --card-on-bg: linear-gradient(135deg, rgba(249, 115, 22, 0.25), rgba(225, 29, 72, 0.25));
            --card-on-border: rgba(249, 115, 22, 0.5); --card-on-text: #fef08a; --card-on-shadow: 0 10px 30px rgba(225, 29, 72, 0.2);
            --music-bg: linear-gradient(135deg, rgba(253, 164, 175, 0.15), rgba(225, 29, 72, 0.15));
            --music-hover: linear-gradient(135deg, rgba(253, 164, 175, 0.25), rgba(225, 29, 72, 0.25));
            --music-border: rgba(253, 164, 175, 0.3); --music-text: #fda4af;
            --btn-bg: rgba(255, 255, 255, 0.15); --btn-border: rgba(255, 255, 255, 0.3);
            --btn-hover-bg: rgba(255, 255, 255, 0.25); --btn-text: #ffffff;
            --ww-bg: linear-gradient(135deg, rgba(249, 115, 22, 0.2), rgba(225, 29, 72, 0.2));
            --ww-border: rgba(249, 115, 22, 0.4); --ww-text: #ffffff;
            --ww-active-bg: linear-gradient(135deg, rgba(16, 185, 129, 0.4), rgba(5, 150, 105, 0.4));
            --ww-active-border: rgba(16, 185, 129, 0.8); --ww-active-text: #ffffff;
            --input-bg: rgba(0, 0, 0, 0.2); --input-focus: rgba(0, 0, 0, 0.3);
            --send-btn: linear-gradient(135deg, #f97316, #e11d48);
            --log-bg: rgba(0, 0, 0, 0.25); --log-border: rgba(255, 255, 255, 0.1); --log-text: rgba(255,255,255,0.9);
            --log-time: #fca5a5; --log-action: #fbbf24; --log-system: #fcd34d; 
            --log-wakeword: #f43f5e; --log-error: #ef4444; --log-success: #4ade80;
            --logo-bg: linear-gradient(135deg, rgba(255,255,255,0.3), rgba(255,255,255,0.05));
            --logo-border: rgba(255,255,255,0.4); --logo-main: #ffffff; --logo-mic: #e11d48; --logo-mic-bg: #ffffff;
            --badge-bg: rgba(255, 255, 255, 0.15); --badge-text: #fef08a; --badge-border: rgba(255,255,255,0.3);
            --switch-bg: rgba(255,255,255,0.15); --switch-active: rgba(255,255,255,0.25); --switch-icon: rgba(255,255,255,0.6);
        }

        /* 2. DARK MODE */
        [data-theme="dark"] {
            --bg-grad: linear-gradient(-45deg, #020617, #0f172a, #1e293b, #0f172a);
            --shape-1: #3b82f6; --shape-2: #8b5cf6; --shape-3: #06b6d4;
            --panel-bg: rgba(30, 41, 59, 0.6); --panel-border: rgba(255, 255, 255, 0.08);
            --panel-shadow: 0 20px 50px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.05);
            --text-main: #f8fafc; --text-muted: #94a3b8;
            --card-bg: rgba(255, 255, 255, 0.03); --card-hover: rgba(255, 255, 255, 0.07);
            --card-border: rgba(255, 255, 255, 0.05); --card-border-hover: rgba(255, 255, 255, 0.15);
            --icon-off: #64748b;
            --card-on-bg: rgba(16, 185, 129, 0.1); --card-on-border: rgba(16, 185, 129, 0.3);
            --card-on-text: #10b981; --card-on-shadow: 0 8px 25px rgba(16, 185, 129, 0.15);
            --music-bg: linear-gradient(135deg, rgba(139, 92, 246, 0.1), rgba(109, 40, 217, 0.1));
            --music-hover: linear-gradient(135deg, rgba(139, 92, 246, 0.2), rgba(109, 40, 217, 0.2));
            --music-border: rgba(139, 92, 246, 0.2); --music-text: #a78bfa;
            --btn-bg: linear-gradient(135deg, #1e293b, #334155); --btn-border: rgba(255, 255, 255, 0.1);
            --btn-hover-bg: linear-gradient(135deg, #334155, #475569); --btn-text: #f8fafc;
            --ww-bg: linear-gradient(135deg, #312e81, #4338ca); --ww-border: #4f46e5; --ww-text: #f8fafc;
            --ww-active-bg: linear-gradient(135deg, #064e3b, #047857); --ww-active-border: #10b981; --ww-active-text: #f8fafc;
            --input-bg: rgba(0, 0, 0, 0.3); --input-focus: rgba(0, 0, 0, 0.5);
            --send-btn: linear-gradient(135deg, #3b82f6, #2563eb);
            --log-bg: #020617; --log-border: #1e293b; --log-text: #cbd5e1;
            --log-time: #64748b; --log-action: #38bdf8; --log-system: #818cf8; 
            --log-wakeword: #a78bfa; --log-error: #f87171; --log-success: #34d399;
            --logo-bg: linear-gradient(135deg, #1e293b, #0f172a);
            --logo-border: rgba(255,255,255,0.1); --logo-main: #f8fafc; --logo-mic: #0f172a; --logo-mic-bg: #3b82f6;
            --badge-bg: rgba(16, 185, 129, 0.15); --badge-text: #10b981; --badge-border: rgba(16, 185, 129, 0.3);
            --switch-bg: rgba(0,0,0,0.3); --switch-active: #334155; --switch-icon: #64748b;
        }

        /* 3. LIGHT MODE */
        [data-theme="light"] {
            --bg-grad: linear-gradient(-45deg, #f8fafc, #e2e8f0, #f1f5f9, #e0e7ff);
            --shape-1: #bfdbfe; --shape-2: #ddd6fe; --shape-3: #bbf7d0;
            --panel-bg: rgba(255, 255, 255, 0.75); --panel-border: rgba(0, 0, 0, 0.06);
            --panel-shadow: 0 20px 40px rgba(0,0,0,0.04);
            --text-main: #0f172a; --text-muted: #64748b;
            --card-bg: rgba(255, 255, 255, 0.8); --card-hover: rgba(255, 255, 255, 1);
            --card-border: rgba(0, 0, 0, 0.05); --card-border-hover: rgba(0, 0, 0, 0.1);
            --icon-off: #94a3b8;
            --card-on-bg: linear-gradient(135deg, #f0fdf4, #dcfce7); --card-on-border: rgba(16, 185, 129, 0.2);
            --card-on-text: #059669; --card-on-shadow: 0 8px 25px rgba(16, 185, 129, 0.1);
            --music-bg: linear-gradient(135deg, #f5f3ff, #ede9fe);
            --music-hover: linear-gradient(135deg, #ede9fe, #ddd6fe);
            --music-border: rgba(139, 92, 246, 0.2); --music-text: #7c3aed;
            --btn-bg: linear-gradient(135deg, #ffffff, #f8fafc); --btn-border: rgba(0, 0, 0, 0.1);
            --btn-hover-bg: linear-gradient(135deg, #f1f5f9, #e2e8f0); --btn-text: #0f172a;
            --ww-bg: linear-gradient(135deg, #ede9fe, #ddd6fe); --ww-border: #c4b5fd; --ww-text: #6d28d9;
            --ww-active-bg: linear-gradient(135deg, #dcfce7, #bbf7d0); --ww-active-border: #86efac; --ww-active-text: #047857;
            --input-bg: rgba(255, 255, 255, 0.9); --input-focus: #ffffff;
            --send-btn: linear-gradient(135deg, #3b82f6, #2563eb);
            --log-bg: rgba(255, 255, 255, 0.9); --log-border: rgba(0, 0, 0, 0.05); --log-text: #334155;
            --log-time: #94a3b8; --log-action: #2563eb; --log-system: #4f46e5; 
            --log-wakeword: #7c3aed; --log-error: #dc2626; --log-success: #059669;
            --logo-bg: linear-gradient(135deg, #ffffff, #f8fafc);
            --logo-border: rgba(0,0,0,0.1); --logo-main: #0f172a; --logo-mic: #ffffff; --logo-mic-bg: #3b82f6;
            --badge-bg: rgba(16, 185, 129, 0.1); --badge-text: #059669; --badge-border: rgba(16, 185, 129, 0.2);
            --switch-bg: rgba(0,0,0,0.05); --switch-active: #ffffff; --switch-icon: #94a3b8;
        }

        /* CORE STYLES */
        body { 
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; 
            color: var(--text-main); margin: 0; padding: 40px 20px; min-height: 100vh; overflow-x: hidden;
            background: var(--bg-grad); background-size: 400% 400%; animation: gradientBG 20s ease infinite; transition: background 0.8s ease, color 0.5s ease;
        }

        @keyframes gradientBG { 0% { background-position: 0% 50%; } 50% { background-position: 100% 50%; } 100% { background-position: 0% 50%; } }

        .bg-shapes { position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; z-index: -1; overflow: hidden; pointer-events: none;}
        .shape { position: absolute; filter: blur(120px); opacity: 0.6; animation: float 14s infinite alternate ease-in-out; border-radius: 50%; transition: background 0.8s ease; }
        .shape-1 { width: 600px; height: 600px; background: var(--shape-1); top: -15%; left: -10%; animation-delay: 0s; }
        .shape-2 { width: 700px; height: 700px; background: var(--shape-2); bottom: -20%; right: -15%; animation-delay: -5s; }
        .shape-3 { width: 500px; height: 500px; background: var(--shape-3); top: 40%; left: 30%; animation-delay: -9s; opacity: 0.4;}

        @keyframes float { 0% { transform: translate(0, 0) scale(1); } 100% { transform: translate(50px, -80px) scale(1.15); } }
        
        .container { max-width: 1000px; margin: 0 auto; position: relative; z-index: 1; }
        
        .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 40px; border-bottom: 1px solid var(--panel-border); padding-bottom: 20px; transition: all 0.5s; }
        h1.dash-title { margin: 0; font-size: 2.2rem; font-weight: 700; color: var(--text-main); display: flex; align-items: center; gap: 15px; letter-spacing: -0.5px; }
        
        .logo-stack { 
            position: relative; display: inline-flex; align-items: center; justify-content: center; 
            width: 48px; height: 48px; background: var(--logo-bg); border: 1px solid var(--logo-border);
            border-radius: 14px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); backdrop-filter: blur(10px); transition: all 0.5s;
        }
        .logo-stack .fa-house-chimney { font-size: 1.6rem; color: var(--logo-main); }
        .logo-stack .fa-microphone-alt { 
            position: absolute; font-size: 0.65rem; color: var(--logo-mic); 
            bottom: 10px; left: 50%; transform: translateX(-50%);
            background: var(--logo-mic-bg); padding: 2px 4px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.2);
        }

        .header-right { display: flex; align-items: center; gap: 15px; }
        
        .theme-switcher { 
            display: flex; background: var(--switch-bg); border: 1px solid var(--panel-border); 
            border-radius: 30px; padding: 4px; backdrop-filter: blur(10px); transition: all 0.5s;
        }
        .theme-btn { 
            background: transparent; border: none; color: var(--switch-icon); padding: 8px 14px; 
            border-radius: 20px; cursor: pointer; transition: all 0.3s; font-size: 0.95rem; 
        }
        .theme-btn.active { background: var(--switch-active); color: var(--text-main); box-shadow: 0 2px 8px rgba(0,0,0,0.1); }

        .status-badge { background: var(--badge-bg); color: var(--badge-text); padding: 10px 18px; border-radius: 30px; font-size: 0.85rem; font-weight: 700; border: 1px solid var(--badge-border); backdrop-filter: blur(10px); transition: all 0.5s;}
        
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 25px; }
        @media (max-width: 768px) { .grid { grid-template-columns: 1fr; } }
        
        .panel { 
            background: var(--panel-bg); backdrop-filter: blur(40px); -webkit-backdrop-filter: blur(40px);
            border: 1px solid var(--panel-border); border-radius: 24px; padding: 32px; 
            box-shadow: var(--panel-shadow); transition: all 0.5s;
        }
        .panel h2 { margin-top: 0; font-size: 1.1rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 2px; margin-bottom: 25px; display: flex; align-items: center; gap: 10px; font-weight: 700; transition: all 0.5s;}
        
        .voice-btn { width: 100%; padding: 22px; background: var(--btn-bg); border: 1px solid var(--btn-border); border-radius: 16px; color: var(--btn-text); font-size: 1.2rem; font-weight: 600; cursor: pointer; transition: all 0.4s var(--fluid-easing); box-shadow: 0 8px 25px rgba(0,0,0,0.05); display: flex; align-items: center; justify-content: center; gap: 12px; backdrop-filter: blur(10px); }
        .voice-btn:hover { background: var(--btn-hover-bg); transform: translateY(-4px) scale(1.01); box-shadow: 0 15px 35px rgba(0,0,0,0.1); }
        .voice-btn:active { transform: translateY(2px) scale(0.97); }
        
        #wakeWordBtn { background: var(--ww-bg); border-color: var(--ww-border); color: var(--ww-text); margin-top: 15px; }
        #wakeWordBtn.active-wake { background: var(--ww-active-bg); border-color: var(--ww-active-border); color: var(--ww-active-text); }
        
        .input-group { display: flex; gap: 12px; margin-top: 25px; }
        input[type="text"] { flex: 1; padding: 18px 22px; background: var(--input-bg); border: 1px solid var(--panel-border); border-radius: 16px; color: var(--text-main); font-size: 1.05rem; font-weight: 500; transition: all 0.3s ease; }
        input[type="text"]::placeholder { color: var(--text-muted); }
        input[type="text"]:focus { outline: none; border-color: var(--text-muted); background: var(--input-focus); }
        
        .send-btn { background: var(--send-btn); border: none; color: white; padding: 0 26px; border-radius: 16px; cursor: pointer; font-size: 1.2rem; transition: all 0.3s; box-shadow: 0 4px 15px rgba(0,0,0,0.2); }
        .send-btn:hover { filter: brightness(1.1); transform: translateY(-2px); }
        
        .slider-container { display: flex; align-items: center; gap: 18px; margin-top: 25px; padding: 22px; background: var(--card-bg); border: 1px solid var(--card-border); border-radius: 16px; transition: all 0.5s; }
        input[type="range"] { flex: 1; accent-color: var(--accent); cursor: pointer; height: 6px; border-radius: 3px; background: var(--panel-border); }
        
        .hw-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; }
        .device-card { background: var(--card-bg); border: 1px solid var(--card-border); padding: 22px 15px; border-radius: 18px; cursor: pointer; transition: all 0.4s var(--fluid-easing); display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 10px; text-align: center; overflow: hidden; box-shadow: 0 4px 15px rgba(0,0,0,0.02);}
        .device-card:hover { background: var(--card-hover); transform: translateY(-4px); border-color: var(--card-border-hover); }
        .device-card:active { transform: scale(0.96); }
        .device-card i { font-size: 2.2rem; color: var(--icon-off); transition: all 0.4s var(--fluid-easing); }
        .device-card .device-name { font-weight: 700; font-size: 1.05rem; margin-top: 5px; color: var(--text-main); transition: all 0.5s;}
        .device-card .device-state { font-size: 0.85rem; font-weight: 800; color: var(--text-muted); text-transform: uppercase; letter-spacing: 1.5px; transition: all 0.5s;}
        
        .device-card.is-on { background: var(--card-on-bg); border-color: var(--card-on-border); box-shadow: var(--card-on-shadow); }
        .device-card.is-on i { color: var(--card-on-text); text-shadow: 0 0 15px currentColor; }
        .device-card.is-on .device-state { color: var(--card-on-text); }

        .music-card { background: var(--music-bg); border-color: var(--music-border); }
        .music-card:hover { background: var(--music-hover); border-color: var(--music-border); }
        .music-card i, .music-card .device-state { color: var(--music-text); }
        
        #log-window { background: var(--log-bg); border-radius: 18px; padding: 25px; height: 250px; overflow-y: auto; font-family: 'SF Mono', 'Fira Code', monospace; font-size: 0.95rem; color: var(--log-text); border: 1px solid var(--log-border); line-height: 1.7; scroll-behavior: smooth; transition: all 0.5s;}
        .log-entry { margin-bottom: 10px; opacity: 0; animation: fadeUp 0.4s var(--fluid-easing) forwards; border-bottom: 1px dashed var(--log-border); padding-bottom: 8px; }
        .log-entry:last-child { border-bottom: none; }
        
        .log-time { color: var(--log-time); margin-right: 12px; font-weight: 600; font-size: 0.85rem; transition: color 0.5s;}
        .log-normal { color: var(--log-text); }
        .log-action { color: var(--log-action); font-weight: bold; }
        .log-system { color: var(--log-system); font-weight: bold; }
        .log-wakeword { color: var(--log-wakeword); font-weight: bold; }
        .log-error { color: var(--log-error); font-weight: bold; }
        .log-success { color: var(--log-success); font-weight: bold; }

        ::-webkit-scrollbar { width: 8px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: var(--panel-border); border-radius: 4px; }
        ::-webkit-scrollbar-thumb:hover { background: var(--text-muted); }
        
        @keyframes fadeUp { from { opacity: 0; transform: translateY(30px); } to { opacity: 1; transform: translateY(0); } }
        .animate-up { opacity: 0; animation: fadeUp 0.8s var(--fluid-easing) forwards; }
        .delay-1 { animation-delay: 0.2s; } .delay-2 { animation-delay: 0.4s; } .delay-3 { animation-delay: 0.6s; } .delay-4 { animation-delay: 0.8s; }
        
        .welcome-overlay {
            position: fixed; top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(30, 19, 61, 0.7); backdrop-filter: blur(35px); -webkit-backdrop-filter: blur(35px);
            z-index: 9999; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center;
            animation: fadeOutOverlay 1.5s var(--fluid-easing) forwards; animation-delay: 1.5s; pointer-events: none;
        }
        .welcome-overlay h1 {
            font-size: 4rem; margin: 0; background: linear-gradient(to right, #fef08a, #f97316, #e11d48);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            animation: scaleUp 1s var(--fluid-easing) forwards; font-weight: 800; letter-spacing: -1px;
        }
        .welcome-overlay p {
            color: #fef08a; font-size: 1.2rem; letter-spacing: 3px; text-transform: uppercase; margin-top: 15px;
            opacity: 0; animation: fadeUp 1s var(--fluid-easing) forwards; animation-delay: 0.5s;
        }
        @keyframes fadeOutOverlay { to { opacity: 0; visibility: hidden; } }
        @keyframes scaleUp { from { transform: scale(0.9); opacity: 0; filter: blur(10px); } to { transform: scale(1); opacity: 1; filter: blur(0px); } }
    </style>
</head>
<body>
    <div class="bg-shapes">
        <div class="shape shape-1"></div>
        <div class="shape shape-2"></div>
        <div class="shape shape-3"></div>
    </div>

    <div class="welcome-overlay">
        <h1>Welcome home, Master.</h1>
        <p><i class="fas fa-circle-notch fa-spin"></i> Initializing Environment Control</p>
    </div>

    <div class="container animate-up delay-1">
        <div class="header animate-up delay-1">
            <h1 class="dash-title">
                <span class="logo-stack">
                    <i class="fas fa-house-chimney"></i>
                    <i class="fas fa-microphone-alt"></i>
                </span>
                Smart Home
            </h1>
            <div class="header-right">
                <div class="theme-switcher">
                    <button class="theme-btn" data-theme-target="sunrise" onclick="setTheme('sunrise')" title="Sunrise Mode"><i class="fas fa-sun"></i></button>
                    <button class="theme-btn" data-theme-target="light" onclick="setTheme('light')" title="Light Mode"><i class="fas fa-desktop"></i></button>
                    <button class="theme-btn" data-theme-target="dark" onclick="setTheme('dark')" title="Dark Mode"><i class="fas fa-moon"></i></button>
                </div>
                <div class="status-badge"><i class="fas fa-circle check" style="margin-right:5px; color:var(--card-on-text);"></i> System Online</div>
            </div>
        </div>
        
        <div class="grid">
            <div class="panel animate-up delay-2">
                <h2><i class="fas fa-microphone-lines"></i> Input Array</h2>
                
                <button class="voice-btn" id="voiceBtn" onclick="triggerVoice()">
                    <i class="fas fa-microphone"></i> Manual Mic Override
                </button>

                <button class="voice-btn" id="wakeWordBtn" onclick="toggleWakeWord()">
                    <i class="fas fa-ear-listen"></i> Enable Wake Word
                </button>
                
                <div class="input-group">
                    <input type="text" id="textCmd" placeholder="Inject command string..." onkeypress="if(event.key === 'Enter') sendText()">
                    <button class="send-btn" onclick="sendText()"><i class="fas fa-paper-plane"></i></button>
                </div>

                <div class="slider-container">
                    <i class="fas fa-volume-down" style="color: var(--text-muted); font-size: 1.2rem;"></i>
                    <input type="range" id="volSlider" min="0.0" max="1.0" step="0.05" value="0.25" onchange="updateVolume(this.value)">
                    <span id="volDisplay" style="width: 50px; text-align: right; font-family: monospace; font-weight: 700; color: var(--text-main);">25%</span>
                </div>
            </div>
            
            <div class="panel animate-up delay-3">
                <h2><i class="fas fa-microchip"></i> Hardware Control</h2>
                <div class="hw-grid">
                    <div class="device-card" id="card-LIGHT" onclick="toggleDevice('LIGHT')">
                        <i class="fas fa-lightbulb"></i>
                        <div class="device-name">Smart Light</div>
                        <div class="device-state" id="state-LIGHT">OFF</div>
                    </div>
                    <div class="device-card" id="card-FAN" onclick="toggleDevice('FAN')">
                        <i class="fas fa-fan"></i>
                        <div class="device-name">Ceiling Fan</div>
                        <div class="device-state" id="state-FAN">OFF</div>
                    </div>
                    <div class="device-card" id="card-TELEVISION" onclick="toggleDevice('TELEVISION')">
                        <i class="fas fa-tv"></i>
                        <div class="device-name">Television</div>
                        <div class="device-state" id="state-TELEVISION">OFF</div>
                    </div>
                    <div class="device-card music-card" onclick="sendDirect('MUSIC_PLAY')">
                        <i class="fas fa-music"></i>
                        <div class="device-name">Media Player</div>
                        <div class="device-state">PLAY AUDIO</div>
                    </div>
                </div>
            </div>
        </div>

        <div class="panel animate-up delay-4" style="margin-top: 25px;">
            <h2><i class="fas fa-terminal"></i> Activity Log</h2>
            <div id="log-window"></div>
        </div>
    </div>

    <script>
        // --- Theme Engine ---
        function setTheme(themeName) {
            document.documentElement.setAttribute('data-theme', themeName);
            localStorage.setItem('shva_theme', themeName);
            
            document.querySelectorAll('.theme-btn').forEach(btn => btn.classList.remove('active'));
            document.querySelector(`.theme-btn[data-theme-target="${themeName}"]`).classList.add('active');
        }
        
        // Load saved theme immediately
        const savedTheme = localStorage.getItem('shva_theme') || 'sunrise';
        setTheme(savedTheme);

        // --- Application Logic ---
        const logWindow = document.getElementById('log-window');
        let currentDeviceStates = { "LIGHT": "OFF", "FAN": "OFF", "TELEVISION": "OFF" };
        let logIndex = 0;

        window.onload = () => {
            fetchData();
            setTimeout(() => {
                appendLogRaw(new Date().toLocaleTimeString('en-US', { hour12: false }), "<span class='log-normal'>Connecting to internal broker on 10.194.186.2...</span>");
                setTimeout(() => {
                    appendLogRaw(new Date().toLocaleTimeString('en-US', { hour12: false }), "<span class='log-success'>[Success] Voice & Text System Initialized. Welcome home, Master.</span>");
                }, 800);
            }, 500);
            
            setInterval(fetchData, 2000); 
        };

        function fetchData() {
            fetch('/api/data')
                .then(res => res.json())
                .then(data => {
                    updateUI(data.states);
                    
                    const volSlider = document.getElementById('volSlider');
                    const volDisplay = document.getElementById('volDisplay');
                    if (data.volume !== undefined && !volSlider.matches(':active')) {
                        const newVol = data.volume / 100;
                        if (Math.abs(volSlider.value - newVol) > 0.01) {
                            volSlider.value = newVol;
                            volDisplay.innerText = data.volume + "%";
                        }
                    }

                    if (data.logs && data.logs.length > logIndex) {
                        for (let i = logIndex; i < data.logs.length; i++) {
                            appendLogRaw(data.logs[i].time, data.logs[i].msg);
                        }
                        logIndex = data.logs.length;
                    }
                })
                .catch(err => console.error("Poll error:", err));
        }

        function appendLogRaw(timeStr, msg) {
            const div = document.createElement('div');
            div.className = 'log-entry';
            div.innerHTML = `<span class="log-time">[${timeStr}]</span> ${msg}`;
            logWindow.appendChild(div);
            logWindow.scrollTo({ top: logWindow.scrollHeight, behavior: 'smooth' });
        }

        function updateUI(states) {
            if (!states) return;
            currentDeviceStates = states;
            const devices = ['LIGHT', 'FAN', 'TELEVISION'];
            
            devices.forEach(device => {
                const card = document.getElementById(`card-${device}`);
                const stateText = document.getElementById(`state-${device}`);
                if (card && stateText) {
                    if (states[device] === 'ON') {
                        card.classList.add('is-on');
                        stateText.innerText = 'ON';
                    } else {
                        card.classList.remove('is-on');
                        stateText.innerText = 'OFF';
                    }
                }
            });
        }

        function toggleWakeWord() {
            const btn = document.getElementById('wakeWordBtn');
            const isActive = btn.classList.contains('active-wake');
            const newState = !isActive;
            
            fetch('/api/toggle_wakeword', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ state: newState })
            })
            .then(res => res.json())
            .then(data => {
                if (data.status === "active") {
                    btn.classList.add('active-wake');
                    btn.innerHTML = "<i class='fas fa-ear-listen fa-pulse'></i> Wake Word Active";
                } else {
                    btn.classList.remove('active-wake');
                    btn.innerHTML = "<i class='fas fa-ear-listen'></i> Enable Wake Word";
                }
            });
        }

        function toggleDevice(device) {
            const targetState = currentDeviceStates[device] === 'ON' ? 'OFF' : 'ON';
            sendDirect(`${device}_${targetState}`);
        }

        function triggerVoice() {
            const btn = document.getElementById('voiceBtn');
            btn.innerHTML = "<i class='fas fa-spinner fa-spin'></i> Awaiting Audio...";
            btn.disabled = true;

            fetch('/api/voice')
                .then(res => res.json())
                .then(data => {
                    btn.innerHTML = "<i class='fas fa-microphone'></i> Manual Mic Override";
                    btn.disabled = false;
                })
                .catch(err => {
                    btn.innerHTML = "<i class='fas fa-microphone'></i> Manual Mic Override";
                    btn.disabled = false;
                });
        }

        function sendText() {
            const inputEl = document.getElementById('textCmd');
            const cmdText = inputEl.value.trim();
            if(!cmdText) return;
            inputEl.value = "";
            
            fetch('/api/text', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ command: cmdText })
            });
        }

        function sendDirect(intent) {
            fetch('/api/direct', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ intent: intent })
            });
        }

        function updateVolume(val) {
            document.getElementById('volDisplay').innerText = Math.round(val * 100) + "%";
            fetch('/api/volume', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ volume: parseFloat(val) })
            });
        }
    </script>
</body>
</html>
"""

def startup_greeting():
    time.sleep(3.0)
    try:
        sh.speak_on_esp32("Welcome home, master")
    except Exception as e:
        print(f"[System Error]: {e}")

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/data', methods=['GET'])
def api_data():
    return jsonify({
        "states": device_states, 
        "logs": backend_logs,
        "volume": int(sh.current_volume * 100)
    })

@app.route('/api/toggle_wakeword', methods=['POST'])
def toggle_wakeword():
    global wake_word_active, wake_word_thread
    data = request.json
    action = data.get("state") 
    
    if action and not wake_word_active:
        wake_word_active = True
        wake_word_thread = threading.Thread(target=wake_word_loop, daemon=True)
        wake_word_thread.start()
        return jsonify({"status": "active"})
    elif not action and wake_word_active:
        wake_word_active = False
        return jsonify({"status": "inactive"})
        
    return jsonify({"status": "unchanged"})

@app.route('/api/voice', methods=['GET'])
def api_voice():
    add_log("<span class='log-system'>Opening socket to ESP32 INMP441 (Manual Override)...</span>")
    text = sh.listen()
    
    if not text:
        reply = "I didn't catch that."
        add_log("<span class='log-error'>[Error]: No speech detected.</span>")
        sh.speak_on_esp32(reply)
        return jsonify({"status": "success"})
    
    execute_command_pipeline(text)
    return jsonify({"status": "success"})

@app.route('/api/text', methods=['POST'])
def api_text():
    data = request.json
    text = data.get("command", "")
    add_log(f"<span class='log-normal'>[Sent text injection]: '{text}'</span>")
    execute_command_pipeline(text)
    return jsonify({"status": "success"})

@app.route('/api/direct', methods=['POST'])
def api_direct():
    data = request.json
    intent = data.get("intent", "")
    add_log(f"<span class='log-normal'>[Command]: Requesting hardware state: {intent}</span>")
    
    update_internal_states([intent])
    sh.publish_intent(intent)
    
    if intent.startswith("MUSIC_PLAY"):
        song_name = None
        if intent != "MUSIC_PLAY":
            song_name = intent.replace("MUSIC_PLAY_", "")
        threading.Thread(target=sh.play_music_on_esp32, args=(song_name,)).start()
        reply = "Playing music."
        add_log(f"<strong class='log-action'>[System Action]:</strong> <span class='log-normal'>{reply}</span>")
    else:
        reply = sh.reply_for_intent(intent) or f"Executed {intent}."
        add_log(f"<strong class='log-success'>[Success]:</strong> <span class='log-normal'>{reply}</span>")
        sh.speak_on_esp32(reply)
    
    return jsonify({"status": "success"})

@app.route('/api/volume', methods=['POST'])
def api_volume():
    data = request.json
    vol = data.get("volume", 0.25)
    sh.set_volume(vol)
    add_log(f"<span class='log-system'>[Config]: Adjusting output gain to {int(vol * 100)}%...</span>")
    return jsonify({"status": "success"})

if __name__ == '__main__':
    threading.Thread(target=startup_greeting, daemon=True).start()
    app.run(host='0.0.0.0', port=5000, debug=False)