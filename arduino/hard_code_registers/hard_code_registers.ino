#include <SPI.h>

void setup() {
  Serial.begin(9600);
  
  pinMode(8, OUTPUT);  // CE
  pinMode(10, OUTPUT); // LE
  
  digitalWrite(8, HIGH); // Enable Chip
  
  SPI.begin();
  SPI.setClockDivider(SPI_CLOCK_DIV64); // Safe speed for resistors
  SPI.setDataMode(SPI_MODE0);

  delay(100);
  set500MHz();
  Serial.println("Manual 50MHz registers sent. Check D3.");
}

void set100MHz() {
  uint32_t reg[6] = {
    0x00500000, // R0: INT=160 (VCO = 160 * 25MHz = 4000MHz)
    0x08008011, // R1: Prescaler=8/9 (Required for 4GHz)
    0x18005E42, // R2: Correct Charge Pump current for 4GHz
    0x000004B3, // R3: CSR enabled for stability
    0x00BFA03C, // R4: RF Div=64, Feedback=VCO, Power=+5dBm
    0x00580005  // R5: Digital Lock Detect
  };

  // Note: To get 100MHz from a 4000MHz VCO, we use Div-by-40.
  // Since the chip only supports 1, 2, 4, 8, 16, 32, 64:
  // We will target 3200MHz VCO with Div-by-32.
  
  reg[0] = 0x00400000; // R0: INT=128 (3200MHz)
  reg[4] = 0x00DFA03C; // R4: RF Div=32, Feedback=VCO
  
  for (int i = 5; i >= 0; i--) {
    digitalWrite(10, LOW);
    SPI.transfer((reg[i] >> 24) & 0xFF);
    SPI.transfer((reg[i] >> 16) & 0xFF);
    SPI.transfer((reg[i] >> 8) & 0xFF);
    SPI.transfer(reg[i] & 0xFF);
    digitalWrite(10, HIGH);
    delay(20);
  }
}

void set500MHz() {
  // VCO = 4000MHz, RF Div = 8  ->  4000 / 8 = 500MHz
  uint32_t reg[6] = {
    0x00500000, // R0: INT=160 (VCO = 160 * 25MHz = 4000MHz), FRAC=0
    0x08008011, // R1: Prescaler 8/9, MOD=2, Phase=1
    0x18005E42, // R2: R=1, CP=5mA, MUXOUT=Digital LD, low-noise mode
    0x000004B3, // R3
    0x00BFA03C, // R4: RF Div=8, Feedback=VCO, Band-sel-div=250, RF enabled, +5dBm
    0x00580005  // R5: Digital Lock Detect on LD pin
  };

  for (int i = 5; i >= 0; i--) {
    digitalWrite(10, LOW);
    SPI.transfer((reg[i] >> 24) & 0xFF);
    SPI.transfer((reg[i] >> 16) & 0xFF);
    SPI.transfer((reg[i] >> 8) & 0xFF);
    SPI.transfer(reg[i] & 0xFF);
    digitalWrite(10, HIGH);
    delay(20);
  }
}

void set800MHz() {
  // VCO = 3200MHz, RF Div = 4  ->  3200 / 4 = 800MHz
  uint32_t reg[6] = {
    0x00400000, // R0: INT=128 (VCO = 128 * 25MHz = 3200MHz), FRAC=0
    0x08008011, // R1: Prescaler 8/9, MOD=2, Phase=1
    0x18005E42, // R2: R=1, CP=5mA, MUXOUT=Digital LD, low-noise mode
    0x000004B3, // R3
    0x00AFA03C, // R4: RF Div=4, Feedback=VCO, Band-sel-div=250, RF enabled, +5dBm
    0x00580005  // R5: Digital Lock Detect on LD pin
  };

  for (int i = 5; i >= 0; i--) {
    digitalWrite(10, LOW);
    SPI.transfer((reg[i] >> 24) & 0xFF);
    SPI.transfer((reg[i] >> 16) & 0xFF);
    SPI.transfer((reg[i] >> 8) & 0xFF);
    SPI.transfer(reg[i] & 0xFF);
    digitalWrite(10, HIGH);
    delay(20);
  }
}

void loop() {
  // Static output. Call set100MHz(), set500MHz(), or set800MHz() in setup().
}