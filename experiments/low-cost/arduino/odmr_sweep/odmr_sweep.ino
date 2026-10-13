#include <SPI.h>

// ----------------------------------------------------------------------------
// ODMR frequency sweep for ADF4351 + NV diamond.
//
// Sweeps the RF output in fixed steps from F_START to F_STOP, waiting for the
// PLL to settle at each point. The photodiode output is recorded externally.
// The current frequency is echoed over serial so you can mark/align the sweep.
//
// Hardware (matches hard_code_registers.ino):
//   D8  -> CE  (chip enable)
//   D10 -> LE  (load enable / latch)
//   D11 -> DATA (MOSI), D13 -> CLK  (hardware SPI)
// ----------------------------------------------------------------------------

// ---- Reference / PLL configuration -----------------------------------------
const double REF_MHZ = 25.0;   // on-board reference oscillator
const uint32_t R_COUNTER = 1;  // R divider
// fPFD = REF * (1+D) / (R * (1+T)) = 25MHz with D=0, R=1, T=0
const double FPFD_MHZ = REF_MHZ;

// 2800-3000 MHz lies inside the 2200-4400 MHz VCO band, so RF divider = 1.
const uint32_t RF_DIV = 1;      // output divider value
const uint32_t RF_DIV_SEL = 0;  // R4[22:20] code: 0->/1, 1->/2, 2->/4, 3->/8 ...

// Fractional modulus. fRES = fPFD / MOD = 25MHz / 1000 = 25kHz channel spacing.
// Any sweep step that is a multiple of 25kHz lands exactly on a channel.
const uint32_t MOD_VAL = 1000;

// ---- Sweep parameters -------------------------------------------------------
const double F_START = 2800.0;   // MHz
const double F_STOP  = 3000.0;   // MHz
const double F_STEP  = 1.0;      // MHz  (must be a multiple of 25kHz = 0.025)

const unsigned long SETTLE_MS = 5;   // PLL lock + signal settle time per step

const int LE_PIN = 10;
const int CE_PIN = 8;

// ----------------------------------------------------------------------------

void writeRegister(uint32_t value) {
  digitalWrite(LE_PIN, LOW);
  SPI.transfer((value >> 24) & 0xFF);
  SPI.transfer((value >> 16) & 0xFF);
  SPI.transfer((value >> 8) & 0xFF);
  SPI.transfer(value & 0xFF);
  digitalWrite(LE_PIN, HIGH);
  delayMicroseconds(5);
}

// Program every register for a given target output frequency (MHz).
// INT/FRAC/MOD are computed from the VCO frequency = target * RF_DIV.
void setFrequency(double freqMHz) {
  double vco = freqMHz * (double)RF_DIV;        // VCO frequency in MHz
  double n = vco / FPFD_MHZ;                     // total division ratio

  uint32_t intVal = (uint32_t)n;                 // 16-bit integer part
  uint32_t fracVal = (uint32_t)(((n - intVal) * (double)MOD_VAL) + 0.5);

  // Handle rounding that pushes FRAC up to MOD.
  if (fracVal >= MOD_VAL) {
    fracVal = 0;
    intVal += 1;
  }

  // R0: INT[30:15], FRAC[14:3], control 000
  uint32_t r0 = (intVal << 15) | (fracVal << 3) | 0x0;

  // R1: prescaler 8/9 (DB27), phase=1 (DB15), MOD[14:3], control 001
  uint32_t r1 = (1UL << 27) | (1UL << 15) | (MOD_VAL << 3) | 0x1;

  // R2: low-noise mode, MUXOUT=digital lock detect, R=1, CP=5mA,
  // LDF=frac-N, PD polarity positive (passive filter), control 010
  uint32_t r2 = 0x18005E42;

  // R3: standard frac-N settings (6ns ABP, band-sel mode low), control 011
  uint32_t r3 = 0x000004B3;

  // R4: feedback=fundamental(VCO), RF divider select, band-select-divider=250
  // (25MHz/250 = 100kHz < 125kHz), RF output enabled, +5dBm, control 100
  uint32_t r4 = (1UL << 23) | (RF_DIV_SEL << 20) | (250UL << 12) | 0x3C;

  // R5: LD pin = digital lock detect, control 101
  uint32_t r5 = 0x00580005;

  // ADF4351 requires writing from R5 down to R0; R0 last triggers VCO autocal.
  writeRegister(r5);
  writeRegister(r4);
  writeRegister(r3);
  writeRegister(r2);
  writeRegister(r1);
  writeRegister(r0);
}

void setup() {
  Serial.begin(9600);

  pinMode(CE_PIN, OUTPUT);
  pinMode(LE_PIN, OUTPUT);
  digitalWrite(CE_PIN, HIGH);   // enable chip
  digitalWrite(LE_PIN, HIGH);

  SPI.begin();
  SPI.setClockDivider(SPI_CLOCK_DIV64);
  SPI.setDataMode(SPI_MODE0);

  delay(100);
  Serial.println("# ADF4351 ODMR sweep");
}

void loop() {
  for (double f = F_START; f <= F_STOP + 1e-6; f += F_STEP) {
    setFrequency(f);
    delay(SETTLE_MS);
    Serial.println(f, 3);   // echo current frequency in MHz
  }

  Serial.println("# sweep complete");
  delay(2000);   // pause before repeating the sweep
}
