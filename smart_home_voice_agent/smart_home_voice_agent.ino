#include <WiFi.h>
#include <PubSubClient.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <DHT.h>
#include <driver/i2s.h>
#include <math.h>
#include <time.h>
 
 
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
 
 
const char* ssid = "POCO F5";
const char* password = "minecraft";
 
 
const char* mqtt_server = "10.194.186.2";
 
const long gmtOffsetSeconds = 8 * 60 * 60;
const int daylightOffsetSeconds = 0;
 
#define DHTPIN 4
#define DHTTYPE DHT22
#define LIGHT_PIN 18
#define FAN_PIN 19
 
#define MIC_PORT I2S_NUM_0
#define MIC_WS   32
#define MIC_SD   35
#define MIC_SCK  26
 
#define SPK_PORT I2S_NUM_1
#define SPK_DIN   23
#define SPK_LRC   27
#define SPK_BCLK  14
#define SPK_SD    33
 
#define SAMPLE_RATE 16000
#define BUFFER_LEN 512
#define MIC_GAIN 1
 
 
#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
#define OLED_ADDRESS 0x3C
 
WiFiClient espClient;
PubSubClient client(espClient);
LiquidCrystal_I2C lcd(0x27, 16, 2);
DHT dht(DHTPIN, DHTTYPE);
TwoWire oledWire = TwoWire(1);
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &oledWire, -1);
 
 
WiFiServer micServer(3333);
WiFiServer speakerServer(3334);
 
bool lightState = false;
bool fanState = false;
bool tvState = false;
float temperature = NAN;
float humidity = NAN;
unsigned long lastDHTRead = 0;
const unsigned long dhtInterval = 3000;
unsigned long lastLCDUpdate = 0;
const unsigned long lcdInterval = 1000;
unsigned long lastMqttReconnectAttempt = 0;
const unsigned long mqttReconnectInterval = 5000;
unsigned long lastOledUpdate = 0;
const unsigned long oledInterval = 20;
bool oledReady = false;
enum OledMode { OLED_OFF, OLED_POKEBALL, OLED_FLASH, OLED_PIKACHU };
OledMode oledMode = OLED_OFF;
unsigned long oledPhaseStarted = 0;
int oledFlashCount = 0;
bool oledFlashVisible = false;
const unsigned long pikachuHoldMs = 3000;
const unsigned long oledRepeatPauseMs = 0;
 
 
void updateLCD() {
  struct tm timeinfo;
  char line1[17];
  char line2[17];
 
  if (getLocalTime(&timeinfo, 20)) {
    snprintf(line1, sizeof(line1), "%02d/%02d/%02d %02d:%02d",
             timeinfo.tm_mday,
             timeinfo.tm_mon + 1,
             (timeinfo.tm_year + 1900) % 100,
             timeinfo.tm_hour,
             timeinfo.tm_min);
  } else {
    snprintf(line1, sizeof(line1), "Time syncing...");
  }
 
  if (!isnan(temperature) && !isnan(humidity)) {
    snprintf(line2, sizeof(line2), "T:%2.1fC H:%2.0f%%", temperature, humidity);
  } else {
    snprintf(line2, sizeof(line2), "T:--.-C H:--%%");
  }
 
  lcd.setCursor(0, 0);
  lcd.print(line1);
  for (int i = strlen(line1); i < 16; i++) lcd.print(" ");
 
  lcd.setCursor(0, 1);
  lcd.print(line2);
  for (int i = strlen(line2); i < 16; i++) lcd.print(" ");
}
 
 
void drawPokeball() {
  display.clearDisplay();
  display.drawCircle(64, 32, 20, WHITE);
  display.drawLine(44, 32, 84, 32, WHITE);
  display.fillCircle(64, 32, 4, WHITE);
  display.drawCircle(64, 32, 6, WHITE);
  display.display();
}
 
void drawFlash() {
  display.clearDisplay();
  for (int i = 0; i < 30; i++) {
    display.drawLine(64, 32, random(0, 128), random(0, 64), WHITE);
  }
  display.display();
}
 
void drawPikachu() {
  display.clearDisplay();
 
  display.drawCircle(64, 24, 16, WHITE);
  display.drawTriangle(50, 16, 44, 2, 56, 8, WHITE);
  display.drawTriangle(78, 16, 84, 2, 72, 8, WHITE);
 
  display.fillCircle(58, 22, 2, WHITE);
  display.fillCircle(70, 22, 2, WHITE);
  display.drawLine(60, 28, 64, 30, WHITE);
  display.drawLine(68, 28, 64, 30, WHITE);
  display.drawCircle(54, 28, 2, WHITE);
  display.drawCircle(74, 28, 2, WHITE);
 
  display.fillRoundRect(52, 36, 24, 18, 6, WHITE);
  display.drawLine(52, 40, 44, 38, WHITE);
  display.drawLine(76, 40, 84, 38, WHITE);
  display.drawLine(56, 54, 54, 60, WHITE);
  display.drawLine(72, 54, 74, 60, WHITE);
 
  display.drawLine(76, 48, 86, 44, WHITE);
  display.drawLine(86, 44, 90, 50, WHITE);
  display.drawLine(90, 50, 94, 46, WHITE);
  display.drawLine(94, 46, 98, 52, WHITE);
 
  display.display();
}
 
void startTvOledAnimation() {
  tvState = true;
  if (!oledReady) return;
 
  oledMode = OLED_POKEBALL;
  oledPhaseStarted = millis();
  oledFlashCount = 0;
  oledFlashVisible = false;
  drawPokeball();
}
 
void stopTvOled() {
  tvState = false;
  oledMode = OLED_OFF;
  if (!oledReady) return;
 
  display.clearDisplay();
  display.display();
}
 
void updateOLED() {
  if (!oledReady || !tvState) return;
 
  unsigned long now = millis();
 
  if (oledMode == OLED_POKEBALL && now - oledPhaseStarted >= 1500) {
    oledMode = OLED_FLASH;
    oledPhaseStarted = now;
    oledFlashCount = 0;
    oledFlashVisible = false;
  }
 
  if (oledMode == OLED_FLASH) {
    if (!oledFlashVisible && now - oledPhaseStarted >= 40) {
      drawFlash();
      oledFlashVisible = true;
      oledPhaseStarted = now;
      return;
    }
 
    if (oledFlashVisible && now - oledPhaseStarted >= 80) {
      display.clearDisplay();
      display.display();
      oledFlashVisible = false;
      oledPhaseStarted = now;
      oledFlashCount++;
 
      if (oledFlashCount >= 8) {
        oledMode = OLED_PIKACHU;
        oledPhaseStarted = now;
        drawPikachu();
      }
    }
  }
 
  if (oledMode == OLED_PIKACHU && now - oledPhaseStarted >= pikachuHoldMs + oledRepeatPauseMs) {
    oledMode = OLED_POKEBALL;
    oledPhaseStarted = now;
    oledFlashCount = 0;
    oledFlashVisible = false;
    drawPokeball();
  }
}
 
 
void callback(char* topic, byte* payload, unsigned int length) {
  String message = "";
  for (unsigned int i = 0; i < length; i++) {
    message += (char)payload[i];
  }
  Serial.print("Topic: ");
  Serial.println(topic);
  Serial.print("Message: ");
  Serial.println(message);
 
  if (String(topic) == "home/light") {
    if (message == "ON") {
      digitalWrite(LIGHT_PIN, LOW);
      lightState = true;
    } else if (message == "OFF") {
      digitalWrite(LIGHT_PIN, LOW);
      lightState = false;
    }
  }

  if (String(topic) == "home/light") {
    if (message == "ON") {
      digitalWrite(LIGHT_PIN, HIGH); // Changed to HIGH to activate TIP31C
      lightState = true;
    } else if (message == "OFF") {
      digitalWrite(LIGHT_PIN, LOW);  // Keeps it OFF
      lightState = false;
    }
  }
 
  if (String(topic) == "home/tv") {
    if (message == "ON") {
      startTvOledAnimation();
    } else if (message == "OFF") {
      stopTvOled();
    }
    Serial.print("TV state: ");
    Serial.println(tvState ? "ON" : "OFF");
  }

  if (String(topic) == "home/fan") {
    if (message == "ON") {
      digitalWrite(FAN_PIN, HIGH);
      fanState = true;
    } else if (message == "OFF") {
      digitalWrite(FAN_PIN, LOW);
      fanState = false;
    }
    Serial.print("Fan state: ");
    Serial.println(fanState ? "ON" : "OFF");
  }
 
  if (String(topic) == "home/request" && message == "temperature") {
    String tempMessage = String(temperature, 1) + "," + String(humidity, 1);
    client.publish("home/temperature", tempMessage.c_str());
    Serial.print("Temperature sent: ");
    Serial.println(tempMessage);
  }
 
  updateLCD();
}
 
 
void reconnect() {
  if (client.connected()) {
    return;
  }
 
  if (millis() - lastMqttReconnectAttempt < mqttReconnectInterval) {
    return;
  }
  lastMqttReconnectAttempt = millis();
 
  Serial.print("Attempting MQTT connection...");
  if (client.connect("ESP32Client")) {
    Serial.println("connected");
    client.subscribe("home/light");
    client.subscribe("home/fan");
    client.subscribe("home/request");
    client.subscribe("home/tv");
    updateLCD();
    updateOLED();
  } else {
    Serial.print("failed, rc=");
    Serial.print(client.state());
    Serial.println(" try again in 5 seconds");
  }
}
 
 
void setupMic() {
  i2s_config_t config = {
    .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX),
    .sample_rate = SAMPLE_RATE,
    .bits_per_sample = I2S_BITS_PER_SAMPLE_32BIT,
    .channel_format = I2S_CHANNEL_FMT_ONLY_LEFT,
    .communication_format = I2S_COMM_FORMAT_I2S,
    .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
    .dma_buf_count = 8,
    .dma_buf_len = BUFFER_LEN,
    .use_apll = false,
    .tx_desc_auto_clear = false,
    .fixed_mclk = 0
  };
  i2s_pin_config_t pins;
  pins.bck_io_num = MIC_SCK;
  pins.ws_io_num = MIC_WS;
  pins.data_out_num = I2S_PIN_NO_CHANGE;
  pins.data_in_num = MIC_SD;
  pins.mck_io_num = I2S_PIN_NO_CHANGE;
  i2s_driver_install(MIC_PORT, &config, 0, NULL);
  i2s_set_pin(MIC_PORT, &pins);
}
 
 
void setupSpeaker() {
  pinMode(SPK_SD, OUTPUT);
  digitalWrite(SPK_SD, HIGH);
  delay(50);
  i2s_config_t config = {
    .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_TX),
    .sample_rate = SAMPLE_RATE,
    .bits_per_sample = I2S_BITS_PER_SAMPLE_16BIT,
    .channel_format = I2S_CHANNEL_FMT_ONLY_LEFT,
    .communication_format = I2S_COMM_FORMAT_I2S,
    .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
    .dma_buf_count = 8,
    .dma_buf_len = BUFFER_LEN,
    .use_apll = false,
    .tx_desc_auto_clear = false,
    .fixed_mclk = 0
  };
  i2s_pin_config_t pins;
  pins.bck_io_num = SPK_BCLK;
  pins.ws_io_num = SPK_LRC;
  pins.data_out_num = SPK_DIN;
  pins.data_in_num = I2S_PIN_NO_CHANGE;
  pins.mck_io_num = I2S_PIN_NO_CHANGE;
  i2s_driver_install(SPK_PORT, &config, 0, NULL);
  i2s_set_pin(SPK_PORT, &pins);
  i2s_set_clk(SPK_PORT, SAMPLE_RATE, I2S_BITS_PER_SAMPLE_16BIT, I2S_CHANNEL_MONO);
  i2s_zero_dma_buffer(SPK_PORT);
}
 
void playPCM(const uint8_t* data, size_t len) {
  i2s_start(SPK_PORT);
  size_t written = 0;
  i2s_write(SPK_PORT, data, len, &written, portMAX_DELAY);
  int delayMs = (int)(len * 1000 / (SAMPLE_RATE * 2)) + 250;
  delay(delayMs);
  i2s_stop(SPK_PORT);
  i2s_zero_dma_buffer(SPK_PORT);
}
 
void playStartupBeep() {
  const float freq = 880.0f;
  const int totalSamples = SAMPLE_RATE / 3;
  int16_t* samples = (int16_t*)malloc(totalSamples * sizeof(int16_t));
  if (!samples) {
    Serial.println("Startup beep allocation failed.");
    return;
  }
  Serial.println("Playing MAX98357 startup beep...");
  for (int i = 0; i < totalSamples; i++) {
    float t = (float)i / SAMPLE_RATE;
    samples[i] = (int16_t)(sinf(2.0f * PI * freq * t) * 9000.0f);
  }
  playPCM((const uint8_t*)samples, totalSamples * sizeof(int16_t));
  free(samples);
}
 
void streamMicToClient(WiFiClient micClient) {
  Serial.println("Laptop connected for INMP441 recording.");
  int32_t mic32[BUFFER_LEN];
  int16_t mic16[BUFFER_LEN];
  static int32_t dcOffset = 0;
  while (micClient.connected()) {
    size_t bytesRead = 0;
    i2s_read(MIC_PORT, mic32, sizeof(mic32), &bytesRead, portMAX_DELAY);
    int samples = bytesRead / sizeof(int32_t);
    for (int i = 0; i < samples; i++) {
      int32_t raw = mic32[i] >> 16;
      dcOffset = dcOffset + ((raw - dcOffset) >> 8);
      int32_t s = (raw - dcOffset) * MIC_GAIN;
      if (s > 32767) s = 32767;
      if (s < -32768) s = -32768;
      mic16[i] = (int16_t)s;
    }
    micClient.write((uint8_t*)mic16, samples * sizeof(int16_t));
  }
  micClient.stop();
  Serial.println("INMP441 recording finished.");
}
 
void playAudioFromClient(WiFiClient speakerClient) {
  Serial.println("Laptop connected for MAX98357 playback.");
  uint8_t firstBytes[4];
  if (speakerClient.readBytes(firstBytes, 4) != 4) {
    Serial.println("Failed to read speaker audio.");
    speakerClient.stop();
    return;
  }
  uint32_t audioLen = 0;
  memcpy(&audioLen, firstBytes, 4);
  if (audioLen == 0 || audioLen > 300000) {
    Serial.println("No valid length header, playing direct PCM stream.");
    uint8_t pcmBytes[1024];
    size_t written = 0;
    unsigned long lastDataMs = millis();
    i2s_start(SPK_PORT);
    i2s_write(SPK_PORT, firstBytes, 4, &written, portMAX_DELAY);
    while (speakerClient.connected() || speakerClient.available() > 0) {
      int availableBytes = speakerClient.available();
      if (availableBytes > 0) {
        int n = speakerClient.read(pcmBytes, min(availableBytes, (int)sizeof(pcmBytes)));
        if (n > 0) {
          if (n % 2 != 0) n--;
          i2s_write(SPK_PORT, pcmBytes, n, &written, portMAX_DELAY);
          lastDataMs = millis();
        }
      } else {
        if (millis() - lastDataMs > 1200) break;
        delay(1);
      }
    }
    delay(300);
    i2s_stop(SPK_PORT);
    i2s_zero_dma_buffer(SPK_PORT);
    speakerClient.stop();
    Serial.println("MAX98357 direct playback finished.");
    return;
  }
  uint8_t* audioData = (uint8_t*)malloc(audioLen);
  if (!audioData) {
    Serial.println("Failed to allocate speaker buffer.");
    speakerClient.stop();
    return;
  }
  size_t received = 0;
  unsigned long startMs = millis();
  while (received < audioLen && millis() - startMs < 10000) {
    int n = speakerClient.read(audioData + received, audioLen - received);
    if (n > 0) {
      received += n;
    } else {
      delay(1);
    }
  }
  if (received == audioLen) {
    Serial.print("Playing PCM bytes: ");
    Serial.println(audioLen);
    playPCM(audioData, audioLen);
  } else {
    Serial.print("Incomplete speaker audio: ");
    Serial.print(received);
    Serial.print(" / ");
    Serial.println(audioLen);
  }
  free(audioData);
  speakerClient.stop();
  Serial.println("MAX98357 playback finished.");
}
 
 
void readDHTIfNeeded() {
  if (millis() - lastDHTRead < dhtInterval) return;
  lastDHTRead = millis();
  temperature = dht.readTemperature();
  humidity = dht.readHumidity();
  if (!isnan(temperature) && !isnan(humidity)) {
    Serial.print("Temperature: ");
    Serial.print(temperature);
    Serial.println(" C");
    Serial.print("Humidity: ");
    Serial.print(humidity);
    Serial.println(" %");
    updateLCD();
  } else {
    Serial.println("Failed to read from DHT22");
  }
}
 
 
void setup() {
  Serial.begin(115200);
  delay(1000);
 
 
  dht.begin();
 
  pinMode(LIGHT_PIN, OUTPUT);
  pinMode(FAN_PIN, OUTPUT);
  digitalWrite(LIGHT_PIN, LOW);
  digitalWrite(FAN_PIN, LOW);
 
 
  Wire.begin(21, 22);
  lcd.init();
  lcd.backlight();
  lcd.setCursor(0, 0);
  lcd.print("Connecting...");
  lcd.setCursor(0, 1);
  lcd.print("Please Wait");
 
  setupMic();
  setupSpeaker();
  playStartupBeep();
 
 
  oledWire.begin(17, 25);
  if (!display.begin(SSD1306_SWITCHCAPVCC, OLED_ADDRESS)) {
    Serial.println("OLED init failed");
    oledReady = false;
  } else {
    oledReady = true;
    randomSeed(millis());
    display.clearDisplay();
    display.setTextSize(1);
    display.setTextColor(SSD1306_WHITE);
    display.setCursor(20, 20);
    display.println("TV Ready");
    display.display();
    delay(1000);
    updateOLED();
  }
 
 
  WiFi.begin(ssid, password);
  unsigned long wifiStartMs = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - wifiStartMs < 20000) {
    delay(500);
    Serial.print(".");
    readDHTIfNeeded();
    updateLCD();
  }
 
  Serial.println();
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("WiFi connected");
    WiFi.setSleep(false);
    configTime(gmtOffsetSeconds, daylightOffsetSeconds, "pool.ntp.org", "time.nist.gov");
    Serial.print("ESP32 IP: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("WiFi not connected, continuing without time sync.");
    lcd.setCursor(0, 0);
    lcd.print("WiFi not ready ");
    lcd.setCursor(0, 1);
    lcd.print("DHT still works ");
    delay(1200);
    updateLCD();
  }
 
 
  client.setServer(mqtt_server, 1883);
  client.setCallback(callback);
 
  micServer.begin();
  speakerServer.begin();
  Serial.println("INMP441 mic server: port 3333");
  Serial.println("MAX98357 speaker server: port 3334");
 
  updateLCD();
}
 
 
void loop() {
 
  if (!client.connected()) {
    reconnect();
  }
  client.loop();
 
  WiFiClient micClient = micServer.available();
  if (micClient) {
    streamMicToClient(micClient);
  }
 
  WiFiClient speakerClient = speakerServer.available();
  if (speakerClient) {
    playAudioFromClient(speakerClient);
  }
 
 
  readDHTIfNeeded();
 
  if (millis() - lastLCDUpdate > lcdInterval) {
    lastLCDUpdate = millis();
    updateLCD();
  }
 
 
  if (millis() - lastOledUpdate > oledInterval) {
    lastOledUpdate = millis();
    updateOLED();
  }
}
