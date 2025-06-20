// #include <Arduino.h>
// #include <BLEDevice.h>
// #include <BLEUtils.h>
// #include <BLEServer.h>
// #include <Wire.h>
// #include "lee_ventus_spm_i2c.h"

// // --- Pins ---
// #define VALVE1_PIN 2
// #define VALVE2_PIN 4
// #define PUMP_PIN   7

// // --- BLE UUIDs ---
// #define SERVICE_UUID        "4fafc201-1fb5-459e-8fcc-c5c9c331914b"
// #define CHARACTERISTIC_UUID "beb5483e-36e1-4688-b7f5-ea07361b26a8"

// // --- Struct for commands ---
// struct ActuatorCommand {
//   volatile int valve1_freq;
//   volatile int valve2_freq;
//   volatile int pump_pwm;
// };

// ActuatorCommand actuatorCmd = {0, 0, 0};

// SemaphoreHandle_t xMutex;
// QueueHandle_t bleQueue;

// // --- BLE Write Handler ---
// class MyCallbacks : public BLECharacteristicCallbacks {
//   void onWrite(BLECharacteristic *pCharacteristic) override {
//     std::string value = pCharacteristic->getValue();

//     if (value.length() != 9) {
//       // Serial.printf("Invalid input length (%d). Expected 9 digits.\n", value.length());
//       return;
//     }

//     String cmdStr = String(value.c_str());
//     cmdStr.replace("\n", "");
//     cmdStr.replace("\r", "");
//     cmdStr.replace(" ", "");

//     if (cmdStr.length() != 9) {
//       // Serial.println("Cleaned string isn't 9 digits. Ignoring.");
//       return;
//     }

//     ActuatorCommand cmd;
//     cmd.valve1_freq = cmdStr.substring(0, 3).toInt();
//     cmd.valve2_freq = cmdStr.substring(3, 6).toInt();
//     cmd.pump_pwm    = cmdStr.substring(6, 9).toInt();
//     if (cmd.pump_pwm > 255) cmd.pump_pwm = 255;

//     xQueueSend(bleQueue, &cmd, portMAX_DELAY);

//     // Serial.printf("Parsed BLE Cmd: V1=%d, V2=%d, PUMP=%d\n",
//                   // cmd.valve1_freq, cmd.valve2_freq, cmd.pump_pwm);
//   }
// };

// class MyServerCallbacks : public BLEServerCallbacks {
//   void onConnect(BLEServer* pServer) override {
//     // Optional: you could set a flag or LED here
//     // Serial.println("Client connected");
//   }

//   void onDisconnect(BLEServer* pServer) override {
//     // Restart advertising when client disconnects
//     BLEDevice::startAdvertising();
//     // Serial.println("Client disconnected, restarting advertising...");
//   }
// };


// // --- BLE Setup (Core 0) ---
// void BLETask(void *pvParameters) {
//   BLEDevice::init("PNEUMATACTORS");
//   BLEServer *pServer = BLEDevice::createServer();
//   pServer->setCallbacks(new MyServerCallbacks());
//   BLEService *pService = pServer->createService(SERVICE_UUID);

//   BLECharacteristic *pCharacteristic = pService->createCharacteristic(
//     CHARACTERISTIC_UUID,
//     BLECharacteristic::PROPERTY_READ | 
//     BLECharacteristic::PROPERTY_WRITE |
//     BLECharacteristic::PROPERTY_WRITE_NR
//   );

//   pCharacteristic->setValue("000000000");  // Default
//   pCharacteristic->setCallbacks(new MyCallbacks());

//   pService->start();

//   BLEAdvertising *pAdvertising = BLEDevice::getAdvertising();
//   pAdvertising->addServiceUUID(SERVICE_UUID);
//   pAdvertising->setScanResponse(true);
//   pAdvertising->setMinPreferred(0x06);
//   pAdvertising->setMinPreferred(0x12);
//   BLEDevice::startAdvertising();

//   // Serial.println("BLE server is running. Connect and write 9-digit code.");

//   while (true) {
//     vTaskDelay(pdMS_TO_TICKS(5000));
//   }
// }

// // --- Actuation Task (Core 1) ---
// void ActuationTask(void *pvParameters) {
//   pinMode(VALVE1_PIN, OUTPUT);
//   pinMode(VALVE2_PIN, OUTPUT);

//   Wire.begin();  // Initialize I2C
//   spm_i2c_setup_manual_power_control(SPM_DEFAULT_I2C_ADDRESS);
//   spm_i2c_write_int16(SPM_DEFAULT_I2C_ADDRESS, REGISTER_PUMP_ENABLE, 1);  // Enable pump

//   unsigned long prevTimeValve1 = 0, prevTimeValve2 = 0;
//   bool valve1State = false, valve2State = false;

//   while (true) {
//     ActuatorCommand receivedCmd;

//     if (xQueueReceive(bleQueue, &receivedCmd, 0)) {
//       if (xSemaphoreTake(xMutex, portMAX_DELAY)) {
//         actuatorCmd = receivedCmd;
//         xSemaphoreGive(xMutex);
//       }
//     }

//     int v1, v2, p;
//     if (xSemaphoreTake(xMutex, portMAX_DELAY)) {
//       v1 = actuatorCmd.valve1_freq;
//       v2 = actuatorCmd.valve2_freq;
//       p  = actuatorCmd.pump_pwm;
//       xSemaphoreGive(xMutex);
//     }

//     // Set pump power via I2C (in mW, mapped from 0–255)
//     float pumpPower_mW = map(p, 0, 255, 0, 1000);  // Adjust max as needed
//     spm_i2c_write_float(SPM_DEFAULT_I2C_ADDRESS, REGISTER_SET_VAL, pumpPower_mW);

//     // Valve 1 Toggle
//     unsigned long now = millis();
//     if (v1 > 0) {
//       int period = 1000 / v1 / 2;
//       if (now - prevTimeValve1 >= period) {
//         valve1State = !valve1State;
//         digitalWrite(VALVE1_PIN, valve1State);
//         prevTimeValve1 = now;
//       }
//     } else {
//       digitalWrite(VALVE1_PIN, LOW);
//     }

//     // Valve 2 Toggle
//     if (v2 > 0) {
//       int period = 1000 / v2 / 2;
//       if (now - prevTimeValve2 >= period) {
//         valve2State = !valve2State;
//         digitalWrite(VALVE2_PIN, valve2State);
//         prevTimeValve2 = now;
//       }
//     } else {
//       digitalWrite(VALVE2_PIN, LOW);
//     }

//     taskYIELD();
//   }
// }


// void setup() {
//   // Serial.begin(115200);
//   delay(500);
//   Wire.begin();  // For I2C pump

//   xMutex = xSemaphoreCreateMutex();
//   bleQueue = xQueueCreate(10, sizeof(ActuatorCommand));

//   xTaskCreatePinnedToCore(BLETask, "BLETask", 4096, NULL, 1, NULL, 0);
//   xTaskCreatePinnedToCore(ActuationTask, "ActuationTask", 4096, NULL, 1, NULL, 1);
// }

// void loop() {
//   // No code needed here; everything is task-based
// }
