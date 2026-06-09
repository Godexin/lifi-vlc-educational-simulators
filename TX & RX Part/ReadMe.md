# Li-Fi Based Communication Project

## 1. Project Overview

This project implements a **Li-Fi based indoor communication prototype** for transmitting sensor data through visible light.

The system uses:

- **ESP32** as the transmitter controller
- **LED / LED driver** as the optical transmitter
- **Photodiode + analog receiver circuit** as the optical receiver
- **PPM (Pulse Position Modulation)** as the modulation method
- **Software framing** for packet synchronization and data recovery

The main idea is to send sensor data, such as temperature, humidity, and machine status, by modulating an LED. The receiver detects the light pulses using a photodiode and reconstructs the original data.

---

## 2. Project Motivation

In indoor environments such as server rooms, banks, industrial rooms, and data centers, sensor data must be monitored continuously.

However, Wi-Fi or modem-based systems can suffer from:

- Network failures
- RF interference
- Security risks
- Dependency on modem/router infrastructure
- Long maintenance time during communication failures

Li-Fi provides a local optical communication method where data is transmitted through light. Since visible light does not easily pass through walls, Li-Fi can provide a physically confined and secure communication channel.

---

## 3. System Architecture

```text
+------------------+
| Sensor Data      |
| DHT11 / Status   |
+--------+---------+
         |
         v
+------------------+
| ESP32 TX Node    |
| Frame + PPM      |
+--------+---------+
         |
         v
+------------------+
| MOSFET LED Driver|
+--------+---------+
         |
         v
+------------------+
| LED Optical TX   |
+--------+---------+
         |
         v
   Visible Light Link
         |
         v
+------------------+
| Photodiode RX    |
+--------+---------+
         |
         v
+------------------+
| TIA / Filter     |
+--------+---------+
         |
         v
+------------------+
| Comparator / ADC |
+--------+---------+
         |
         v
+------------------+
| ESP32 RX Node    |
| PPM Decoder      |
+--------+---------+
         |
         v
+------------------+
| Decoded Data     |
+------------------+
```

---

## 4. Work Package 4 Scope

This README mainly focuses on **WP4: Modulation Selection and Software Framing**.

WP4 includes:

- Selecting the modulation method
- Designing the PPM symbol structure
- Defining timing parameters
- Creating the frame format
- Calculating TX timing values
- Calculating RX signal levels
- Estimating optical link behavior
- Defining packet-level performance metrics

---

## 5. Selected Modulation Method

The selected modulation technique is:

```text
4-PPM: 4-Level Pulse Position Modulation
```

In 4-PPM, each symbol period is divided into four time slots. Only one pulse exists inside each symbol period. The position of the pulse represents the transmitted data bits.

---

## 6. 4-PPM Mapping

Since there are four possible pulse positions, each symbol carries:

```text
log2(4) = 2 bits
```

The mapping is:

| Data Bits | Pulse Position |
|----------|----------------|
| 00       | Slot 0         |
| 01       | Slot 1         |
| 10       | Slot 2         |
| 11       | Slot 3         |

Visual representation:

```text
Symbol period:
| Slot 0 | Slot 1 | Slot 2 | Slot 3 |

Data = 00:
| Pulse  |        |        |        |

Data = 01:
|        | Pulse  |        |        |

Data = 10:
|        |        | Pulse  |        |

Data = 11:
|        |        |        | Pulse  |
```

---

## 7. Why PPM Instead of OOK?

OOK means **On-Off Keying**. It is simpler because the LED is turned ON or OFF directly according to the bit value.

However, OOK has disadvantages in visible light communication:

- Long sequences of `1` or `0` may cause brightness changes
- Flicker may become visible
- Average optical power depends on transmitted data
- Synchronization can be weaker

PPM was selected because:

- It reduces visible flicker risk
- It provides more stable average optical power
- It gives clear symbol timing
- It is suitable for low-data-rate sensor communication
- It improves synchronization structure

Comparison:

| Feature | OOK | PPM |
|--------|-----|-----|
| Principle | LED ON/OFF | Pulse position |
| Complexity | Low | Medium |
| Flicker Risk | Higher | Lower |
| Average Optical Power | Data dependent | More stable |
| Synchronization | Weaker | Stronger |
| Timing Requirement | Lower | Higher |
| Selected Method | No | Yes |

---

# 8. Main Timing Parameters

The current prototype uses the following timing parameters:

| Parameter | Symbol | Value |
|----------|--------|-------|
| Slot duration | `Tslot` | 500 us |
| Pulse width | `Tpulse` | 125 us |
| Number of slots | `M` | 4 |
| Bits per symbol | `log2(M)` | 2 bits |
| Symbol duration | `Tsym` | 2 ms |

These values are selected for early testing and oscilloscope-level verification. They are not final high-speed parameters.

---

# 9. TX-Side PPM Timing Calculations

## 9.1 Symbol Duration

For M-PPM:

```text
Tsym = M × Tslot
```

For 4-PPM:

```text
M = 4
Tslot = 500 us
```

Therefore:

```text
Tsym = 4 × 500 us
Tsym = 2000 us
Tsym = 2 ms
```

Result:

```text
Symbol duration = 2 ms
```

---

## 9.2 Bits per Symbol

For M-PPM:

```text
Bits per symbol = log2(M)
```

For 4-PPM:

```text
Bits per symbol = log2(4)
Bits per symbol = 2 bits
```

Result:

```text
Each PPM symbol carries 2 bits.
```

---

## 9.3 Symbol Rate

```text
Symbol rate = 1 / Tsym
```

```text
Symbol rate = 1 / 2 ms
Symbol rate = 1 / 0.002 s
Symbol rate = 500 symbols/s
```

Result:

```text
Symbol rate = 500 symbols/s
```

---

## 9.4 Raw Bit Rate

```text
Raw bit rate = Bits per symbol × Symbol rate
```

```text
Raw bit rate = 2 × 500
Raw bit rate = 1000 bit/s
```

Result:

```text
Raw bit rate = 1 kbps
```

Alternative calculation:

```text
Rb = log2(M) / (M × Tslot)
```

```text
Rb = 2 / (4 × 500 us)
Rb = 2 / 0.002
Rb = 1000 bit/s
```

---

## 9.5 Pulse Duty Cycle Inside Active Slot

```text
Duty_active_slot = Tpulse / Tslot
```

```text
Duty_active_slot = 125 us / 500 us
Duty_active_slot = 0.25
Duty_active_slot = 25%
```

Result:

```text
The LED is ON for 25% of the selected slot.
```

---

## 9.6 Average Duty Cycle per Symbol

Only one pulse exists inside one symbol period.

```text
Duty_symbol = Tpulse / Tsym
```

```text
Duty_symbol = 125 us / 2000 us
Duty_symbol = 0.0625
Duty_symbol = 6.25%
```

Result:

```text
Average LED duty cycle per symbol = 6.25%
```

---

## 9.7 Pulse Frequency Approximation

Since one pulse is transmitted in every symbol:

```text
Pulse repetition rate = Symbol rate
```

```text
Pulse repetition rate = 500 pulses/s
```

Result:

```text
Pulse repetition rate = 500 Hz
```

---

## 9.8 Required Slot Duration for Higher Data Rates

The target data rate of the project is:

```text
50 kbps to 100 kbps
```

For 4-PPM:

```text
Rb = 2 / (4 × Tslot)
```

Simplified:

```text
Rb = 1 / (2 × Tslot)
```

Therefore:

```text
Tslot = 1 / (2 × Rb)
```

### For 50 kbps

```text
Tslot = 1 / (2 × 50000)
Tslot = 1 / 100000
Tslot = 10 us
```

### For 100 kbps

```text
Tslot = 1 / (2 × 100000)
Tslot = 1 / 200000
Tslot = 5 us
```

Required slot durations:

| Target Data Rate | Required Slot Duration |
|------------------|------------------------|
| 1 kbps | 500 us |
| 50 kbps | 10 us |
| 100 kbps | 5 us |

Conclusion:

```text
The current 500 us slot time is suitable for testing.
For 50–100 kbps operation, slot duration must be reduced to 10–5 us.
```

---

# 10. Frame Format

The proposed frame format is:

```text
[Preamble] [Header] [Payload] [Checksum]
```

| Field | Size | Purpose |
|------|------|---------|
| Preamble | 1 byte | Start-of-frame detection |
| Header | 1 byte | Payload length or packet type |
| Payload | Variable | Sensor data |
| Checksum | 1 byte | Error detection |

---

## 10.1 Preamble

The selected preamble is:

```text
0x1B
```

Binary form:

```text
0x1B = 00011011
```

Purpose of preamble:

- Detect frame start
- Synchronize receiver timing
- Align PPM slot boundaries
- Prevent random noise from being decoded as data

---

## 10.2 Example Payload

Example sensor data:

```text
Temperature    = 24 °C
Humidity       = 48 %
Machine Status = 1
```

Hexadecimal values:

```text
Temperature    = 24 decimal = 0x18
Humidity       = 48 decimal = 0x30
Machine Status = 1 decimal  = 0x01
```

Payload:

```text
[0x18] [0x30] [0x01]
```

---

## 10.3 Checksum Calculation

A simple XOR checksum can be used:

```text
Checksum = Temperature XOR Humidity XOR Machine_Status
```

Calculation:

```text
Temperature = 0x18
Humidity    = 0x30
Status      = 0x01
```

Step by step:

```text
0x18 XOR 0x30 = 0x28
0x28 XOR 0x01 = 0x29
```

Result:

```text
Checksum = 0x29
```

---

## 10.4 Example Full Frame

```text
Preamble = 0x1B
Header   = 0x03
Temp     = 0x18
Humidity = 0x30
Status   = 0x01
Checksum = 0x29
```

Full frame:

```text
[0x1B] [0x03] [0x18] [0x30] [0x01] [0x29]
```

Total size:

```text
6 bytes = 48 bits
```

---

# 11. Frame Transmission Calculations

## 11.1 Number of Bits

```text
Frame size = 6 bytes
1 byte = 8 bits
```

```text
Total bits = 6 × 8
Total bits = 48 bits
```

---

## 11.2 Number of PPM Symbols

Each 4-PPM symbol carries 2 bits.

```text
Number of symbols = Total bits / Bits per symbol
```

```text
Number of symbols = 48 / 2
Number of symbols = 24 symbols
```

---

## 11.3 Frame Transmission Time

Each symbol duration is 2 ms.

```text
Tframe = Number of symbols × Tsym
```

```text
Tframe = 24 × 2 ms
Tframe = 48 ms
```

Alternative:

```text
Tframe = Total bits / Raw bit rate
```

```text
Tframe = 48 bits / 1000 bit/s
Tframe = 0.048 s
Tframe = 48 ms
```

Result:

```text
A 6-byte frame takes 48 ms to transmit.
```

---

## 11.4 Maximum Frame Rate

Ignoring idle time:

```text
Frame rate = 1 / Tframe
```

```text
Frame rate = 1 / 0.048
Frame rate = 20.83 frames/s
```

Result:

```text
Maximum theoretical frame rate ≈ 20.8 frames/s
```

---

## 11.5 Payload Efficiency

Payload size:

```text
Payload = 3 bytes = 24 bits
```

Total frame size:

```text
Frame = 6 bytes = 48 bits
```

Efficiency:

```text
Efficiency = Payload bits / Total frame bits
```

```text
Efficiency = 24 / 48
Efficiency = 0.5
Efficiency = 50%
```

Result:

```text
Frame efficiency = 50%
```

---

## 11.6 Effective Payload Throughput

Raw bit rate:

```text
Rb = 1000 bit/s
```

Frame efficiency:

```text
η = 50% = 0.5
```

Effective payload throughput:

```text
Throughput_payload = Rb × η
```

```text
Throughput_payload = 1000 × 0.5
Throughput_payload = 500 bit/s
```

Result:

```text
Effective payload throughput = 500 bit/s
```

This is lower than raw bit rate because the frame contains overhead fields.

---

# 12. TX Circuit Design

## 12.1 TX Hardware Structure

```text
ESP32 GPIO → MOSFET Gate
MOSFET Drain → LED Cathode
LED Anode → Current-Limiting Resistor → VCC
MOSFET Source → GND
```

The ESP32 GPIO does not directly drive the high-power LED.  
The MOSFET is used as a fast switching element.

---

## 12.2 LED Current-Limiting Resistor

The LED current-limiting resistor is calculated as:

```text
Rled = (Vcc - Vf_LED - VDS_MOSFET) / Iled
```

Where:

| Symbol | Description |
|--------|-------------|
| `Vcc` | Supply voltage |
| `Vf_LED` | LED forward voltage |
| `VDS_MOSFET` | MOSFET drain-source voltage drop |
| `Iled` | Desired LED current |

Example values:

```text
Vcc = 5 V
Vf_LED = 3.2 V
VDS_MOSFET = 0.1 V
Iled = 20 mA = 0.02 A
```

Calculation:

```text
Rled = (5 - 3.2 - 0.1) / 0.02
Rled = 1.7 / 0.02
Rled = 85 ohm
```

Nearest standard resistor values:

```text
82 ohm or 91 ohm
```

For safer first testing:

```text
Use 100 ohm or higher.
```

---

## 12.3 LED Current with 100 Ohm Resistor

If:

```text
Rled = 100 ohm
```

Then:

```text
Iled = (Vcc - Vf_LED - VDS_MOSFET) / Rled
```

```text
Iled = (5 - 3.2 - 0.1) / 100
Iled = 1.7 / 100
Iled = 0.017 A
Iled = 17 mA
```

Result:

```text
LED current ≈ 17 mA
```

---

## 12.4 LED Electrical Power

```text
Pled = Vf_LED × Iled
```

Using:

```text
Vf_LED = 3.2 V
Iled = 20 mA = 0.02 A
```

```text
Pled = 3.2 × 0.02
Pled = 0.064 W
Pled = 64 mW
```

Result:

```text
LED electrical power = 64 mW
```

---

## 12.5 Current-Limiting Resistor Power

```text
Presistor = Iled² × Rled
```

Using:

```text
Iled = 20 mA = 0.02 A
Rled = 85 ohm
```

```text
Presistor = (0.02)² × 85
Presistor = 0.0004 × 85
Presistor = 0.034 W
Presistor = 34 mW
```

A standard resistor rating is enough:

```text
0.25 W resistor is suitable.
```

---

## 12.6 Average LED Current in PPM

Peak LED current:

```text
Ipeak = 20 mA
```

Average PPM duty cycle:

```text
Duty_symbol = 6.25% = 0.0625
```

Average current:

```text
Iavg = Ipeak × Duty_symbol
```

```text
Iavg = 20 mA × 0.0625
Iavg = 1.25 mA
```

Result:

```text
Average LED current = 1.25 mA
```

---

## 12.7 Average LED Electrical Power

```text
Pavg = Vf_LED × Iavg
```

```text
Pavg = 3.2 V × 1.25 mA
Pavg = 3.2 × 0.00125
Pavg = 0.004 W
Pavg = 4 mW
```

Result:

```text
Average LED electrical power = 4 mW
```

---

## 12.8 MOSFET Power Dissipation

Approximate MOSFET conduction loss:

```text
PMOSFET = Iled² × RDS_on
```

Assume:

```text
Iled = 20 mA = 0.02 A
RDS_on = 0.1 ohm
```

```text
PMOSFET = (0.02)² × 0.1
PMOSFET = 0.0004 × 0.1
PMOSFET = 0.00004 W
PMOSFET = 0.04 mW
```

Result:

```text
MOSFET conduction loss is very small at 20 mA.
```

---

## 12.9 GPIO Timing Requirement

Current timing:

```text
Tpulse = 125 us
Tslot = 500 us
```

The ESP32 must generate pulses shorter than or equal to:

```text
125 us
```

Software delay loops can introduce jitter. Therefore, timer-based control or direct register control is preferred.

---

# 13. RX Circuit Design

## 13.1 RX Hardware Structure

```text
Optical Signal
     ↓
Photodiode
     ↓
Transimpedance Amplifier
     ↓
Filter / Comparator
     ↓
ESP32 Digital Input or ADC
     ↓
PPM Decoder
```

The photodiode converts received light into current. The receiver circuit converts this current into a voltage.

---

## 13.2 Photodiode Current Calculation

Photodiode current is calculated as:

```text
Ipd = Rλ × Prx
```

Where:

| Symbol | Description |
|--------|-------------|
| `Ipd` | Photodiode current |
| `Rλ` | Photodiode responsivity |
| `Prx` | Received optical power |

Example values:

```text
Rλ = 0.4 A/W
Prx = 10 uW = 10 × 10^-6 W
```

Calculation:

```text
Ipd = 0.4 × 10 × 10^-6
Ipd = 4 × 10^-6 A
Ipd = 4 uA
```

Result:

```text
Photodiode current = 4 uA
```

---

## 13.3 Transimpedance Amplifier Output Voltage

The TIA output voltage is:

```text
Vout = Ipd × Rf
```

Where:

| Symbol | Description |
|--------|-------------|
| `Vout` | TIA output voltage |
| `Ipd` | Photodiode current |
| `Rf` | Feedback resistor |

Example:

```text
Ipd = 4 uA
Rf = 100 kohm
```

Calculation:

```text
Vout = 4 uA × 100 kohm
Vout = 4 × 10^-6 × 100 × 10^3
Vout = 0.4 V
```

Result:

```text
TIA output voltage = 0.4 V
```

---

## 13.4 Required Feedback Resistor

If the desired output voltage is known:

```text
Rf = Vout / Ipd
```

Example:

```text
Vout = 1 V
Ipd = 4 uA
```

Calculation:

```text
Rf = 1 / 4 uA
Rf = 1 / 4 × 10^-6
Rf = 250000 ohm
Rf = 250 kohm
```

Result:

```text
Required feedback resistor = 250 kohm
```

---

## 13.5 TIA Bandwidth Approximation

The feedback resistor and feedback capacitor limit the bandwidth:

```text
fc = 1 / (2π × Rf × Cf)
```

Example:

```text
Rf = 100 kohm
Cf = 10 pF
```

Calculation:

```text
fc = 1 / (2π × 100000 × 10 × 10^-12)
fc = 1 / (6.283 × 10^-6)
fc ≈ 159154 Hz
fc ≈ 159 kHz
```

Result:

```text
TIA cutoff frequency ≈ 159 kHz
```

---

## 13.6 Required RX Bandwidth from Pulse Width

Pulse width:

```text
Tpulse = 125 us
```

Minimum bandwidth approximation:

```text
BWmin ≈ 1 / Tpulse
```

```text
BWmin = 1 / 125 us
BWmin = 1 / 125 × 10^-6
BWmin = 8000 Hz
BWmin = 8 kHz
```

For sharper pulse detection, choose at least 5 times this value:

```text
BWrecommended ≥ 5 × BWmin
```

```text
BWrecommended ≥ 5 × 8 kHz
BWrecommended ≥ 40 kHz
```

Result:

```text
Receiver bandwidth should be at least 40 kHz for this prototype.
```

Since the example TIA bandwidth is:

```text
159 kHz
```

It is suitable for the current 125 us pulse width.

---

## 13.7 Comparator Threshold Selection

If the expected TIA pulse output is:

```text
Vsignal = 0.4 V
```

A possible comparator threshold can be:

```text
Vthreshold ≈ 0.2 V
```

General rule:

```text
Vnoise < Vthreshold < Vsignal
```

For example:

```text
Vnoise = 50 mV
Vsignal = 400 mV
```

A reasonable threshold:

```text
Vthreshold = 200 mV
```

This threshold must be adjusted experimentally because ambient light and receiver noise can change the signal level.

---

## 13.8 ADC Reading Resolution on ESP32

If ESP32 ADC is used with 12-bit resolution:

```text
ADC levels = 2^12 = 4096
```

Assume ADC reference voltage:

```text
Vref = 3.3 V
```

ADC voltage resolution:

```text
ADC_step = Vref / 4096
```

```text
ADC_step = 3.3 / 4096
ADC_step = 0.000805 V
ADC_step = 0.805 mV
```

If:

```text
Vsignal = 0.4 V
```

ADC count:

```text
ADC_count = Vsignal / ADC_step
```

```text
ADC_count = 0.4 / 0.000805
ADC_count ≈ 497
```

Result:

```text
0.4 V corresponds to approximately 497 ADC counts.
```

---

# 14. Optical Link Budget Estimation

## 14.1 Simplified Free-Space Optical Estimate

A rough received optical power estimate is:

```text
Prx ≈ Ptx × Arx / (4πd²)
```

Where:

| Symbol | Description |
|--------|-------------|
| `Prx` | Received optical power |
| `Ptx` | Transmitted optical power |
| `Arx` | Photodiode active area |
| `d` | TX-RX distance |

This is a simplified isotropic model. Real LEDs are directional, so practical measurements can be better if the LED and photodiode are aligned.

---

## 14.2 Example Optical Link Calculation

Assume:

```text
Ptx = 10 mW = 0.01 W
d = 1 m
Arx = 7 mm²
```

Convert receiver area:

```text
Arx = 7 mm² = 7 × 10^-6 m²
```

Calculation:

```text
Prx ≈ 0.01 × (7 × 10^-6) / (4π × 1²)
Prx ≈ 0.01 × 7 × 10^-6 / 12.566
Prx ≈ 5.57 × 10^-9 W
Prx ≈ 5.57 nW
```

Result:

```text
Received optical power ≈ 5.57 nW
```

This is a weak signal, so receiver gain and optical alignment are critical.

---

## 14.3 Photodiode Current from Optical Link

Using:

```text
Prx = 5.57 nW
Rλ = 0.4 A/W
```

```text
Ipd = Rλ × Prx
```

```text
Ipd = 0.4 × 5.57 × 10^-9
Ipd = 2.23 × 10^-9 A
Ipd = 2.23 nA
```

Result:

```text
Photodiode current ≈ 2.23 nA
```

---

## 14.4 TIA Output from Link Estimate

Using:

```text
Ipd = 2.23 nA
Rf = 100 kohm
```

```text
Vout = Ipd × Rf
Vout = 2.23 × 10^-9 × 100 × 10^3
Vout = 223 × 10^-6 V
Vout = 223 uV
```

Result:

```text
TIA output ≈ 223 uV
```

This is too small for reliable direct detection.

Therefore, the practical system should improve the received signal by using:

- Higher optical power LED
- Better TX/RX alignment
- Narrower beam LED
- Optical lens
- Reflector
- Larger photodiode active area
- Higher feedback resistor
- Low-noise op-amp
- Shielded receiver box
- Optical filter

---

# 15. Improved Link Example with Better Coupling

Assume better optical coupling provides:

```text
Prx = 10 uW
```

Then:

```text
Ipd = Rλ × Prx
```

```text
Ipd = 0.4 × 10 × 10^-6
Ipd = 4 uA
```

With:

```text
Rf = 100 kohm
```

```text
Vout = 4 uA × 100 kohm
Vout = 0.4 V
```

Result:

```text
With better coupling, the receiver output can reach approximately 0.4 V.
```

This is suitable for comparator or ADC-based pulse detection.

---

# 16. Noise and Ambient Light Considerations

## 16.1 Ambient Light Effect

Ambient light creates a DC current in the photodiode.

Total photodiode current:

```text
Ipd_total = Iambient + Isignal
```

Where:

| Symbol | Description |
|--------|-------------|
| `Iambient` | Current caused by background light |
| `Isignal` | Current caused by LED pulse |

The receiver must detect the pulse component, not the DC ambient component.

Possible solutions:

- Optical shielding
- Optical filter
- AC coupling
- High-pass filtering
- Comparator threshold adjustment
- Adaptive thresholding
- Closed-box test environment

---

## 16.2 Shot Noise Approximation

Photodiode shot noise current is approximately:

```text
in = sqrt(2qIdcB)
```

Where:

| Symbol | Description |
|--------|-------------|
| `in` | Shot noise current |
| `q` | Electron charge, 1.602 × 10^-19 C |
| `Idc` | DC photodiode current |
| `B` | Receiver bandwidth |

Example:

```text
q = 1.602 × 10^-19 C
Idc = 10 uA
B = 100 kHz
```

Calculation:

```text
in = sqrt(2 × 1.602 × 10^-19 × 10 × 10^-6 × 100 × 10^3)
in = sqrt(3.204 × 10^-16)
in ≈ 1.79 × 10^-8 A
in ≈ 17.9 nA
```

Result:

```text
Shot noise current ≈ 17.9 nA
```

With:

```text
Rf = 100 kohm
```

Equivalent noise voltage:

```text
vn = in × Rf
vn = 17.9 nA × 100 kohm
vn = 1.79 mV
```

Result:

```text
Shot noise output voltage ≈ 1.79 mV
```

If the signal output is around 0.4 V, this noise level is acceptable.

---

# 17. Performance Metrics

## 17.1 Packet Delivery Ratio

Packet Delivery Ratio is:

```text
PDR = Successfully received packets / Total transmitted packets
```

Percentage:

```text
PDR(%) = PDR × 100
```

Example:

```text
Total transmitted packets = 1000
Successfully received packets = 960
```

```text
PDR = 960 / 1000
PDR = 0.96
PDR = 96%
```

Target:

```text
PDR ≥ 95%
```

---

## 17.2 Packet Error Rate

Packet Error Rate is:

```text
PER = Erroneous packets / Total transmitted packets
```

Percentage:

```text
PER(%) = PER × 100
```

Example:

```text
Total transmitted packets = 1000
Erroneous packets = 40
```

```text
PER = 40 / 1000
PER = 0.04
PER = 4%
```

Target:

```text
PER ≤ 5%
```

---

## 17.3 Throughput

Throughput is:

```text
Throughput = Successfully received payload bits / Total test time
```

Example:

```text
Payload size = 3 bytes = 24 bits
Successfully received packets = 960
Total test time = 60 s
```

```text
Throughput = 960 × 24 / 60
Throughput = 23040 / 60
Throughput = 384 bit/s
```

Result:

```text
Effective throughput = 384 bit/s
```

---

## 17.4 Bit Error Rate

Bit Error Rate is:

```text
BER = Number of wrong bits / Total received bits
```

Example:

```text
Wrong bits = 12
Total received bits = 48000
```

```text
BER = 12 / 48000
BER = 0.00025
BER = 2.5 × 10^-4
```

---

# 18. TX Software Flow

```text
1. Read sensor values
2. Create payload bytes
3. Add preamble
4. Add header
5. Calculate checksum
6. Convert frame bytes into bit stream
7. Group bits into 2-bit symbols
8. Convert each 2-bit symbol into PPM slot index
9. Generate LED pulse in selected slot
10. Repeat for all symbols
11. Send next frame
```

---

## 18.1 TX Pseudocode

```cpp
read_sensor_data();

frame[0] = PREAMBLE;
frame[1] = PAYLOAD_LENGTH;
frame[2] = temperature;
frame[3] = humidity;
frame[4] = machine_status;
frame[5] = checksum;

for (int i = 0; i < frame_length; i++) {
    byte current_byte = frame[i];

    for (int bit = 6; bit >= 0; bit -= 2) {
        uint8_t symbol = (current_byte >> bit) & 0x03;
        transmit_ppm_symbol(symbol);
    }
}
```

---

## 18.2 PPM Symbol Transmission Logic

```cpp
void transmit_ppm_symbol(uint8_t slot_index) {
    for (int slot = 0; slot < 4; slot++) {
        if (slot == slot_index) {
            LED_ON();
            delayMicroseconds(Tpulse_us);
            LED_OFF();
            delayMicroseconds(Tslot_us - Tpulse_us);
        } else {
            LED_OFF();
            delayMicroseconds(Tslot_us);
        }
    }
}
```

Note:

```text
For accurate timing, hardware timer or direct GPIO register control is better than delayMicroseconds().
```

---

# 19. RX Software Flow

```text
1. Sample receiver output
2. Detect rising edge or pulse peak
3. Search for preamble pattern
4. Synchronize slot timing
5. Measure pulse position in each symbol
6. Convert slot position to 2-bit data
7. Reconstruct frame bytes
8. Verify checksum
9. Accept valid packet
10. Reject invalid packet
```

---

## 19.1 RX Pseudocode

```cpp
while (true) {
    if (detect_pulse()) {
        update_timing_state();

        if (preamble_detected()) {
            synchronize_slots();

            for (int s = 0; s < expected_symbol_count; s++) {
                uint8_t slot = detect_ppm_slot();
                uint8_t bits = slot_to_bits(slot);
                append_bits(bits);
            }

            if (checksum_valid()) {
                accept_packet();
            } else {
                reject_packet();
            }
        }
    }
}
```

---

# 20. Main Software Parameters

```cpp
#define LED_PIN 18

static const uint32_t Tslot_us  = 500;
static const uint32_t Tpulse_us = 125;

static const size_t MAX_FRAME_BYTES = 64;
static const size_t MAX_BITS        = MAX_FRAME_BYTES * 8;
static const size_t MAX_PPM_SLOTS   = MAX_BITS / 2;
```

Explanation:

| Parameter | Meaning |
|----------|---------|
| `LED_PIN` | TX LED output pin |
| `Tslot_us` | Duration of each PPM slot |
| `Tpulse_us` | Width of transmitted pulse |
| `MAX_FRAME_BYTES` | Maximum frame size |
| `MAX_BITS` | Maximum number of bits in frame |
| `MAX_PPM_SLOTS` | Number of 2-bit PPM symbols |

---

# 21. Testing Plan

## 21.1 TX Test

TX should be tested by:

- Observing ESP32 GPIO output with oscilloscope
- Checking pulse width
- Checking slot duration
- Checking symbol duration
- Verifying PPM mapping
- Verifying complete frame transmission time

Expected values:

| Measurement | Expected Value |
|------------|----------------|
| Pulse width | 125 us |
| Slot duration | 500 us |
| Symbol duration | 2 ms |
| Frame duration, 6 bytes | 48 ms |

---

## 21.2 RX Test

RX should be tested by:

- Measuring photodiode output
- Measuring TIA output
- Checking pulse amplitude
- Checking ambient light offset
- Adjusting comparator threshold
- Testing preamble detection
- Testing checksum validation

---

## 21.3 Optical Link Test

Optical link should be tested under:

- 10 cm distance
- 25 cm distance
- 50 cm distance
- 1 m distance
- Dark environment
- Normal room light
- Misaligned TX/RX
- Line-of-Sight blocked condition

---

# 22. Expected Project Targets

| Metric | Target |
|--------|--------|
| Packet Delivery Ratio | ≥ 95% |
| Packet Error Rate | ≤ 5% |
| Link Distance | 1 meter |
| Data Rate | 50–100 kbps final target |
| Current Prototype Rate | 1 kbps |
| Modulation | 4-PPM |
| Communication Medium | Visible light |

---

# 23. Current Status

## Completed

- System architecture defined
- PPM selected as main modulation method
- OOK and PPM compared
- 4-PPM symbol mapping created
- Timing parameters selected
- Frame format designed
- TX/RX calculation baseline created
- Initial ESP32 PPM logic drafted
- LED driver calculation completed
- Photodiode/TIA calculation completed

## In Progress

- ESP32 PPM transmitter implementation
- RX-side pulse detection
- Preamble detection
- Checksum validation
- LED driver breadboard testing
- Photodiode receiver testing
- Oscilloscope timing verification
- Optical link measurement

---

# 24. Next Steps

- Complete ESP32 TX code
- Build MOSFET LED driver circuit
- Build photodiode receiver circuit
- Test LED pulse using oscilloscope
- Measure photodiode response
- Implement RX slot synchronization
- Implement preamble detection
- Implement checksum verification
- Measure PDR
- Measure PER
- Measure throughput
- Optimize slot duration for higher data rate
- Compare Li-Fi performance with Wi-Fi fallback scenario

---

# 25. Important Design Notes

- ESP32 GPIO should not directly drive high-power LEDs.
- A MOSFET driver is required for reliable LED switching.
- PPM needs accurate timing.
- Hardware timer control is preferred over software delay.
- Ambient light affects the photodiode receiver.
- Receiver shielding improves signal quality.
- TIA gain must be selected according to received optical power.
- Higher gain reduces bandwidth, so gain-bandwidth tradeoff is important.
- Final data rate depends on LED switching speed, receiver bandwidth, and ESP32 timing accuracy.
- Current 1 kbps timing is for debugging.
- Final 50–100 kbps operation requires slot durations around 10–5 us.

---

# 26. Summary

This project develops a visible-light-based communication prototype for indoor sensor data transmission.

The transmitter converts sensor data into a framed packet and encodes it using 4-PPM. The LED emits short optical pulses according to the PPM slot position. The receiver detects these pulses using a photodiode, amplifies the signal, synchronizes using the preamble, decodes the PPM symbols, reconstructs the frame, and validates it using checksum.

The current timing configuration provides a raw data rate of 1 kbps, which is suitable for early testing. Future improvements will reduce the slot duration to reach the target range of 50–100 kbps.

```
End of README.
```
