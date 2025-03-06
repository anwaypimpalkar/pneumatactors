#include <Arduino.h>
#include <Wire.h>

// Shared variable to store the received number
volatile int receivedNumber = 0;
int D2 = 2;
int D3 = 3;

// I2C receive handler (ISR context)
void I2C_RxHandler(int numBytes) {
  while (Wire.available()) {
    receivedNumber = Wire.read();
  }
}

void setup() {
  pinMode(LED_BUILTIN, OUTPUT); // Initialize built-in LED as output
  pinMode(D2, OUTPUT); // Initialize D2 as output
  pinMode(D3, OUTPUT); // Initialize D3 as output

  Wire.begin(0x55);            // Initialize I2C in Slave Mode with address 0x55
  Wire.setClock(400000);       // Set I2C bitrate to 400 kHz
  Wire.onReceive(I2C_RxHandler); // Set receive handler
}

void loop() {
  int frequency = receivedNumber; // Read the latest received number

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
