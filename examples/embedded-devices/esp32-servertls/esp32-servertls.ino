/**
 * TESAIoT Platform - ESP32 Server TLS Client
 *
 * Connects to TESAIoT Platform using MQTTS with Server TLS authentication.
 * Publishes telemetry data every 10 seconds.
 *
 * Copyright (c) 2025 TESAIoT Platform (TESA)
 * Licensed under Apache License 2.0
 */

#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <time.h>

#include "config.h"
#include "ca_cert.h"

// Constants
#define TELEMETRY_INTERVAL 10000  // 10 seconds
#define MQTT_BUFFER_SIZE 512
#define NTP_SERVER "pool.ntp.org"

// Global objects
WiFiClientSecure espClient;
PubSubClient mqttClient(espClient);

// State variables
unsigned long lastTelemetryTime = 0;
bool timeInitialized = false;

/**
 * Initialize WiFi connection
 */
void setupWiFi() {
    Serial.println();
    Serial.print("Connecting to WiFi: ");
    Serial.println(WIFI_SSID);

    WiFi.mode(WIFI_STA);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

    int attempts = 0;
    while (WiFi.status() != WL_CONNECTED && attempts < 30) {
        delay(500);
        Serial.print(".");
        attempts++;
    }

    if (WiFi.status() == WL_CONNECTED) {
        Serial.println();
        Serial.println("WiFi connected!");
        Serial.print("IP address: ");
        Serial.println(WiFi.localIP());
        Serial.print("Signal strength (RSSI): ");
        Serial.print(WiFi.RSSI());
        Serial.println(" dBm");
    } else {
        Serial.println();
        Serial.println("WiFi connection failed!");
        ESP.restart();
    }
}

/**
 * Synchronize time using NTP
 */
void setupTime() {
    Serial.print("Synchronizing time with NTP...");

    configTime(0, 0, NTP_SERVER);

    time_t now = time(nullptr);
    int attempts = 0;
    while (now < 8 * 3600 * 2 && attempts < 20) {
        delay(500);
        Serial.print(".");
        now = time(nullptr);
        attempts++;
    }

    if (now > 8 * 3600 * 2) {
        timeInitialized = true;
        Serial.println(" done!");

        struct tm timeinfo;
        gmtime_r(&now, &timeinfo);
        Serial.print("Current time: ");
        Serial.println(asctime(&timeinfo));
    } else {
        Serial.println(" failed!");
        Serial.println("Warning: Time not synchronized, using epoch");
    }
}

/**
 * Setup TLS with CA certificate
 */
void setupTLS() {
    espClient.setCACert(CA_CERT);
    Serial.println("TLS configured with CA certificate");
}

/**
 * MQTT callback for incoming messages
 */
void mqttCallback(char* topic, byte* payload, unsigned int length) {
    Serial.print("Message received [");
    Serial.print(topic);
    Serial.print("]: ");

    // Convert payload to string
    char message[length + 1];
    memcpy(message, payload, length);
    message[length] = '\0';
    Serial.println(message);

    // Parse JSON command
    JsonDocument doc;
    DeserializationError error = deserializeJson(doc, message);

    if (!error) {
        const char* command = doc["command"];
        if (command) {
            Serial.print("Command: ");
            Serial.println(command);
            // Handle commands here
        }
    }
}

/**
 * Connect to MQTT broker
 */
bool connectMQTT() {
    if (mqttClient.connected()) {
        return true;
    }

    Serial.print("Connecting to MQTT broker...");

    // Generate client ID
    String clientId = String(DEVICE_ID);

    // Connect with credentials
    if (mqttClient.connect(clientId.c_str(), MQTT_USERNAME, MQTT_PASSWORD)) {
        Serial.println(" connected!");

        // Subscribe to command and config topics
        String commandTopic = String("device/") + DEVICE_ID + "/commands";
        String configTopic = String("device/") + DEVICE_ID + "/config";

        mqttClient.subscribe(commandTopic.c_str());
        mqttClient.subscribe(configTopic.c_str());

        Serial.println("Subscribed to:");
        Serial.println("  - " + commandTopic);
        Serial.println("  - " + configTopic);

        return true;
    } else {
        Serial.print(" failed, rc=");
        Serial.print(mqttClient.state());
        Serial.println();

        // Print error explanation
        switch (mqttClient.state()) {
            case -4: Serial.println("  -> Connection timeout"); break;
            case -3: Serial.println("  -> Connection lost"); break;
            case -2: Serial.println("  -> Connect failed"); break;
            case -1: Serial.println("  -> Disconnected"); break;
            case 1: Serial.println("  -> Bad protocol"); break;
            case 2: Serial.println("  -> Bad client ID"); break;
            case 3: Serial.println("  -> Unavailable"); break;
            case 4: Serial.println("  -> Bad credentials"); break;
            case 5: Serial.println("  -> Not authorized"); break;
        }

        return false;
    }
}

/**
 * Get current timestamp in ISO 8601 format
 */
String getTimestamp() {
    time_t now = time(nullptr);
    struct tm timeinfo;
    gmtime_r(&now, &timeinfo);

    char buffer[30];
    strftime(buffer, sizeof(buffer), "%Y-%m-%dT%H:%M:%SZ", &timeinfo);
    return String(buffer);
}

/**
 * Read simulated sensor data
 */
void readSensorData(float& temperature, float& humidity) {
    // Simulated values - replace with real sensor readings
    temperature = 25.0 + (random(0, 100) / 10.0) - 5.0;
    humidity = 60.0 + (random(0, 200) / 10.0) - 10.0;
}

/**
 * Publish telemetry data
 */
void publishTelemetry() {
    float temperature, humidity;
    readSensorData(temperature, humidity);

    // Build JSON payload
    JsonDocument doc;
    doc["device_id"] = DEVICE_ID;
    doc["timestamp"] = getTimestamp();

    JsonObject data = doc["data"].to<JsonObject>();
    data["temperature"] = temperature;
    data["humidity"] = humidity;
    data["wifi_rssi"] = WiFi.RSSI();
    data["heap_free"] = ESP.getFreeHeap();

    // Serialize to string
    char payload[MQTT_BUFFER_SIZE];
    serializeJson(doc, payload, sizeof(payload));

    // Publish to telemetry topic
    String topic = String("device/") + DEVICE_ID + "/telemetry";

    if (mqttClient.publish(topic.c_str(), payload)) {
        Serial.print("Published: ");
        Serial.println(payload);
    } else {
        Serial.println("Publish failed!");
    }
}

/**
 * Arduino setup function
 */
void setup() {
    Serial.begin(115200);
    delay(100);

    Serial.println();
    Serial.println("========================================");
    Serial.println("TESAIoT ESP32 Client (Server TLS)");
    Serial.print("Device ID: ");
    Serial.println(DEVICE_ID);
    Serial.println("========================================");

    // Initialize WiFi
    setupWiFi();

    // Synchronize time (required for TLS)
    setupTime();

    // Configure TLS
    setupTLS();

    // Configure MQTT
    mqttClient.setServer(MQTT_HOST, MQTT_PORT);
    mqttClient.setCallback(mqttCallback);
    mqttClient.setBufferSize(MQTT_BUFFER_SIZE);

    // Initial connection
    connectMQTT();

    Serial.println("Setup complete. Starting telemetry loop...");
    Serial.println();
}

/**
 * Arduino main loop
 */
void loop() {
    // Ensure MQTT connection
    if (!mqttClient.connected()) {
        if (!connectMQTT()) {
            delay(5000);
            return;
        }
    }

    // Process MQTT messages
    mqttClient.loop();

    // Publish telemetry at interval
    unsigned long currentTime = millis();
    if (currentTime - lastTelemetryTime >= TELEMETRY_INTERVAL) {
        lastTelemetryTime = currentTime;
        publishTelemetry();
    }

    // Small delay to prevent tight loop
    delay(10);
}
