#include <Arduino.h>
#include <Wire.h>

// Task handles for the two tasks
TaskHandle_t PrintTaskHandle;

// Shared variable to store the received number
volatile int receivedNumber = 0;

// Mutex for synchronizing access to the shared variable
SemaphoreHandle_t xMutex;

// Function to handle I2C receive (Slave Mode)
void I2C_RxHandler(int numBytes) {
  Serial.print("I2C Handler running on core: ");
  Serial.println(xPortGetCoreID());

  while (Wire.available()) {
    int number = Wire.read();

    // Lock mutex, update shared variable, unlock mutex
    if (xSemaphoreTake(xMutex, portMAX_DELAY)) {
      receivedNumber = number;
      xSemaphoreGive(xMutex);
    }

    Serial.print("I2C Handler received number: ");
    Serial.println(number);
  }
}

// Function to be run on core 1 (Print task)
void PrintTask(void *pvParameters) {
  while (true) {
    int numberToPrint;

    // Lock mutex, read shared variable, unlock mutex
    if (xSemaphoreTake(xMutex, portMAX_DELAY)) {
      numberToPrint = receivedNumber;
      xSemaphoreGive(xMutex);
    }

    Serial.print("Print Task printing number: ");
    Serial.println(numberToPrint);

    Serial.print("Print Task running on core: ");
    Serial.println(xPortGetCoreID());

    delay(1000); // 1-second delay
  }
}

void setup() {
  Serial.begin(115200);
  delay(1000);  // Allow time for Serial to initialize

  Wire.begin(0x55); // Initialize I2C in Slave Mode with address 0x55
  Wire.setClock(400000); // Set I2C bitrate to 400 kHz
  Wire.onReceive(I2C_RxHandler); // Set receive handler

  Serial.print("setup() running on core ");
  Serial.println(xPortGetCoreID());

  // Initialize mutex
  xMutex = xSemaphoreCreateMutex();

  if (xMutex == NULL) {
    Serial.println("Mutex creation failed!");
    while (true);
  }

  // Create Print Task on core 1
  xTaskCreatePinnedToCore(
    PrintTask,       // Function to be executed
    "PrintTask",     // Name of the task
    2048,            // Stack size (in words)
    NULL,            // Task input parameter
    1,               // Priority of the task
    &PrintTaskHandle,// Task handle
    1                // Core 1
  );
}

void loop() {
  // The loop remains empty because tasks handle functionality
}
