#include <SPI.h>

// ----------------------------------------------------------------------------
// Thin SPI bridge: Python (over USB serial) owns all the PLL math and sweep
// logic; this firmware just latches whatever 32-bit register it receives into
// the ADF4351.
//
// Protocol: one register per line, as 8 hex digits + newline, e.g. "00580005".
// To set a frequency, Python sends the six registers in order R5 -> R0.
// The board replies "OK <hex>" after each write so Python can stay in sync.
//
// Hardware (matches hard_code_registers.ino):
//   D8  -> CE  (chip enable)
//   D10 -> LE  (load enable / latch)
//   D11 -> DATA (MOSI), D13 -> CLK  (hardware SPI)
// ----------------------------------------------------------------------------

const int LE_PIN = 10;
const int CE_PIN = 8;

char buf[16];
int len = 0;

void writeRegister(uint32_t value) {
  digitalWrite(LE_PIN, LOW);
  SPI.transfer((value >> 24) & 0xFF);
  SPI.transfer((value >> 16) & 0xFF);
  SPI.transfer((value >> 8) & 0xFF);
  SPI.transfer(value & 0xFF);
  digitalWrite(LE_PIN, HIGH);
  delayMicroseconds(5);
}

void setup() {
  Serial.begin(115200);

  pinMode(CE_PIN, OUTPUT);
  pinMode(LE_PIN, OUTPUT);
  digitalWrite(CE_PIN, HIGH);   // enable chip
  digitalWrite(LE_PIN, HIGH);

  SPI.begin();
  SPI.setClockDivider(SPI_CLOCK_DIV64);
  SPI.setDataMode(SPI_MODE0);

  delay(50);
  Serial.println("READY");
}

void loop() {
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n' || c == '\r') {
      if (len > 0) {
        buf[len] = '\0';
        uint32_t reg = strtoul(buf, NULL, 16);
        writeRegister(reg);
        Serial.print("OK ");
        Serial.println(buf);
        len = 0;
      }
    } else if (len < (int)sizeof(buf) - 1) {
      buf[len++] = c;
    }
  }
}
