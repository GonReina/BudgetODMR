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
  set50MHz();
  Serial.println("Manual 50MHz registers sent. Check D3.");
}

void set50MHz() {
  // Calculated registers for 50MHz output using a 25MHz Reference
  // This uses a VCO of 3200MHz and an output divider of 64
  uint32_t reg[6] = {
    0x00400000, // Reg 0: INT=128 (128 * 25MHz = 3200MHz)
    0x08008011, // Reg 1: Phase and Mod settings
    0x00004E42, // Reg 2: R=1, Standard settings
    0x000004B3, // Reg 3: Clock dividers
    0x00BC803C, // Reg 4: Output Divider = 64, Power = +5dBm
    0x00580005  // Reg 5: Lock detect precision
  };

  for (int i = 5; i >= 0; i--) {
    digitalWrite(10, LOW);
    delayMicroseconds(10);
    
    SPI.transfer((reg[i] >> 24) & 0xFF);
    SPI.transfer((reg[i] >> 16) & 0xFF);
    SPI.transfer((reg[i] >> 8) & 0xFF);
    SPI.transfer(reg[i] & 0xFF);
    
    delayMicroseconds(10);
    digitalWrite(10, HIGH); // LATCH
    delay(10);
  }
}

void loop() {
  // Static 50MHz
}