#include <Arduino.h>
#include <Wire.h>

// Task handles for the two tasks
TaskHandle_t FrequencySetHandle, I2CTaskHandle;

// Shared variable to store the received number
volatile int receivedNumber = 0;

// Mutex for synchronizing access to the shared variable
SemaphoreHandle_t xMutex;

// Queue to store I2C received data
QueueHandle_t i2cQueue;

// Task to handle I2C receive on Core 0
void I2CTask(void *pvParameters) {
  int number;
  while (true) {
    // Wait for data from the queue
    if (xQueueReceive(i2cQueue, &number, portMAX_DELAY)) {
      // Lock mutex, update shared variable, unlock mutex
      if (xSemaphoreTake(xMutex, portMAX_DELAY)) {
        receivedNumber = number;
        xSemaphoreGive(xMutex);
      }

      // Serial.print("I2CTask Received: ");
      // Serial.print(number);
      // Serial.print("\t on core: ");
      // Serial.println(xPortGetCoreID());
    }
  }
}

// I2C receive handler (ISR context)
void I2C_RxHandler(int numBytes) {
  while (Wire.available()) {
    int number = Wire.read();
    // Serial.print("I2C ISR received number: ");
    // Serial.println(number);

    // Send the received number to the queue for processing
    xQueueSendFromISR(i2cQueue, &number, NULL);
  }
}

// Task to set frequency on Core 1
void FrequencySet(void *pvParameters) {
  pinMode(LED_BUILTIN, OUTPUT); // Initialize built-in LED as output
  pinMode(D2, OUTPUT); // Initialize D2 as output
  pinMode(D3, OUTPUT); // Initialize D3 as output

  while (true) {
    int frequency;

    // Lock mutex, read shared variable, unlock mutex
    if (xSemaphoreTake(xMutex, portMAX_DELAY)) {
      frequency = receivedNumber;
      xSemaphoreGive(xMutex);
    }

    if (frequency > 0) {
      int delayMs = 1000 / (2 * frequency); // Calculate delay for the given frequency

      digitalWrite(LED_BUILTIN, LOW); // Turn built-in LED on
      digitalWrite(D2, LOW); // Turn D2 off
      digitalWrite(D3, HIGH); // Turn D3 on
      delay(delayMs);

      digitalWrite(LED_BUILTIN, HIGH);  // Turn built-in LED off
      digitalWrite(D2, HIGH);  // Turn D2 on
      digitalWrite(D3, LOW);  // Turn D3 off
      delay(delayMs);
    } else {
      // If frequency is zero or invalid, keep LEDs off
      digitalWrite(LED_BUILTIN, LOW);
      digitalWrite(D3, LOW);
      delay(100); // Short delay to avoid busy looping
    }
  }
}

void setup() {
  // Serial.begin(115200);
  // delay(100); // Allow time for Serial to initialize

  Wire.begin(0x40);            // Initialize I2C in Slave Mode with address 0x55
  Wire.setClock(400000);       // Set I2C bitrate to 400 kHz
  Wire.onReceive(I2C_RxHandler); // Set receive handler

  // Serial.print("setup() running on core ");
  // Serial.println(xPortGetCoreID());

  // Initialize mutex
  xMutex = xSemaphoreCreateMutex();
  if (xMutex == NULL) {
    // Serial.println("Mutex creation failed!");
    while (true);
  }

  // Create queue for I2C communication
  i2cQueue = xQueueCreate(10, sizeof(int));
  if (i2cQueue == NULL) {
    // Serial.println("Queue creation failed!");
    while (true);
  }

  // Create I2C Task on Core 0
  xTaskCreatePinnedToCore(
    I2CTask,       // Function to be executed
    "I2CTask",     // Name of the task
    2048,          // Stack size (in words)
    NULL,          // Task input parameter
    2,             // Priority of the task
    &I2CTaskHandle,// Task handle
    0              // Core 0
  );

  // Create Frequency Set Task on Core 1
  xTaskCreatePinnedToCore(
    FrequencySet,       // Function to be executed
    "FrequencySet",     // Name of the task
    2048,            // Stack size (in words)
    NULL,            // Task input parameter
    1,               // Priority of the task
    &FrequencySetHandle,// Task handle
    1                // Core 1
  );
}

void loop() {
  // The loop remains empty because tasks handle functionality
}
