#include <WiFi.h>
#include <WiFiUdp.h>
#include <Wire.h>
#include "lee_ventus_spm_i2c.h"
#include <ESPmDNS.h>


// --- WiFi Access Point credentials ---
const char* ssid = "PNEUMATACTORS_AP";
const char* password = "12345678";
const int udpPort = 4210;

WiFiUDP Udp;

// --- Pins ---
#define VALVE1_PIN 1
#define VALVE2_PIN 2

// --- Struct for commands ---
struct ActuatorCommand {
  volatile int valve1_freq;
  volatile int valve2_freq;
  volatile int pump1_pwm;
  volatile int pump2_pwm;
};

ActuatorCommand actuatorCmd = {0, 0, 0};

SemaphoreHandle_t xMutex;
QueueHandle_t cmdQueue;

void UDPTask(void *pvParameters) {
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
  }

  Udp.begin(udpPort);
  
  char incoming[255];

  while (true) {
    int packetSize = Udp.parsePacket();
    if (packetSize) {
      int len = Udp.read(incoming, 255);
      if (len > 0) incoming[len] = 0;

      String cmdStr = String(incoming);
      cmdStr.trim();  // Removes newline, carriage return, spaces

      // --- Discovery handler ---
      if (cmdStr == "DISCOVERXIAO") {
        Udp.beginPacket(Udp.remoteIP(), udpPort);
        Udp.print("XIAO_HERE");
        Udp.endPacket();
        // continue so it doesn't fall through to command parser
        continue;
      }

      // --- Main actuator command handler ---
      if (cmdStr.length() == 12) {
        ActuatorCommand cmd;
        cmd.valve1_freq = cmdStr.substring(0, 3).toInt();
        cmd.valve2_freq = cmdStr.substring(3, 6).toInt();
        cmd.pump1_pwm   = cmdStr.substring(6, 9).toInt();
        cmd.pump2_pwm   = cmdStr.substring(9, 12).toInt();

        cmd.pump1_pwm = constrain(cmd.pump1_pwm, 0, 999);
        cmd.pump2_pwm = constrain(cmd.pump2_pwm, 0, 999);

        xQueueSend(cmdQueue, &cmd, portMAX_DELAY);
      }
    }

    vTaskDelay(pdMS_TO_TICKS(10)); // Yield CPU
  }
}


// --- Actuation Task (Core 1) ---
void ActuationTask(void *pvParameters) {

  pinMode(VALVE1_PIN, OUTPUT);
  pinMode(VALVE2_PIN, OUTPUT);

  // Wire.begin();

  // Setup both pumps (assuming different I2C addresses)
  const int PUMP1_ADDR = 0x26;  
  const int PUMP2_ADDR = 0x25;


  spm_i2c_setup_manual_power_control(PUMP1_ADDR);
  spm_i2c_write_int16(PUMP1_ADDR, REGISTER_PUMP_ENABLE, 1);

  spm_i2c_setup_manual_power_control(PUMP2_ADDR);
  spm_i2c_write_int16(PUMP2_ADDR, REGISTER_PUMP_ENABLE, 1);

  delay(500);

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

    // Convert and write pump power

    spm_i2c_write_float(PUMP1_ADDR, REGISTER_SET_VAL, p1);
    spm_i2c_write_float(PUMP2_ADDR, REGISTER_SET_VAL, p2);

    unsigned long now = millis();

    // Valve 1 toggle
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

    // Valve 2 toggle
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
  // Serial.begin(115200);
  delay(500);

  Wire.begin();
  delay(500);
  
  byte pumpAddresses[] = {0x26, 0x25};
  for (byte i = 0; i < sizeof(pumpAddresses); i++) {
    Wire.beginTransmission(pumpAddresses[i]);
    byte error = Wire.endTransmission();
  }

  delay(500);

  xMutex = xSemaphoreCreateMutex();
  cmdQueue = xQueueCreate(10, sizeof(ActuatorCommand));

  xTaskCreatePinnedToCore(UDPTask, "UDPTask", 4096, NULL, 1, NULL, 0);
  xTaskCreatePinnedToCore(ActuationTask, "ActuationTask", 4096, NULL, 1, NULL, 1);
}

void loop() {
  // No code here; task-based execution
}
