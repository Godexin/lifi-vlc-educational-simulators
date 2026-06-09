import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, Button

# ============================================================
# Interactive Li-Fi / VLC L-PPM Transmitter Waveform Simulator
# ============================================================
#
# Purpose:
#   This script interactively visualizes an ideal L-level Pulse
#   Position Modulation (L-PPM) transmitted optical waveform for
#   Li-Fi / Visible Light Communication (VLC) systems.
#
# Mathematical model:
#
#   x(t) = sum_k A * p_{l_k}(t - kT)
#
# where:
#   x(t)    : transmitted optical intensity / optical power waveform
#   A       : pulse amplitude
#   T       : symbol duration
#   L       : PPM order, i.e., number of slots per symbol
#   p_l(t)  : rectangular pulse located at the selected slot
#   l_k     : slot index corresponding to the k-th bit group
#
# Main assumptions:
#   - Ideal rectangular PPM pulses are used.
#   - Only the transmitter waveform is modeled.
#   - LED bandwidth, LED rise/fall time, VLC channel, photodetector,
#     noise, SNR, BER, and receiver decision logic are not included.
#
# Main limitation:
#   This is not a full Li-Fi system simulator. It is an ideal
#   L-PPM transmitter waveform visualization tool.
# ============================================================


# ============================================================
# 1) Global simulation constants
# ============================================================
SAMPLING_FREQUENCY = 100_000          # Hz
RANDOM_SEED = 42                      # Fixed seed for repeatability
VALID_PPM_ORDERS = np.array([2, 4, 8, 16])
MIN_RECOMMENDED_SAMPLES_PER_SLOT = 5


# ============================================================
# 2) Initial parameters
# ============================================================
INITIAL_AMPLITUDE = 1.0
INITIAL_SYMBOL_DURATION = 1e-3        # seconds
INITIAL_NUMBER_OF_SYMBOLS = 5
INITIAL_L_INDEX = 1                   # VALID_PPM_ORDERS[1] = 4


# ============================================================
# 3) Utility functions
# ============================================================
def validate_ppm_parameters(amplitude, symbol_duration, ppm_order,
                            number_of_symbols, sampling_frequency):
    """
    Validate the main L-PPM simulation parameters.

    Parameters
    ----------
    amplitude : float
        Pulse amplitude A.
    symbol_duration : float
        Symbol duration T in seconds.
    ppm_order : int
        PPM order L. Must be one of the allowed powers of two.
    number_of_symbols : int
        Number of PPM symbols to generate.
    sampling_frequency : float
        Sampling frequency in Hz.

    Raises
    ------
    ValueError
        If any parameter is physically or numerically invalid.
    """
    if amplitude <= 0:
        raise ValueError("Amplitude must be positive.")

    if symbol_duration <= 0:
        raise ValueError("Symbol duration must be positive.")

    if sampling_frequency <= 0:
        raise ValueError("Sampling frequency must be positive.")

    if number_of_symbols < 1:
        raise ValueError("Number of symbols must be at least 1.")

    if ppm_order not in VALID_PPM_ORDERS:
        raise ValueError(f"PPM order must be one of {VALID_PPM_ORDERS.tolist()}.")


def generate_bit_sequence(number_of_bits, seed=RANDOM_SEED):
    """
    Generate a repeatable binary bit sequence.

    Parameters
    ----------
    number_of_bits : int
        Number of bits to generate.
    seed : int
        Random seed for repeatable results.

    Returns
    -------
    np.ndarray
        Binary bit sequence containing 0 and 1 values.
    """
    rng = np.random.default_rng(seed)
    return rng.integers(0, 2, size=number_of_bits, dtype=int)


def bits_to_slot_indices(bit_sequence, ppm_order):
    """
    Convert a binary bit sequence into zero-based PPM slot indices.

    In L-PPM, each symbol carries log2(L) bits. Each bit group is
    interpreted as a binary number and mapped to one of L slots.

    Example for L = 4:
        00 -> slot 0
        01 -> slot 1
        10 -> slot 2
        11 -> slot 3

    Parameters
    ----------
    bit_sequence : np.ndarray
        Input binary bit sequence.
    ppm_order : int
        PPM order L.

    Returns
    -------
    np.ndarray
        Zero-based slot indices.
    """
    bits_per_symbol = int(np.log2(ppm_order))

    if len(bit_sequence) % bits_per_symbol != 0:
        raise ValueError("Bit sequence length must be divisible by log2(L).")

    bit_groups = bit_sequence.reshape(-1, bits_per_symbol)

    binary_weights = 2 ** np.arange(bits_per_symbol - 1, -1, -1)
    slot_indices_zero_based = bit_groups @ binary_weights

    return slot_indices_zero_based.astype(int)


def generate_lppm_waveform(amplitude, symbol_duration, ppm_order,
                           number_of_symbols, sampling_frequency,
                           seed=RANDOM_SEED):
    """
    Generate an ideal multi-symbol L-PPM transmitter waveform.

    The target slot duration is T/L. Since the waveform is generated
    in discrete time, the number of samples per slot must be an integer.
    Therefore, the effective simulated slot duration may slightly differ
    from the theoretical slot duration.

    Parameters
    ----------
    amplitude : float
        Pulse amplitude A.
    symbol_duration : float
        Target symbol duration T in seconds.
    ppm_order : int
        PPM order L.
    number_of_symbols : int
        Number of symbols.
    sampling_frequency : float
        Sampling frequency in Hz.
    seed : int
        Random seed for bit generation.

    Returns
    -------
    dict
        Dictionary containing time vector, waveform, bit sequence,
        slot indices, timing parameters, and warnings.
    """
    validate_ppm_parameters(
        amplitude,
        symbol_duration,
        ppm_order,
        number_of_symbols,
        sampling_frequency
    )

    bits_per_symbol = int(np.log2(ppm_order))
    number_of_bits = number_of_symbols * bits_per_symbol

    target_slot_duration = symbol_duration / ppm_order
    ideal_samples_per_slot = target_slot_duration * sampling_frequency

    samples_per_slot = max(1, int(round(ideal_samples_per_slot)))
    samples_per_symbol = ppm_order * samples_per_slot

    effective_slot_duration = samples_per_slot / sampling_frequency
    effective_symbol_duration = samples_per_symbol / sampling_frequency

    total_samples = number_of_symbols * samples_per_symbol

    bit_sequence = generate_bit_sequence(number_of_bits, seed)
    slot_indices_zero_based = bits_to_slot_indices(bit_sequence, ppm_order)
    slot_indices_one_based = slot_indices_zero_based + 1

    waveform = np.zeros(total_samples)

    active_slot_intervals = []

    for symbol_index, slot_zero_based in enumerate(slot_indices_zero_based):
        symbol_start_sample = symbol_index * samples_per_symbol
        active_slot_start_sample = symbol_start_sample + slot_zero_based * samples_per_slot
        active_slot_end_sample = active_slot_start_sample + samples_per_slot

        waveform[active_slot_start_sample:active_slot_end_sample] = amplitude

        active_slot_intervals.append((
            active_slot_start_sample / sampling_frequency,
            active_slot_end_sample / sampling_frequency
        ))

    # For accurate step plotting, append one final sample.
    time_step = np.arange(total_samples + 1) / sampling_frequency
    waveform_step = np.append(waveform, waveform[-1] if len(waveform) > 0 else 0.0)

    slot_duration_error = effective_slot_duration - target_slot_duration
    relative_slot_duration_error = (
        slot_duration_error / target_slot_duration * 100
        if target_slot_duration > 0 else 0.0
    )

    warnings = []

    if samples_per_slot < MIN_RECOMMENDED_SAMPLES_PER_SLOT:
        warnings.append(
            f"Low time resolution: only {samples_per_slot} sample(s) per slot."
        )

    if abs(relative_slot_duration_error) > 1.0:
        warnings.append(
            f"Discrete slot duration differs from target by "
            f"{relative_slot_duration_error:+.2f}%."
        )

    symbol_rate = 1.0 / symbol_duration
    bit_rate = bits_per_symbol / symbol_duration
    duty_cycle = 1.0 / ppm_order
    approximate_average_optical_level = amplitude / ppm_order
    peak_to_average_ratio = ppm_order

    return {
        "time_step": time_step,
        "waveform_step": waveform_step,
        "bit_sequence": bit_sequence,
        "slot_indices_zero_based": slot_indices_zero_based,
        "slot_indices_one_based": slot_indices_one_based,
        "active_slot_intervals": active_slot_intervals,

        "amplitude": amplitude,
        "ppm_order": ppm_order,
        "number_of_symbols": number_of_symbols,
        "bits_per_symbol": bits_per_symbol,

        "target_symbol_duration": symbol_duration,
        "target_slot_duration": target_slot_duration,
        "effective_symbol_duration": effective_symbol_duration,
        "effective_slot_duration": effective_slot_duration,

        "samples_per_slot": samples_per_slot,
        "samples_per_symbol": samples_per_symbol,
        "ideal_samples_per_slot": ideal_samples_per_slot,

        "slot_duration_error": slot_duration_error,
        "relative_slot_duration_error": relative_slot_duration_error,

        "symbol_rate": symbol_rate,
        "bit_rate": bit_rate,
        "duty_cycle": duty_cycle,
        "approximate_average_optical_level": approximate_average_optical_level,
        "peak_to_average_ratio": peak_to_average_ratio,

        "sampling_frequency": sampling_frequency,
        "random_seed": seed,
        "warnings": warnings
    }


def format_bit_groups(bit_sequence, bits_per_symbol):
    """
    Format a bit sequence into groups of bits per symbol.

    Parameters
    ----------
    bit_sequence : np.ndarray
        Binary bit sequence.
    bits_per_symbol : int
        Number of bits carried by one PPM symbol.

    Returns
    -------
    list[str]
        List of bit strings, one for each symbol.
    """
    bit_groups = bit_sequence.reshape(-1, bits_per_symbol)
    return ["".join(str(bit) for bit in group) for group in bit_groups]


def create_information_panel_text(result):
    """
    Create a formatted text block for the information panel.

    Parameters
    ----------
    result : dict
        Output dictionary from generate_lppm_waveform().

    Returns
    -------
    str
        Multiline information string.
    """
    bit_groups = format_bit_groups(
        result["bit_sequence"],
        result["bits_per_symbol"]
    )

    compact_bit_sequence = "".join(str(bit) for bit in result["bit_sequence"])

    lines = []
    lines.append("IDEAL L-PPM TRANSMITTER")
    lines.append("=" * 34)
    lines.append(f"PPM order L              : {result['ppm_order']}")
    lines.append(f"Bits/symbol b=log2(L)   : {result['bits_per_symbol']}")
    lines.append(f"Amplitude A             : {result['amplitude']:.3f}")
    lines.append(f"Number of symbols       : {result['number_of_symbols']}")
    lines.append(f"Random seed             : {result['random_seed']}")
    lines.append("")
    lines.append("TIMING PARAMETERS")
    lines.append("-" * 34)
    lines.append(f"Target T                : {result['target_symbol_duration']*1e3:.3f} ms")
    lines.append(f"Target T_slot = T/L     : {result['target_slot_duration']*1e6:.3f} us")
    lines.append(f"Discrete T_slot         : {result['effective_slot_duration']*1e6:.3f} us")
    lines.append(f"Discrete T_symbol       : {result['effective_symbol_duration']*1e3:.3f} ms")
    lines.append(f"Samples per slot        : {result['samples_per_slot']}")
    lines.append(f"Ideal samples per slot  : {result['ideal_samples_per_slot']:.3f}")
    lines.append(f"Slot timing error       : {result['relative_slot_duration_error']:+.2f}%")
    lines.append("")
    lines.append("DATA RATE METRICS")
    lines.append("-" * 34)
    lines.append(f"Symbol rate Rs = 1/T    : {result['symbol_rate']:.2f} sym/s")
    lines.append(f"Bit rate Rb = b/T       : {result['bit_rate']:.2f} bit/s")
    lines.append(f"Duty cycle = 1/L        : {result['duty_cycle']:.3f}")
    lines.append(f"Average level ≈ A/L     : {result['approximate_average_optical_level']:.3f}")
    lines.append(f"Peak-to-average ≈ L     : {result['peak_to_average_ratio']:.1f}")
    lines.append("")
    lines.append("BIT SEQUENCE")
    lines.append("-" * 34)
    lines.append(compact_bit_sequence)
    lines.append("")
    lines.append("SYMBOL TO SLOT MAPPING")
    lines.append("-" * 34)

    for symbol_index, bits in enumerate(bit_groups):
        slot = result["slot_indices_one_based"][symbol_index]
        lines.append(f"S{symbol_index + 1:02d}: bits {bits}  ->  slot {slot}")

    if result["warnings"]:
        lines.append("")
        lines.append("WARNINGS")
        lines.append("-" * 34)
        for warning in result["warnings"]:
            lines.append(f"! {warning}")

    return "\n".join(lines)


# ============================================================
# 4) Initial waveform generation
# ============================================================
initial_ppm_order = VALID_PPM_ORDERS[INITIAL_L_INDEX]

initial_result = generate_lppm_waveform(
    amplitude=INITIAL_AMPLITUDE,
    symbol_duration=INITIAL_SYMBOL_DURATION,
    ppm_order=initial_ppm_order,
    number_of_symbols=INITIAL_NUMBER_OF_SYMBOLS,
    sampling_frequency=SAMPLING_FREQUENCY,
    seed=RANDOM_SEED
)


# ============================================================
# 5) Figure and layout
# ============================================================
fig = plt.figure(figsize=(16.5, 9.0))

grid = fig.add_gridspec(
    1, 2,
    width_ratios=[2.25, 1.15],
    left=0.06,
    right=0.97,
    top=0.90,
    bottom=0.23,
    wspace=0.18
)

ax_waveform = fig.add_subplot(grid[0, 0])
ax_info = fig.add_subplot(grid[0, 1])
ax_info.axis("off")

fig.suptitle(
    "Interactive Li-Fi / VLC L-PPM Transmitter Waveform Simulation",
    fontsize=15,
    fontweight="bold"
)


# ============================================================
# 6) Initial plot
# ============================================================
ppm_line, = ax_waveform.step(
    initial_result["time_step"] * 1e3,
    initial_result["waveform_step"],
    where="post",
    linewidth=2.4,
    color="C0",
    label="Transmitted L-PPM waveform"
)

ax_waveform.set_title(
    "Ideal Transmitted L-PPM Optical Waveform",
    fontsize=12,
    fontweight="bold"
)
ax_waveform.set_xlabel("Time (ms)")
ax_waveform.set_ylabel("Normalized optical intensity / amplitude")
ax_waveform.grid(True, alpha=0.25)
ax_waveform.legend(loc="upper right")

info_text = ax_info.text(
    0.02,
    0.98,
    "",
    transform=ax_info.transAxes,
    va="top",
    ha="left",
    fontsize=8.5,
    family="monospace",
    bbox=dict(
        boxstyle="round,pad=0.6",
        facecolor="white",
        edgecolor="0.75",
        alpha=0.95
    )
)

guide_artists = []


# ============================================================
# 7) Plot guide update functions
# ============================================================
def clear_guides():
    """
    Remove previous symbol boundaries, slot boundaries,
    and active slot highlight regions from the plot.
    """
    global guide_artists

    for artist in guide_artists:
        try:
            artist.remove()
        except ValueError:
            pass

    guide_artists = []


def draw_symbol_and_slot_guides(result):
    """
    Draw symbol boundaries, slot boundaries, and active slot regions.

    Symbol boundaries:
        Black dashed vertical lines.

    Slot boundaries:
        Gray dotted vertical lines.

    Active slots:
        Light shaded background regions.
    """
    global guide_artists

    clear_guides()

    ppm_order = result["ppm_order"]
    number_of_symbols = result["number_of_symbols"]
    effective_symbol_duration = result["effective_symbol_duration"]
    effective_slot_duration = result["effective_slot_duration"]

    # Active slot highlighting
    for start_time, end_time in result["active_slot_intervals"]:
        span = ax_waveform.axvspan(
            start_time * 1e3,
            end_time * 1e3,
            color="C0",
            alpha=0.10,
            zorder=0
        )
        guide_artists.append(span)

    # Symbol boundaries
    for symbol_index in range(number_of_symbols + 1):
        x_ms = symbol_index * effective_symbol_duration * 1e3
        line = ax_waveform.axvline(
            x_ms,
            color="black",
            linestyle="--",
            linewidth=1.1,
            alpha=0.45,
            zorder=1
        )
        guide_artists.append(line)

    # Slot boundaries
    for symbol_index in range(number_of_symbols):
        symbol_start_time = symbol_index * effective_symbol_duration

        for slot_index in range(1, ppm_order):
            x_ms = (symbol_start_time + slot_index * effective_slot_duration) * 1e3
            line = ax_waveform.axvline(
                x_ms,
                color="gray",
                linestyle=":",
                linewidth=0.8,
                alpha=0.30,
                zorder=1
            )
            guide_artists.append(line)


# ============================================================
# 8) Slider and button layout
# ============================================================
slider_face_color = "lightgoldenrodyellow"

ax_amplitude_slider = plt.axes(
    [0.12, 0.155, 0.31, 0.026],
    facecolor=slider_face_color
)

ax_symbol_duration_slider = plt.axes(
    [0.57, 0.155, 0.31, 0.026],
    facecolor=slider_face_color
)

ax_number_symbols_slider = plt.axes(
    [0.12, 0.100, 0.31, 0.026],
    facecolor=slider_face_color
)

ax_ppm_order_slider = plt.axes(
    [0.57, 0.100, 0.31, 0.026],
    facecolor=slider_face_color
)

ax_reset_button = plt.axes(
    [0.44, 0.040, 0.12, 0.040]
)


# ============================================================
# 9) Slider creation
# ============================================================
amplitude_slider = Slider(
    ax=ax_amplitude_slider,
    label="Amplitude A",
    valmin=0.2,
    valmax=2.0,
    valinit=INITIAL_AMPLITUDE,
    valstep=0.01
)

symbol_duration_slider_ms = Slider(
    ax=ax_symbol_duration_slider,
    label="Symbol Duration T (ms)",
    valmin=0.2,
    valmax=3.0,
    valinit=INITIAL_SYMBOL_DURATION * 1e3,
    valstep=0.05
)

number_symbols_slider = Slider(
    ax=ax_number_symbols_slider,
    label="Number of Symbols",
    valmin=2,
    valmax=10,
    valinit=INITIAL_NUMBER_OF_SYMBOLS,
    valstep=1
)

ppm_order_slider = Slider(
    ax=ax_ppm_order_slider,
    label="PPM Order L",
    valmin=0,
    valmax=len(VALID_PPM_ORDERS) - 1,
    valinit=INITIAL_L_INDEX,
    valstep=1
)

# Show the actual L values under the index slider.
ax_ppm_order_slider.set_xticks(np.arange(len(VALID_PPM_ORDERS)))
ax_ppm_order_slider.set_xticklabels([str(value) for value in VALID_PPM_ORDERS])

reset_button = Button(
    ax=ax_reset_button,
    label="Reset"
)


# ============================================================
# 10) Update callback
# ============================================================
def update_plot(_):
    """
    Update the L-PPM waveform, guide lines, active slot highlights,
    and information panel whenever any slider value changes.
    """
    amplitude = amplitude_slider.val
    symbol_duration = symbol_duration_slider_ms.val * 1e-3
    number_of_symbols = int(round(number_symbols_slider.val))

    ppm_order_index = int(round(ppm_order_slider.val))
    ppm_order = int(VALID_PPM_ORDERS[ppm_order_index])

    # Make the slider value text show L directly, not the internal index.
    ppm_order_slider.valtext.set_text(str(ppm_order))

    result = generate_lppm_waveform(
        amplitude=amplitude,
        symbol_duration=symbol_duration,
        ppm_order=ppm_order,
        number_of_symbols=number_of_symbols,
        sampling_frequency=SAMPLING_FREQUENCY,
        seed=RANDOM_SEED
    )

    ppm_line.set_data(
        result["time_step"] * 1e3,
        result["waveform_step"]
    )

    total_duration_ms = result["time_step"][-1] * 1e3
    ax_waveform.set_xlim(0, total_duration_ms)

    y_upper = max(1.15 * amplitude, 1.0)
    ax_waveform.set_ylim(-0.08 * y_upper, y_upper)

    draw_symbol_and_slot_guides(result)
    info_text.set_text(create_information_panel_text(result))

    fig.canvas.draw_idle()


# ============================================================
# 11) Reset callback
# ============================================================
def reset_sliders(_):
    """
    Reset all sliders to their initial values.
    """
    amplitude_slider.reset()
    symbol_duration_slider_ms.reset()
    number_symbols_slider.reset()
    ppm_order_slider.reset()


# ============================================================
# 12) Connect callbacks
# ============================================================
amplitude_slider.on_changed(update_plot)
symbol_duration_slider_ms.on_changed(update_plot)
number_symbols_slider.on_changed(update_plot)
ppm_order_slider.on_changed(update_plot)

reset_button.on_clicked(reset_sliders)


# ============================================================
# 13) First draw
# ============================================================
update_plot(None)

plt.show()