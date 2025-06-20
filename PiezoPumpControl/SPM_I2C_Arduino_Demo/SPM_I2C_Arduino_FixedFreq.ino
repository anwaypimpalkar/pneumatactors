/*
DISCLAIMER
This Arduino demo is provided "as is" and without any warranty of any kind, and its use is at your 
own risk. LEE Ventus does not warrant the performance or results that you may obtain by using 
this Arduino demo. LEE Ventus makes no warranties regarding this Arduino demo, express 
or implied, including as to non-infringement, merchantability, or fitness for any particular purpose. 
To the maximum extent permitted by law LEE Ventus disclaims liability for any loss or damage 
resulting from use of this Arduino demo, whether arising under contract, tort (including 
negligence), strict liability, or otherwise, and whether direct, consequential, indirect, or otherwise, 
even if LEE Ventus has been advised of the possibility of such damages, or for any claim from any 
third party.
*/

/*
Lee Ventus SPM I2C Arduino demo
Date: 02/02/2023
Author: Ruzhev, Dimitar
Arduino IDE version: 2.0.2

For up to date information on the I2C commands and functionality please refer to:
Technical Note TN003: Communications Guide
*/

#include <Arduino.h>
#include <Wire.h>  // Arduino library for I2C
#include "lee_ventus_spm_i2c.h"


void setup() {
  Serial.begin(115200);  //initialize serial communication
  Serial.println("SPM I2C demo");

  Wire.begin();  // join i2c bus (address optional for master)
}

void loop() {
  static bool isOscillating = false;
  static float targetPower = 0;
  static unsigned long halfPeriodMicros = 0;
  static bool powerHigh = false;
  static unsigned long lastToggleTime = 0;

  // Check for new serial input
  if (Serial.available()) {
    String input = Serial.readStringUntil('\n');
    input.trim();

    if (input.length() > 0) {
      float freq = 0;
      float power = 0;

      int spaceIndex = input.indexOf(' ');
      if (spaceIndex > 0) {
        freq = input.substring(0, spaceIndex).toFloat();
        power = input.substring(spaceIndex + 1).toFloat();

        if (freq >= 0 && power >= 0 && power <= 1000) {
          spm_i2c_setup_manual_power_control(0x26);
          spm_i2c_write_int16(0x26, REGISTER_PUMP_ENABLE, 1);  // Enable pump

          targetPower = power;

          if (freq == 0) {
            Serial.print("Setting constant power: ");
            Serial.print(power);
            Serial.println(" mW");

            spm_i2c_write_float(0x26, REGISTER_SET_VAL, power);
            isOscillating = false;  // Disable toggling
          } else {
            Serial.print("Starting ");
            Serial.print(freq);
            Serial.print(" Hz oscillation at ");
            Serial.print(power);
            Serial.println(" mW");

            halfPeriodMicros = 1e6 / (2 * freq);
            lastToggleTime = micros();
            powerHigh = false;
            isOscillating = true;
          }

        } else {
          Serial.println("Invalid input. Format: <frequency> <power>");
        }
      } else {
        Serial.println("Invalid input. Format: <frequency> <power>");
      }
    }
  }

  // Perform square wave toggling if active
  if (isOscillating) {
    unsigned long now = micros();
    if (now - lastToggleTime >= halfPeriodMicros) {
      powerHigh = !powerHigh;
      float setPower = powerHigh ? targetPower : 0.0;
      spm_i2c_write_float(0x26, REGISTER_SET_VAL, setPower);
      lastToggleTime = now;
    }
  }
}

