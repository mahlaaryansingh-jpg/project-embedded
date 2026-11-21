#include <WiFiNINA.h>
#include <PubSubClient.h>
#include <Servo.h>
#include <DHT.h>

// ---------------- WIFI SETTINGS ----------------
const char* WIFI_SSID = "HARYANA";
const char* WIFI_PASSWORD = "aryan1234";

// ---------------- MQTT SETTINGS ----------------
const char* MQTT_SERVER = "192.168.43.206";
const int MQTT_PORT = 1883;

const char* MQTT_USER = "smartgarden";
const char* MQTT_PASSWORD = "Aryan@2421";

const char* STATUS_TOPIC = "smartgarden/status";
const char* COMMAND_TOPIC = "smartgarden/command";

// ---------------- PIN SETTINGS ----------------
#define RAIN_PIN 2
#define DHT_PIN 3
#define DHT_TYPE DHT22

#define SOIL_PIN A0

#define RED_LED 5
#define GREEN_LED 6
#define BUZZER_PIN 7

#define CLOTHESLINE_SERVO_PIN 9
#define WALL_SERVO_PIN 10

// ---------------- OBJECTS ----------------
WiFiClient wifiClient;
PubSubClient mqtt(wifiClient);

DHT dht(DHT_PIN, DHT_TYPE);

Servo clotheslineServo;
Servo wallServo;

// ---------------- SENSOR VALUES ----------------
int soilValue = 0;
int soilThreshold = 450;

bool rainDetected = false;
bool soilWet = false;

float humidity = 0;
float temperature = 0;

// Assumed servo positions.
// Check that these match your physical mechanism.
int clotheslineAngle = 0;
int wallAngle = 0;

// ---------------- MOTOR STATES ----------------
enum MotorState {
  IDLE,
  CLOSING_CLOTHESLINE,
  RAISING_WALL,
  PROTECTED,
  LOWERING_WALL,
  EXPANDING_CLOTHESLINE
};

MotorState motorState = IDLE;

unsigned long motorTimer = 0;
unsigned long lastSensorRead = 0;
unsigned long lastStatusPublish = 0;
unsigned long lastMqttAttempt = 0;

const unsigned long MOTOR_WAIT = 2000;
const unsigned long SENSOR_INTERVAL = 2000;
const unsigned long STATUS_INTERVAL = 2000;

bool protectionActive = false;
bool rainAlarmActive = false;

// ---------------- SENSOR READING ----------------
void readSensors() {
  // Assumes LOW means rain detected.
  rainDetected = (digitalRead(RAIN_PIN) == LOW);

  soilValue = analogRead(SOIL_PIN);

  // Starting assumption: lower reading means wetter soil.
  soilWet = (soilValue < soilThreshold);

  humidity = dht.readHumidity();
  temperature = dht.readTemperature();

  Serial.println("------------------------");
  Serial.print("Rain detected: ");
  Serial.println(rainDetected);

  Serial.print("Soil value: ");
  Serial.println(soilValue);

  Serial.print("Soil wet: ");
  Serial.println(soilWet);

  if (!isnan(humidity) && !isnan(temperature)) {
    Serial.print("Humidity: ");
    Serial.print(humidity);
    Serial.println("%");

    Serial.print("Temperature: ");
    Serial.print(temperature);
    Serial.println(" C");
  } else {
    Serial.println("DHT22 reading unavailable");
  }
}

// ---------------- LED AND BUZZER ----------------
void updateIndicators() {
  if (rainDetected || soilWet) {
    digitalWrite(RED_LED, HIGH);
    digitalWrite(GREEN_LED, LOW);
  } else {
    digitalWrite(RED_LED, LOW);
    digitalWrite(GREEN_LED, HIGH);
  }

  if (soilWet || rainAlarmActive) {
    tone(BUZZER_PIN, 2000);
  } else {
    noTone(BUZZER_PIN);
  }
}

// ---------------- MQTT COMMAND CALLBACK ----------------
void mqttCallback(char* topic, byte* payload, unsigned int length) {
  String command = "";

  for (unsigned int i = 0; i < length; i++) {
    command += (char)payload[i];
  }

  command.trim();

  Serial.print("Received command: ");
  Serial.println(command);

  // Do not allow manual operation during automatic rain protection.
  if (rainDetected || motorState != IDLE || protectionActive) {
    Serial.println("Manual command ignored: automatic protection is active.");
    return;
  }

  if (command == "CLOSE_CLOTHESLINE") {
    clotheslineServo.write(90);
    clotheslineAngle = 90;
  }

  else if (command == "EXPAND_CLOTHESLINE") {
    clotheslineServo.write(0);
    clotheslineAngle = 0;
  }

  else if (command == "RAISE_WALL") {
    wallServo.write(180);
    wallAngle = 180;
  }

  else if (command == "LOWER_WALL") {
    wallServo.write(0);
    wallAngle = 0;
  }
}

// ---------------- WIFI CONNECTION ----------------
void connectWiFi() {
  Serial.print("Connecting to Wi-Fi");

  while (WiFi.status() != WL_CONNECTED) {
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

    unsigned long startAttempt = millis();

    while (WiFi.status() != WL_CONNECTED &&
           millis() - startAttempt < 10000) {
      delay(500);
      Serial.print(".");
    }
  }

  Serial.println();
  Serial.println("Wi-Fi connected!");

  Serial.print("Arduino IP: ");
  Serial.println(WiFi.localIP());
}

// ---------------- MQTT CONNECTION ----------------
void reconnectMQTT() {
  if (mqtt.connected()) {
    return;
  }

  if (millis() - lastMqttAttempt < 5000) {
    return;
  }

  lastMqttAttempt = millis();

  Serial.println("Connecting to MQTT...");

  if (mqtt.connect("SmartRainArduino", MQTT_USER, MQTT_PASSWORD)) {
    Serial.println("MQTT connected!");

    mqtt.subscribe(COMMAND_TOPIC);
  } else {
    Serial.print("MQTT connection failed. State: ");
    Serial.println(mqtt.state());
  }
}

// ---------------- AUTOMATIC MOTOR CONTROL ----------------
void automaticMotorControl() {

  // Start rain protection when rain is detected.
  if (rainDetected && motorState == IDLE && !protectionActive) {

    Serial.println("RAIN DETECTED: Starting protection.");

    protectionActive = true;
    rainAlarmActive = true;

    clotheslineServo.write(90);
    clotheslineAngle = 90;

    motorState = CLOSING_CLOTHESLINE;
    motorTimer = millis();
  }

  // Wait for clothesline to close.
  if (motorState == CLOSING_CLOTHESLINE) {

    if (millis() - motorTimer >= MOTOR_WAIT) {

      wallServo.write(180);
      wallAngle = 180;

      motorState = RAISING_WALL;
      motorTimer = millis();

      Serial.println("Raising protective wall.");
    }
  }

  // Wait for protective wall to raise.
  else if (motorState == RAISING_WALL) {

    if (millis() - motorTimer >= MOTOR_WAIT) {

      motorState = PROTECTED;
      rainAlarmActive = false;

      Serial.println("Rain protection completed.");
    }
  }

  // When rain stops, restore the system.
  if (!rainDetected && motorState == PROTECTED) {

    Serial.println("Rain stopped: Restoring system.");

    rainAlarmActive = false;

    wallServo.write(0);
    wallAngle = 0;

    motorState = LOWERING_WALL;
    motorTimer = millis();
  }

  // Wait for wall to lower.
  else if (motorState == LOWERING_WALL) {

    if (millis() - motorTimer >= MOTOR_WAIT) {

      clotheslineServo.write(0);
      clotheslineAngle = 0;

      motorState = EXPANDING_CLOTHESLINE;
      motorTimer = millis();

      Serial.println("Expanding clothesline.");
    }
  }

  // Wait for clothesline to expand.
  else if (motorState == EXPANDING_CLOTHESLINE) {

    if (millis() - motorTimer >= MOTOR_WAIT) {

      motorState = IDLE;
      protectionActive = false;

      Serial.println("System returned to normal.");
    }
  }
}

// ---------------- MQTT STATUS PUBLISH ----------------
void publishStatus() {

  if (!mqtt.connected()) {
    return;
  }

  char message[300];

  snprintf(
    message,
    sizeof(message),
    "{\"rain\":%s,\"soilWet\":%s,\"soilValue\":%d,"
    "\"humidity\":%.1f,\"temperature\":%.1f,"
    "\"redLed\":%s,\"greenLed\":%s,\"buzzer\":%s,"
    "\"clotheslineAngle\":%d,\"wallAngle\":%d,"
    "\"motorState\":%d}",
    rainDetected ? "true" : "false",
    soilWet ? "true" : "false",
    soilValue,
    isnan(humidity) ? 0.0 : humidity,
    isnan(temperature) ? 0.0 : temperature,
    (rainDetected || soilWet) ? "true" : "false",
    (!rainDetected && !soilWet) ? "true" : "false",
    (soilWet || rainAlarmActive) ? "true" : "false",
    clotheslineAngle,
    wallAngle,
    (int)motorState
  );

  mqtt.publish(STATUS_TOPIC, message);
}

// ---------------- SETUP ----------------
void setup() {
  Serial.begin(9600);

  pinMode(RAIN_PIN, INPUT);
  pinMode(RED_LED, OUTPUT);
  pinMode(GREEN_LED, OUTPUT);
  pinMode(BUZZER_PIN, OUTPUT);

  clotheslineServo.attach(CLOTHESLINE_SERVO_PIN);
  wallServo.attach(WALL_SERVO_PIN);

  clotheslineServo.write(0);
  wallServo.write(0);

  dht.begin();

  mqtt.setServer(MQTT_SERVER, MQTT_PORT);
  mqtt.setCallback(mqttCallback);

  connectWiFi();
}

// ---------------- MAIN LOOP ----------------
void loop() {

  if (WiFi.status() != WL_CONNECTED) {
    connectWiFi();
  }

  reconnectMQTT();
  mqtt.loop();

  if (millis() - lastSensorRead >= SENSOR_INTERVAL) {
    lastSensorRead = millis();
    readSensors();
  }

  automaticMotorControl();
  updateIndicators();

  if (millis() - lastStatusPublish >= STATUS_INTERVAL) {
    lastStatusPublish = millis();
    publishStatus();
  }
}