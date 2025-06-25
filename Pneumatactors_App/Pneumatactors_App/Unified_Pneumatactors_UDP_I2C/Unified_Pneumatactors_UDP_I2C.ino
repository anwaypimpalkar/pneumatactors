#include <WiFi.h>
#include <WiFiUdp.h>
#include <Wire.h>
#include "lee_ventus_spm_i2c.h"

// --- WiFi Access Point credentials ---
const char* ssid = "PNEUMATACTORS_AP";
const char* password = "12345678";
const int udpPort = 4210;
WiFiUDP Udp;

// --- I2C and Device Addresses ---
#define SDA_PIN 6  // XIAO D4
#define SCL_PIN 7  // XIAO D5
#define PUMP1_ADDR 0x25
#define PUMP2_ADDR 0x26

// --- Pins ---
#define VALVE1_PIN 3
#define VALVE2_PIN 4

// --- Command structure ---
struct ActuatorCommand {
  volatile int valve1_freq;
  volatile int valve2_freq;
  volatile int pump1_pwm;
  volatile int pump2_pwm;
};

ActuatorCommand actuatorCmd = {0, 0, 0, 0};
SemaphoreHandle_t xMutex;
QueueHandle_t cmdQueue;

// --- I2C Scanner for Debug ---
void scanI2CBus() {
  for (byte addr = 1; addr < 127; ++addr) {
    Wire.beginTransmission(addr);
    if (Wire.endTransmission() == 0) {
      Serial.print("Found I2C device at 0x");
      Serial.println(addr, HEX);
    }
  }
}

// --- UDP Listener Task (Core 0) ---
void UDPTask(void *pvParameters) {
  WiFi.softAP(ssid, password);
  IPAddress ip = WiFi.softAPIP();
  Serial.print("SoftAP IP: ");
  Serial.println(ip);

  Udp.begin(udpPort);
  Serial.println("UDP listener started");

  char incoming[255];
  while (true) {
    int packetSize = Udp.parsePacket();
    if (packetSize) {
      int len = Udp.read(incoming, 255);
      if (len > 0) incoming[len] = 0;

      String cmdStr = String(incoming);
      cmdStr.replace("\n", "");
      cmdStr.replace("\r", "");
      cmdStr.replace(" ", "");

      if (cmdStr.length() == 12) {
        ActuatorCommand cmd;
        cmd.valve1_freq = cmdStr.substring(0, 3).toInt();
        cmd.valve2_freq = cmdStr.substring(3, 6).toInt();
        cmd.pump1_pwm   = cmdStr.substring(6, 9).toInt();
        cmd.pump2_pwm   = cmdStr.substring(9, 12).toInt();
        cmd.pump1_pwm = constrain(cmd.pump1_pwm, 0, 1000);
        cmd.pump2_pwm = constrain(cmd.pump2_pwm, 0, 1000);

        xQueueSend(cmdQueue, &cmd, portMAX_DELAY);
        Serial.printf("Parsed: V1=%d, V2=%d, P1=%d, P2=%d\n",
                      cmd.valve1_freq, cmd.valve2_freq, cmd.pump1_pwm, cmd.pump2_pwm);
      } else {
        Serial.println("Invalid UDP command length");
      }
    }
    vTaskDelay(pdMS_TO_TICKS(10));
  }
}

// --- Actuation Task (Core 1) ---
void ActuationTask(void *pvParameters) {
  pinMode(VALVE1_PIN, OUTPUT);
  pinMode(VALVE2_PIN, OUTPUT);

  unsigned long prevTimeValve1 = 0, prevTimeValve2 = 0;
  bool valve1State = false, valve2State = false;

  while (true) {
    ActuatorCommand receivedCmd;
    if (xQueueReceive(cmdQueue, &receivedCmd, 0)) {
      if (xSemaphoreTake(xMutex, portMAX_DELAY)) {
        actuatorCmd = receivedCmd;
        xSemaphoreGive(xMutex);
      }
    }

    int v1, v2, p1, p2;
    if (xSemaphoreTake(xMutex, portMAX_DELAY)) {
      v1 = actuatorCmd.valve1_freq;
      v2 = actuatorCmd.valve2_freq;
      p1 = actuatorCmd.pump1_pwm;
      p2 = actuatorCmd.pump2_pwm;
      xSemaphoreGive(xMutex);
    }

    spm_i2c_write_float(PUMP1_ADDR, REGISTER_SET_VAL, p1);
    spm_i2c_write_float(PUMP2_ADDR, REGISTER_SET_VAL, p2);

    unsigned long now = millis();
    if (v1 > 0) {
      int period = 1000 / v1 / 2;
      if (now - prevTimeValve1 >= period) {
        valve1State = !valve1State;
        digitalWrite(VALVE1_PIN, valve1State);
        prevTimeValve1 = now;
      }
    } else {
      digitalWrite(VALVE1_PIN, LOW);
    }

    if (v2 > 0) {
      int period = 1000 / v2 / 2;
      if (now - prevTimeValve2 >= period) {
        valve2State = !valve2State;
        digitalWrite(VALVE2_PIN, valve2State);
        prevTimeValve2 = now;
      }
    } else {
      digitalWrite(VALVE2_PIN, LOW);
    }

    taskYIELD();
  }
}

void setup() {
  Serial.begin(115200);
  delay(1000);  // Power stabilization

  Wire.begin(SDA_PIN, SCL_PIN);
  delay(100);
  scanI2CBus();  // Optional for debug

  // Safe initialization
  spm_i2c_setup_manual_power_control(PUMP1_ADDR);
  spm_i2c_write_float(PUMP1_ADDR, REGISTER_SET_VAL, 0.0);
  spm_i2c_write_int16(PUMP1_ADDR, REGISTER_PUMP_ENABLE, 1);

  spm_i2c_setup_manual_power_control(PUMP2_ADDR);
  spm_i2c_write_float(PUMP2_ADDR, REGISTER_SET_VAL, 0.0);
  spm_i2c_write_int16(PUMP2_ADDR, REGISTER_PUMP_ENABLE, 1);

  xMutex = xSemaphoreCreateMutex();
  cmdQueue = xQueueCreate(10, sizeof(ActuatorCommand));
  xTaskCreatePinnedToCore(UDPTask, "UDPTask", 4096, NULL, 1, NULL, 0);
  xTaskCreatePinnedToCore(ActuationTask, "ActuationTask", 4096, NULL, 1, NULL, 1);
}

void loop() {
  // No loop code; task-based execution
}
