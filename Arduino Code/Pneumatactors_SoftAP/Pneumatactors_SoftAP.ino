#include <WiFi.h>
#include <WiFiUdp.h>

// --- WiFi Access Point credentials ---
const char* ssid = "PNEUMATACTORS_AP";
const char* password = "12345678";
const int udpPort = 4210;

WiFiUDP Udp;

// --- Pins ---
#define VALVE1_PIN 8
#define VALVE2_PIN 9
#define PUMP_PIN 7

// --- Struct for commands ---
struct ActuatorCommand {
  volatile int valve1_freq;
  volatile int valve2_freq;
  volatile int pump_pwm;
};

ActuatorCommand actuatorCmd = { 0, 0, 0 };

SemaphoreHandle_t xMutex;
QueueHandle_t cmdQueue;

// --- UDP Listener Task (Core 0) ---
void UDPTask(void* pvParameters) {
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nConnected to router!");
  Serial.print("IP: ");
  Serial.println(WiFi.localIP());  // <- You’ll use this in Unity

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

      if (cmdStr.length() == 9) {
        ActuatorCommand cmd;
        cmd.valve1_freq = cmdStr.substring(0, 3).toInt();
        cmd.valve2_freq = cmdStr.substring(3, 6).toInt();
        cmd.pump_pwm = cmdStr.substring(6, 9).toInt();
        if (cmd.pump_pwm > 255) cmd.pump_pwm = 255;

        xQueueSend(cmdQueue, &cmd, portMAX_DELAY);
        Serial.printf("Parsed UDP Cmd: V1=%d, V2=%d, PUMP=%d\n",
                      cmd.valve1_freq, cmd.valve2_freq, cmd.pump_pwm);
      } else {
        Serial.println("Invalid UDP command length");
      }
    }

    vTaskDelay(pdMS_TO_TICKS(10));  // Yield CPU
  }
}

// --- Actuation Task (Core 1) ---
void ActuationTask(void* pvParameters) {
  pinMode(VALVE1_PIN, OUTPUT);
  pinMode(VALVE2_PIN, OUTPUT);
  pinMode(PUMP_PIN, OUTPUT);

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

    int v1, v2, p;
    if (xSemaphoreTake(xMutex, portMAX_DELAY)) {
      v1 = actuatorCmd.valve1_freq;
      v2 = actuatorCmd.valve2_freq;
      p = actuatorCmd.pump_pwm;
      xSemaphoreGive(xMutex);
    }

    // Pump PWM
    analogWrite(PUMP_PIN, constrain(p, 0, 255));

    // Valve 1 Toggle
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

    // Valve 2 Toggle
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
  delay(500);

  xMutex = xSemaphoreCreateMutex();
  cmdQueue = xQueueCreate(10, sizeof(ActuatorCommand));

  xTaskCreatePinnedToCore(UDPTask, "UDPTask", 4096, NULL, 1, NULL, 0);
  xTaskCreatePinnedToCore(ActuationTask, "ActuationTask", 4096, NULL, 1, NULL, 1);
}

void loop() {
  // No code here; task-based execution
}
