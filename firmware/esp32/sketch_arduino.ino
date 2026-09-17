/*
 * Arduino-style ESP32 thin bridge — execute + sense ONLY.
 * Evolution stays on the host. No mutation / selection on device.
 *
 * SAFETY (mandatory):
 * - Separate motor PSU from ESP32 logic rail. Never power motors from ESP32 5V.
 * - Physical e-stop required on every experimental robot.
 * - Enclosed / fixed test area for initial trials (reality gap).
 * - Motors stay DISARMED until host sends {"cmd":"arm","token":"..."}.
 * - No dangerous defaults: PWM starts at 0; duration hard-capped.
 *
 * Protocol: UART JSON lines (see firmware/esp32/main.py).
 * This sketch does NOT claim physical robots ran in CodonTrace campaigns.
 */

// Placeholder — flesh out with ArduinoJson + ledcWrite when wiring hardware.
// void setup() { Serial.begin(115200); disarmMotors(); }
// void loop() { /* parse line; handle move/sense/arm/disarm */ }

void disarmMotors() {
  // analogWrite / ledcWrite both channels to 0
}

void setup() {
  disarmMotors();
}

void loop() {
  // Fail closed: no motion without host arm + validated JSON command.
}
