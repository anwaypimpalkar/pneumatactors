#include <Arduino.h>
#include <Wire.h>

// --- Global Definitions ---
#define VALVE1_PIN D10
#define VALVE2_PIN D9
#define PUMP_PIN A8

struct ActuatorCommand {
  volatile int valve1_freq;   // Frequency in Hz for Valve 1
  volatile int valve2_freq;   // Frequency in Hz for Valve 2
  volatile int pump_pwm;      // PWM value 0-255 for pump
};

ActuatorCommand actuatorCmd = {0, 0, 0};

SemaphoreHandle_t xMutex;
QueueHandle_t i2cQueue;

// --- I2C Task (Core 0) ---
void I2CTask(void *pvParameters) {
  ActuatorCommand receivedCmd;

  while (true) {
    if (xQueueReceive(i2cQueue, &receivedCmd, portMAX_DELAY)) {
      if (xSemaphoreTake(xMutex, portMAX_DELAY)) {
        actuatorCmd = receivedCmd;
        xSemaphoreGive(xMutex);
      }
    }
  }
}

// --- I2C ISR ---
void I2C_RxHandler(int numBytes) {
  if (numBytes >= 3) {
    ActuatorCommand cmd;
    cmd.valve1_freq = Wire.read(); // Assumes frequency fits in single byte
    cmd.valve2_freq = Wire.read();
    cmd.pump_pwm    = Wire.read();
    
    xQueueSendFromISR(i2cQueue, &cmd, NULL);
  } else {
    while(Wire.available()) Wire.read(); // Flush remaining bytes if incomplete
  }
}

// --- Actuation Task (Core 1) ---
void ActuationTask(void *pvParameters) {
  pinMode(VALVE1_PIN, OUTPUT);
  pinMode(VALVE2_PIN, OUTPUT);
  pinMode(PUMP_PIN, OUTPUT);

  unsigned long prevTimeValve1 = 0, prevTimeValve2 = 0;
  bool valve1State = false, valve2State = false;

  while (true) {
    int valve1_freq, valve2_freq, pump_pwm;

    // Safely copy actuator commands
    if (xSemaphoreTake(xMutex, portMAX_DELAY)) {
      valve1_freq = actuatorCmd.valve1_freq;
      valve2_freq = actuatorCmd.valve2_freq;
      pump_pwm    = actuatorCmd.pump_pwm;
      xSemaphoreGive(xMutex);
    }

    // --- Pump Control (PWM) ---
    analogWrite(PUMP_PIN, constrain(pump_pwm, 0, 255));

    // --- Valve 1 Control (PFM) ---
    unsigned long currentMillis = millis();
    if (valve1_freq > 0) {
      int period_ms = 1000 / valve1_freq / 2; // Half-period toggle

      if (currentMillis - prevTimeValve1 >= period_ms) {
        prevTimeValve1 = currentMillis;
        valve1State = !valve1State;
        digitalWrite(VALVE1_PIN, valve1State);
      }
    } else {
      digitalWrite(VALVE1_PIN, LOW);
    }

    // --- Valve 2 Control (PFM) ---
    if (valve2_freq > 0) {
      int period_ms = 1000 / valve2_freq / 2;

      if (currentMillis - prevTimeValve2 >= period_ms) {
        prevTimeValve2 = currentMillis;
        valve2State = !valve2State;
        digitalWrite(VALVE2_PIN, valve2State);
      }
    } else {
      digitalWrite(VALVE2_PIN, LOW);
    }
    taskYIELD();
  }
}

void setup() {
  Wire.begin(0x15);
  Wire.setClock(400000);
  Wire.onReceive(I2C_RxHandler);

  // Initialize mutex and queue
  xMutex = xSemaphoreCreateMutex();
  i2cQueue = xQueueCreate(10, sizeof(ActuatorCommand));

  // Task creation
  xTaskCreatePinnedToCore(I2CTask, "I2CTask", 2048, NULL, 2, NULL, 0);
  xTaskCreatePinnedToCore(ActuationTask, "ActuationTask", 4096, NULL, 1, NULL, 1);
}

void loop() {
}
