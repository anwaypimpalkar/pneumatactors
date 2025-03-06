#include <Arduino.h>
#include <Wire.h>

volatile int receivedNumber = 0;
const int pwmPin = 6;   // PWM output pin
const int enablePin = 12; // Enable pin, always HIGH

// I2C receive handler (ISR context)
void I2C_RxHandler(int numBytes) {
  while (Wire.available()) {
    receivedNumber = Wire.read(); // Read the received PWM value
  }
}

void setup() {
  pinMode(pwmPin, OUTPUT);   // Set PWM pin as output
  pinMode(enablePin, OUTPUT); // Set Enable pin as output
  digitalWrite(enablePin, HIGH); // Always set D12 to HIGH (5V)

  Wire.begin(0x10);         // Initialize I2C in Slave Mode with address 0x55
  Wire.setClock(400000);    // Set I2C bitrate to 400 kHz
  Wire.onReceive(I2C_RxHandler); // Set receive handler
}

void loop() {
  int pwmValue = receivedNumber; // Read the latest received value
  
  if (pwmValue >= 0 && pwmValue <= 255) {
    analogWrite(pwmPin, pwmValue); // Set PWM duty cycle
  }
  
  delay(10); // Short delay to stabilize processing
}
