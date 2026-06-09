# Li-Fi / VLC Educational Simulators

This repository contains a set of interactive Python simulators developed for educational analysis of Li-Fi and Visible Light Communication (VLC) systems.

The project focuses on VLC baseband channel modeling, channel DC gain, Lambertian LED radiation, LOS channel gain, received optical power, SNR performance, L-PPM transmitter waveform generation, PPM slot analysis, bits-per-symbol analysis, slot duration analysis, and theoretical L-PPM BER visualization.

---

## Project Purpose

The main purpose of this project is to visualize important Li-Fi / VLC communication concepts with interactive Python simulations.

Instead of only presenting theoretical formulas, this project allows users to change system parameters with sliders and observe how the communication system behavior changes in real time.

This project is designed for:

* educational demonstrations,
* communication systems learning,
* Li-Fi / VLC project presentations,
* academic report support,
* visualization of optical wireless communication concepts.

---

## Main Topics

This project includes the following Li-Fi / VLC topics:

1. Baseband VLC channel model
2. Channel impulse response and DC gain H(0)
3. Lambertian LED radiation pattern
4. LOS DC channel gain
5. Received optical power
6. SNR performance analysis
7. L-PPM transmitter waveform
8. Single-symbol PPM slot pulse
9. Bits per symbol in L-PPM
10. Slot duration analysis
11. Theoretical L-PPM BER analysis

---

## System Model

The basic VLC baseband channel model used in this project is:

```text
Y(t) = R · X(t) * h(t) + N(t)
```

where:

* `Y(t)` is the received electrical signal,
* `X(t)` is the transmitted optical power signal,
* `h(t)` is the VLC channel impulse response,
* `R` is the photodetector responsivity,
* `N(t)` is the receiver noise,
* `*` represents convolution.

This simplified model helps to understand how optical transmission, channel response, photodetector responsivity, and receiver noise affect the received signal.

---

## Repository Structure

```text
lifi-vlc-educational-simulators/
│
├── README.md
├── requirements.txt
├── .gitignore
├── LICENSE
│
├── simulators/
│   ├── 01_lifi_vlc_baseband_channel_simulator.py
│   ├── 02_lifi_vlc_channel_dc_gain_h0_simulator.py
│   ├── 03_lifi_vlc_lambertian_pattern_simulator.py
│   ├── 04_lifi_vlc_los_dc_gain_simulator.py
│   ├── 05_lifi_vlc_received_optical_power_simulator.py
│   ├── 06_lifi_vlc_snr_performance_simulator.py
│   ├── 07_lifi_vlc_lppm_transmitter_simulator.py
│   ├── 08_lifi_vlc_ppm_slot_pulse_simulator.py
│   ├── 09_lifi_vlc_ppm_bits_per_symbol_simulator.py
│   ├── 10_lifi_vlc_lppm_slot_duration_simulator.py
│   └── 11_lifi_vlc_lppm_ber_simulator.py
│
├── assets/
│   └── screenshots/
│
├── outputs/
│   └── figures/
│
└── report/
    └── project_report.pdf
```

---

## Simulators

| No | File                                              | Description                                                                       |
| -: | ------------------------------------------------- | --------------------------------------------------------------------------------- |
| 01 | `01_lifi_vlc_baseband_channel_simulator.py`       | Visualizes the baseband VLC channel model `Y(t) = R·X(t)*h(t) + N(t)`             |
| 02 | `02_lifi_vlc_channel_dc_gain_h0_simulator.py`     | Shows the relationship between channel impulse response `h(t)` and DC gain `H(0)` |
| 03 | `03_lifi_vlc_lambertian_pattern_simulator.py`     | Visualizes Lambertian order and LED radiation pattern                             |
| 04 | `04_lifi_vlc_los_dc_gain_simulator.py`            | Simulates LOS DC channel gain based on VLC geometry                               |
| 05 | `05_lifi_vlc_received_optical_power_simulator.py` | Shows received optical power using `P_r = H(0)P_t`                                |
| 06 | `06_lifi_vlc_snr_performance_simulator.py`        | Analyzes SNR behavior with respect to `R`, `H(0)`, `P_t`, and noise variance      |
| 07 | `07_lifi_vlc_lppm_transmitter_simulator.py`       | Generates an ideal L-PPM transmitter waveform                                     |
| 08 | `08_lifi_vlc_ppm_slot_pulse_simulator.py`         | Visualizes a single-symbol PPM slot pulse                                         |
| 09 | `09_lifi_vlc_ppm_bits_per_symbol_simulator.py`    | Shows the relationship between PPM order and bits per symbol                      |
| 10 | `10_lifi_vlc_lppm_slot_duration_simulator.py`     | Analyzes slot duration using `T_slot = T/L`                                       |
| 11 | `11_lifi_vlc_lppm_ber_simulator.py`               | Visualizes theoretical L-PPM BER behavior                                         |

---

## Mathematical Background

### 1. Channel DC Gain

The DC channel gain is defined as:

```text
H(0) = ∫ h(t) dt
```

In discrete time, it can be approximated as:

```text
H(0) ≈ Σ h[n] Δt
```

This relation shows how the impulse response contributes to the total channel gain.

---

### 2. Lambertian Order

The Lambertian order of an LED is calculated as:

```text
m = ln(0.5) / ln(cos(Phi_half))
```

where `Phi_half` is the LED half-power semi-angle.

The normalized Lambertian radiation pattern is:

```text
I(phi) = cos^m(phi)
```

---

### 3. LOS DC Channel Gain

The line-of-sight DC channel gain is modeled as:

```text
H_LOS(0) = ((m + 1) A_PD / (2πd²)) · cos^m(Phi) · T_s · g · cos(psi)
```

This model is valid when the incidence angle is inside the receiver field of view:

```text
0 ≤ psi ≤ psi_c
```

Otherwise:

```text
H_LOS(0) = 0
```

---

### 4. Received Optical Power

The received optical power is calculated as:

```text
P_r = H(0) · P_t
```

where:

* `P_r` is the received optical power,
* `H(0)` is the channel DC gain,
* `P_t` is the transmitted optical power.

---

### 5. SNR Model

The simplified SNR model is:

```text
SNR = (R² H(0)² P_t²) / σ_n²
```

where:

* `R` is the photodetector responsivity,
* `H(0)` is the channel DC gain,
* `P_t` is the transmitted optical power,
* `σ_n²` is the receiver noise variance.

---

### 6. L-PPM Transmitter Signal

The ideal L-PPM transmitter signal is modeled as:

```text
x(t) = Σ A · p_lk(t - kT)
```

where:

* `A` is the pulse amplitude,
* `T` is the symbol duration,
* `L` is the PPM order,
* `p_lk(t)` is the selected slot pulse.

---

### 7. PPM Slot Pulse

A single PPM slot pulse is defined as:

```text
p_l(t) = 1,  if ((l-1)T/L) ≤ t < lT/L
p_l(t) = 0,  otherwise
```

---

### 8. Bits per Symbol

For L-PPM:

```text
b = log2(L)
```

where:

* `L` is the PPM order,
* `b` is the number of bits per symbol.

---

### 9. Slot Duration

The slot duration is:

```text
T_slot = T / L
```

Increasing `L` makes each slot shorter for the same symbol duration.

---

### 10. Theoretical L-PPM BER

The theoretical BER expression used in the BER simulator is:

```text
BER_PPM = 1/2 · erfc( 1/(2√2) · √(SNR · L/(2log2(L))) )
```

This simulator is not a Monte Carlo simulation. It only visualizes the theoretical BER behavior.

---

## Installation

First, clone the repository:

```bash
git clone https://github.com/YOUR_USERNAME/lifi-vlc-educational-simulators.git
cd lifi-vlc-educational-simulators
```

Install the required Python packages:

```bash
pip install -r requirements.txt
```

---

## Requirements

The required Python packages are:

```text
numpy
matplotlib
scipy
```

Recommended Python version:

```text
Python 3.9 or newer
```

---

## How to Run

Each simulator can be run independently.

Example:

```bash
python simulators/01_lifi_vlc_baseband_channel_simulator.py
```

Another example:

```bash
python simulators/11_lifi_vlc_lppm_ber_simulator.py
```

If you are using macOS and VS Code, you can also run the files directly from the terminal inside the project folder.

---

## Example Usage

1. Open a simulator.
2. Change the slider values.
3. Observe how the plots and system parameters change.
4. Use the generated visualizations in a report or presentation.

For example:

* Increase `H(0)` to observe higher received power.
* Increase noise variance to observe lower SNR.
* Increase PPM order `L` to observe higher bits per symbol.
* Increase `L` while keeping `T` constant to observe shorter slot duration.
* Change the LED half-power semi-angle to observe the Lambertian radiation pattern.
* Change LOS distance and incidence angle to observe the LOS DC channel gain.

---

## Educational Scope

This project is designed as an educational simulation package.

The simulators are simplified and focus on conceptual understanding. They are useful for learning and demonstrating how Li-Fi / VLC parameters affect system behavior.

The project does not aim to provide a complete hardware-accurate Li-Fi link budget or a full experimental VLC communication system. Instead, it provides interactive visual models for understanding the main physical and communication relationships.

---

## Limitations

This project does not fully model every real-world Li-Fi / VLC effect.

The following effects are simplified or not included in all simulators:

* LED nonlinearity
* LED bandwidth limitation
* photodetector circuit noise model
* ambient light interference
* optical filter implementation
* receiver synchronization
* complete multipath ray tracing
* full hardware link budget
* experimental validation
* real-time communication hardware
* complete receiver decision logic
* advanced channel coding
* adaptive modulation

Therefore, the results should be interpreted as educational and theoretical visualizations rather than complete hardware-accurate simulations.

---

## Suggested Folder Usage

The `simulators/` folder contains all Python simulation files.

The `assets/screenshots/` folder can be used for screenshots of the simulator outputs.

The `outputs/figures/` folder can be used for saved figures generated by the simulators.

The `report/` folder can be used for the final project report or presentation-related documents.

---

## Author

Selhan Coşkun
Department of Electrical and Electronics Engineering
Abdullah Gül University

---

## License

This project is prepared for educational and academic purposes.

---

## Acknowledgment

This project was developed as part of a Li-Fi / VLC educational simulation study. The aim is to support visual learning of optical wireless communication systems by combining theoretical formulas with interactive Python-based visualizations.
