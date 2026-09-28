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

#include <Arduino.h>

static const int LEFT_PWM_PIN = 25;
static const int RIGHT_PWM_PIN = 26;
static const int DISTANCE_ADC_PIN = 34;
static const int LIGHT_ADC_PIN = 35;
static const int BUMP_GPIO_PIN = 14;
static const int PWM_CH_LEFT = 0;
static const int PWM_CH_RIGHT = 1;
static const int PWM_FREQ_HZ = 1000;
static const int PWM_RES_BITS = 10;
static const float MAX_DURATION_S = 0.5f;
static const float MAX_WHEEL = 0.3f;

static bool armed = false;

void zeroPwm() {
  ledcWrite(PWM_CH_LEFT, 0);
  ledcWrite(PWM_CH_RIGHT, 0);
}

void disarmMotors() {
  zeroPwm();
  armed = false;
}

void driveMotors(float left, float right, float duration) {
  if (!armed) {
    return;  // fail closed
  }
  if (left > MAX_WHEEL) left = MAX_WHEEL;
  if (left < -MAX_WHEEL) left = -MAX_WHEEL;
  if (right > MAX_WHEEL) right = MAX_WHEEL;
  if (right < -MAX_WHEEL) right = -MAX_WHEEL;
  if (duration < 0.0f) duration = 0.0f;
  if (duration > MAX_DURATION_S) duration = MAX_DURATION_S;

  const int maxDuty = (1 << PWM_RES_BITS) - 1;
  ledcWrite(PWM_CH_LEFT, (int)(fabsf(left) * maxDuty));
  ledcWrite(PWM_CH_RIGHT, (int)(fabsf(right) * maxDuty));
  delay((int)(duration * 1000.0f));
  disarmMotors();  // auto-disarm after each short move during bring-up
}

void readSensors(float &distance, float &light, bool &bump) {
  distance = analogRead(DISTANCE_ADC_PIN) / 4095.0f;
  light = analogRead(LIGHT_ADC_PIN) / 4095.0f;
  bump = digitalRead(BUMP_GPIO_PIN) == LOW;  // active-low
}

void setup() {
  Serial.begin(115200);
  pinMode(BUMP_GPIO_PIN, INPUT_PULLUP);
  ledcSetup(PWM_CH_LEFT, PWM_FREQ_HZ, PWM_RES_BITS);
  ledcSetup(PWM_CH_RIGHT, PWM_FREQ_HZ, PWM_RES_BITS);
  ledcAttachPin(LEFT_PWM_PIN, PWM_CH_LEFT);
  ledcAttachPin(RIGHT_PWM_PIN, PWM_CH_RIGHT);
  disarmMotors();
}

void loop() {
  // Fail closed: no motion without host arm + validated JSON command.
  // Full JSON parsing (ArduinoJson) is left to the board bring-up session;
  // MicroPython main.py is the reference protocol implementation for CI.
  if (Serial.available()) {
    String line = Serial.readStringUntil('\n');
    line.trim();
    if (line.length() == 0) {
      return;
    }
    // Minimal arm/disarm recognition without a JSON library dependency.
    if (line.indexOf("\"cmd\":\"disarm\"") >= 0) {
      disarmMotors();
      Serial.println("{\"ok\":true,\"message\":\"disarmed\"}");
      return;
    }
    if (line.indexOf("\"cmd\":\"arm\"") >= 0 && line.indexOf("\"token\"") >= 0) {
      // Token presence check only; host must still send a non-empty token.
      int tokenKey = line.indexOf("\"token\"");
      int colon = line.indexOf(':', tokenKey);
      int firstQuote = line.indexOf('"', colon + 1);
      int secondQuote = line.indexOf('"', firstQuote + 1);
      if (firstQuote >= 0 && secondQuote > firstQuote + 1) {
        armed = true;
        Serial.println("{\"ok\":true,\"message\":\"armed\"}");
      } else {
        disarmMotors();
        Serial.println("{\"ok\":false,\"message\":\"arm_token_required\"}");
      }
      return;
    }
    if (line.indexOf("\"cmd\":\"sense\"") >= 0) {
      float distance = 0.0f;
      float light = 0.0f;
      bool bump = false;
      readSensors(distance, light, bump);
      Serial.print("{\"distance\":");
      Serial.print(distance, 4);
      Serial.print(",\"light\":");
      Serial.print(light, 4);
      Serial.print(",\"bump\":");
      Serial.print(bump ? "true" : "false");
      Serial.println("}");
      return;
    }
    if (line.indexOf("\"cmd\":\"move\"") >= 0) {
      // Parsed magnitudes are not extracted here without ArduinoJson;
      // refuse open-loop motion and keep outputs zeroed unless armed was set
      // and a full parser is wired on the board under test.
      if (!armed) {
        Serial.println("{\"ok\":true,\"left\":0,\"right\":0,\"duration\":0}");
        return;
      }
      // Conservative bring-up: zero-magnitude move then auto-disarm.
      driveMotors(0.0f, 0.0f, 0.0f);
      Serial.println("{\"ok\":true,\"left\":0,\"right\":0,\"duration\":0}");
      return;
    }
    disarmMotors();
    Serial.println("{\"ok\":false,\"message\":\"unknown_cmd\"}");
  }
}
