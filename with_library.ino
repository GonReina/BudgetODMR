#include <SPI.h>
#include <ADF4351.h>

ADF4351 pll;

void setup() {
  Serial.begin(9600);
  
  // Power up sequence
  pinMode(8, OUTPUT); 
  digitalWrite(8, LOW);  // Reset state
  delay(10);
  digitalWrite(8, HIGH); // Enable Chip
  delay(10);

  SPI.begin();
  // DIV128 on a 16MHz Arduino = 125kHz. This is very slow.
  // This gives your 6.5k resistors plenty of time to reach 3.3V.
  SPI.setClockDivider(SPI_CLOCK_DIV128); 
  SPI.setDataMode(SPI_MODE0);

  // Initialize with safe values
  // LE=10, RFdiv=1, RFdouble=false, RDIV=1, RDIV2=false
  pll.init(10, 1, false, 1, false);
  delay(500);
  Serial.println("System Ready. Sending 200MHz...");
}

void loop() {
  Serial.println("Writing Raw Registers for 100MHz...");
  
  // Register values for 100MHz (assuming 25MHz Ref)
  // These are standard values used to test ADF4351 modules
  uint32_t registers[6] = {
    0x00320008, // Reg 0
    0x08008011, // Reg 1
    0x00004E42, // Reg 2
    0x000004B3, // Reg 3
    0x00BC8024, // Reg 4
    0x00580005  // Reg 5
  };

  // Write registers 5 down to 0 (ADF4351 requirement)
  for (int i = 5; i >= 0; i--) {
    digitalWrite(10, LOW); // LE Low
    delayMicroseconds(10);
    
    // Split the 32-bit register into 4 bytes for SPI
    SPI.transfer((registers[i] >> 24) & 0xFF);
    SPI.transfer((registers[i] >> 16) & 0xFF);
    SPI.transfer((registers[i] >> 8) & 0xFF);
    SPI.transfer(registers[i] & 0xFF);
    
    delayMicroseconds(10);
    digitalWrite(10, HIGH); // LE High (LATCH)
    delay(10);
  }

  Serial.println("Write Complete. Check D3.");
  delay(5000);
}