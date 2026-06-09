# 01_interactive_vlc_channel_model.py

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, Button

# ============================================================
# Interactive Li-Fi / VLC Baseband Channel Simulator
# ============================================================
#
# This educational simulation demonstrates the baseband VLC model:
#
#     Y(t) = R · X(t) * h(t) + N(t)
#
# where:
# - X(t): normalized optical power signal emitted by the LED
# - h(t): normalized VLC channel impulse response
# - R   : photodetector responsivity [A/W]
# - N(t): additive receiver noise
# - *   : convolution operation
#
# Educational notes:
# - Increasing LOS gain strengthens the direct optical path.
# - Increasing reflection gain increases multipath effects.
# - Increasing delay spread may increase ISI risk.
# - Increasing responsivity increases the received electrical signal.
# - Increasing noise standard deviation decreases SNR.
#
# This is a normalized educational model, not a full hardware-accurate
# optical link budget simulator.
# ============================================================


# ============================================================
# 1) Simulation settings
# ============================================================
fs = 1_000_000                 # Sampling frequency [Hz]
dt = 1 / fs                    # Sampling period [s]
T_total = 3e-3                 # Total signal duration [s]

t = np.arange(0, T_total, dt)  # Time axis [s]
N = len(t)

h_len = 260                    # Channel impulse response length [samples]
t_h = np.arange(h_len) * dt    # Channel time axis [s]

rng = np.random.default_rng(42)

# Fixed noise pattern:
# The shape of the noise does not change when sliders move.
# Only its amplitude changes with noise_std.
base_noise = rng.normal(0.0, 1.0, size=N)


# ============================================================
# 2) Transmitted optical signal X(t)
# ============================================================
def build_transmitted_signal(time_axis):
    """
    Build a simple normalized optical power signal X(t).

    In VLC, optical power cannot be negative. Therefore, the signal is
    clipped to be non-negative for safety.
    """
    x_signal = np.zeros_like(time_axis)

    # Three rectangular optical pulses.
    # The first two pulses are intentionally relatively close so that
    # delayed reflections can visually demonstrate possible ISI.
    pulses = [
        (0.30e-3, 0.50e-3, 1.0),
        (0.58e-3, 0.78e-3, 0.8),
        (1.55e-3, 1.85e-3, 1.2),
    ]

    for start, end, amplitude in pulses:
        x_signal[(time_axis >= start) & (time_axis < end)] = amplitude

    # Optical power must be non-negative.
    x_signal = np.maximum(x_signal, 0.0)

    return x_signal


x = build_transmitted_signal(t)


# ============================================================
# 3) VLC channel impulse response h(t)
# ============================================================
def clip_delay(delay_sample, length):
    """Convert delay value to a valid integer sample index."""
    return int(np.clip(round(delay_sample), 0, length - 1))


def add_reflection_tail(h, delay_sample, gain, tail_length=12, tail_scale=0.18, tail_tau=4.0):
    """
    Add a short weak exponential tail after a reflection path.

    This gives the reflected path a slightly more realistic spread while
    keeping the model simple and readable.
    """
    for k in range(1, tail_length + 1):
        idx = delay_sample + k
        if idx < len(h):
            h[idx] += gain * tail_scale * np.exp(-k / tail_tau)


def build_channel_impulse_response(
    length,
    los_gain, los_delay,
    ref1_gain, ref1_delay,
    ref2_gain, ref2_delay
):
    """
    Build a simplified VLC channel impulse response.

    The channel contains:
    - One dominant LOS path
    - Two weaker delayed reflection paths
    - Short weak tails after reflections to illustrate multipath spreading
    """
    h = np.zeros(length)

    los_delay = clip_delay(los_delay, length)
    ref1_delay = clip_delay(ref1_delay, length)
    ref2_delay = clip_delay(ref2_delay, length)

    los_gain = max(los_gain, 0.0)
    ref1_gain = max(ref1_gain, 0.0)
    ref2_gain = max(ref2_gain, 0.0)

    # Dominant line-of-sight path
    h[los_delay] += los_gain

    # Weaker reflected paths
    h[ref1_delay] += ref1_gain
    h[ref2_delay] += ref2_gain

    # Short weak tails after reflections
    add_reflection_tail(h, ref1_delay, ref1_gain)
    add_reflection_tail(h, ref2_delay, ref2_gain)

    # VLC channel gain is non-negative in this simplified baseband model.
    h = np.maximum(h, 0.0)

    return h, los_delay, ref1_delay, ref2_delay


# ============================================================
# 4) Channel metrics
# ============================================================
def compute_channel_metrics(h):
    """
    Compute basic VLC channel metrics:
    - DC gain H(0)
    - Mean delay
    - RMS delay spread

    All delay metrics are returned in microseconds.
    """
    weights = np.maximum(h, 0.0)
    total_gain = np.sum(weights)

    if total_gain <= 1e-15:
        return {
            "dc_gain": 0.0,
            "mean_delay_us": 0.0,
            "rms_delay_spread_us": 0.0,
        }

    time_us = t_h * 1e6

    mean_delay_us = np.sum(time_us * weights) / total_gain
    rms_delay_spread_us = np.sqrt(
        np.sum(((time_us - mean_delay_us) ** 2) * weights) / total_gain
    )

    return {
        "dc_gain": total_gain,
        "mean_delay_us": mean_delay_us,
        "rms_delay_spread_us": rms_delay_spread_us,
    }


def compute_snr_db(signal, noise):
    """
    Compute SNR in dB using average powers.

    SNR = 10 log10(signal_power / noise_power)
    """
    signal_power = np.mean(signal ** 2)
    noise_power = np.mean(noise ** 2)

    if noise_power <= 1e-20:
        return np.inf, signal_power, noise_power

    if signal_power <= 1e-20:
        return -np.inf, signal_power, noise_power

    snr_db = 10 * np.log10(signal_power / noise_power)

    return snr_db, signal_power, noise_power


def format_snr(snr_db):
    """Format SNR value safely for the information box."""
    if np.isposinf(snr_db):
        return "∞ dB"
    if np.isneginf(snr_db):
        return "-∞ dB"
    return f"{snr_db:.2f} dB"


# ============================================================
# 5) Main simulation
# ============================================================
def run_simulation(
    responsivity,
    noise_std,
    los_gain, los_delay,
    ref1_gain, ref1_delay,
    ref2_gain, ref2_delay
):
    """
    Run the baseband VLC simulation.

    A causal full convolution is used first. Then the first N samples are
    taken so that all plotted signals share the same time axis as X(t).
    """
    h, los_d, ref1_d, ref2_d = build_channel_impulse_response(
        h_len,
        los_gain, los_delay,
        ref1_gain, ref1_delay,
        ref2_gain, ref2_delay
    )

    # Causal channel convolution: X(t) * h(t)
    x_conv_h_full = np.convolve(x, h, mode="full")
    x_conv_h = x_conv_h_full[:N]

    # Noiseless received electrical signal
    y_noiseless = responsivity * x_conv_h

    # Fixed-pattern AWGN scaled by noise_std
    noise = noise_std * base_noise

    # Final received signal
    y_noisy = y_noiseless + noise

    channel_metrics = compute_channel_metrics(h)
    snr_db, signal_power, noise_power = compute_snr_db(y_noiseless, noise)

    results = {
        "h": h,
        "los_delay_sample": los_d,
        "ref1_delay_sample": ref1_d,
        "ref2_delay_sample": ref2_d,
        "y_noiseless": y_noiseless,
        "y_noisy": y_noisy,
        "noise": noise,
        "snr_db": snr_db,
        "signal_power": signal_power,
        "noise_power": noise_power,
        "channel_metrics": channel_metrics,
    }

    return results


# ============================================================
# 6) Initial parameters
# ============================================================
R0 = 0.40
noise_std0 = 0.02

los_gain0 = 0.70
los_delay0 = 25

ref1_gain0 = 0.18
ref1_delay0 = 55

ref2_gain0 = 0.10
ref2_delay0 = 95

initial_results = run_simulation(
    R0, noise_std0,
    los_gain0, los_delay0,
    ref1_gain0, ref1_delay0,
    ref2_gain0, ref2_delay0
)


# ============================================================
# 7) Plot helper functions
# ============================================================
def set_stable_ylim(axis, data, min_span=0.10):
    """
    Set stable y-axis limits with margin to reduce excessive jumping.
    """
    data = np.asarray(data)
    finite_data = data[np.isfinite(data)]

    if finite_data.size == 0:
        axis.set_ylim(-1.0, 1.0)
        return

    y_min = np.min(finite_data)
    y_max = np.max(finite_data)

    if abs(y_max - y_min) < min_span:
        center = 0.5 * (y_max + y_min)
        axis.set_ylim(center - min_span / 2, center + min_span / 2)
        return

    margin = 0.10 * (y_max - y_min)
    axis.set_ylim(y_min - margin, y_max + margin)


def configure_common_axis(axis):
    """Apply common grid style."""
    axis.grid(True, linestyle="--", alpha=0.45)


def update_impulse_response_plot(h, los_d, ref1_d, ref2_d):
    """
    Update h(t) plot.

    For clarity and compatibility with Matplotlib stem plots, this axis is
    redrawn in a controlled way during each update.
    """
    axes[1].cla()

    axes[1].stem(
        t_h * 1e6,
        h,
        basefmt=" ",
        linefmt="C1-",
        markerfmt="C1o"
    )

    axes[1].plot([], [], "C1o-", label="Total CIR h(t)")

    if h[los_d] > 0:
        axes[1].axvline(los_d * dt * 1e6, color="C0", linestyle="--", alpha=0.7, label="LOS delay")
    if h[ref1_d] > 0:
        axes[1].axvline(ref1_d * dt * 1e6, color="C2", linestyle="--", alpha=0.7, label="Ref1 delay")
    if h[ref2_d] > 0:
        axes[1].axvline(ref2_d * dt * 1e6, color="C3", linestyle="--", alpha=0.7, label="Ref2 delay")

    axes[1].set_title("VLC Channel Impulse Response h(t)")
    axes[1].set_xlabel("Time (µs)")
    axes[1].set_ylabel("Normalized Channel Gain")
    axes[1].set_xlim(0, h_len * dt * 1e6)

    h_max = np.max(h)
    if h_max <= 1e-12:
        axes[1].set_ylim(0, 1.0)
    else:
        axes[1].set_ylim(0, 1.25 * h_max)

    configure_common_axis(axes[1])
    axes[1].legend(loc="upper right", fontsize=8)


def delay_text(delay_sample):
    """Return delay as sample and microsecond text."""
    delay_us = delay_sample * dt * 1e6
    return f"{delay_sample:d} sample = {delay_us:.1f} µs"


# ============================================================
# 8) Figure and plots
# ============================================================
fig, axes = plt.subplots(4, 1, figsize=(14, 11.5))

plt.subplots_adjust(
    left=0.08,
    right=0.67,
    top=0.95,
    bottom=0.35,
    hspace=0.70
)

fig.suptitle(
    "Interactive Li-Fi / VLC Baseband Channel Simulation",
    fontsize=14,
    fontweight="bold"
)

# Plot 1: X(t)
line_x, = axes[0].plot(
    t * 1e3,
    x,
    lw=2.2,
    label="Transmitted optical power X(t)"
)
axes[0].set_title("Transmitted Optical Power Signal X(t)")
axes[0].set_xlabel("Time (ms)")
axes[0].set_ylabel("Normalized Optical Power")
set_stable_ylim(axes[0], x)
configure_common_axis(axes[0])
axes[0].legend(loc="upper right", fontsize=8)

# Plot 2: h(t)
update_impulse_response_plot(
    initial_results["h"],
    initial_results["los_delay_sample"],
    initial_results["ref1_delay_sample"],
    initial_results["ref2_delay_sample"]
)

# Plot 3: noiseless received signal
line_y_noiseless, = axes[2].plot(
    t * 1e3,
    initial_results["y_noiseless"],
    lw=2.0,
    color="C2",
    label="Noiseless received signal"
)
axes[2].set_title("Noiseless Received Signal R·X(t)*h(t)")
axes[2].set_xlabel("Time (ms)")
axes[2].set_ylabel("Normalized Electrical Signal")
set_stable_ylim(axes[2], initial_results["y_noiseless"])
configure_common_axis(axes[2])
axes[2].legend(loc="upper right", fontsize=8)

# Plot 4: noisy received signal
line_y_noisy, = axes[3].plot(
    t * 1e3,
    initial_results["y_noisy"],
    lw=1.4,
    color="C3",
    label="Noisy received signal Y(t)"
)
axes[3].set_title("Noisy Received Signal Y(t) = R·X(t)*h(t) + N(t)")
axes[3].set_xlabel("Time (ms)")
axes[3].set_ylabel("Normalized Electrical Signal")
set_stable_ylim(axes[3], initial_results["y_noisy"])
configure_common_axis(axes[3])
axes[3].legend(loc="upper right", fontsize=8)


# ============================================================
# 9) Information box
# ============================================================
info_text = fig.text(
    0.70,
    0.50,
    "",
    fontsize=9.5,
    family="monospace",
    va="center",
    bbox=dict(
        boxstyle="round,pad=0.55",
        facecolor="white",
        edgecolor="gray",
        alpha=0.95
    )
)


# ============================================================
# 10) Sliders and buttons
# ============================================================
slider_color = "lightgoldenrodyellow"

# Left slider column
ax_R = plt.axes([0.08, 0.285, 0.34, 0.020], facecolor=slider_color)
ax_noise = plt.axes([0.08, 0.245, 0.34, 0.020], facecolor=slider_color)
ax_los_gain = plt.axes([0.08, 0.205, 0.34, 0.020], facecolor=slider_color)
ax_los_delay = plt.axes([0.08, 0.165, 0.34, 0.020], facecolor=slider_color)

# Right slider column
ax_r1_gain = plt.axes([0.54, 0.285, 0.34, 0.020], facecolor=slider_color)
ax_r1_delay = plt.axes([0.54, 0.245, 0.34, 0.020], facecolor=slider_color)
ax_r2_gain = plt.axes([0.54, 0.205, 0.34, 0.020], facecolor=slider_color)
ax_r2_delay = plt.axes([0.54, 0.165, 0.34, 0.020], facecolor=slider_color)

s_R = Slider(ax_R, "R [A/W]", 0.05, 1.00, valinit=R0, valstep=0.01)
s_noise = Slider(ax_noise, "Noise σ", 0.00, 0.15, valinit=noise_std0, valstep=0.001)

s_los_gain = Slider(ax_los_gain, "LOS gain", 0.00, 1.50, valinit=los_gain0, valstep=0.01)
s_los_delay = Slider(ax_los_delay, "LOS delay", 0, h_len - 1, valinit=los_delay0, valstep=1)

s_r1_gain = Slider(ax_r1_gain, "Ref1 gain", 0.00, 1.00, valinit=ref1_gain0, valstep=0.01)
s_r1_delay = Slider(ax_r1_delay, "Ref1 delay", 0, h_len - 1, valinit=ref1_delay0, valstep=1)

s_r2_gain = Slider(ax_r2_gain, "Ref2 gain", 0.00, 1.00, valinit=ref2_gain0, valstep=0.01)
s_r2_delay = Slider(ax_r2_delay, "Ref2 delay", 0, h_len - 1, valinit=ref2_delay0, valstep=1)

reset_ax = plt.axes([0.36, 0.070, 0.11, 0.045])
button_reset = Button(reset_ax, "Reset")

save_ax = plt.axes([0.51, 0.070, 0.13, 0.045])
button_save = Button(save_ax, "Save PNG")


# ============================================================
# 11) Plot update function
# ============================================================
def update_plots(_=None):
    """Update simulation, plots, and metrics when a slider changes."""
    R = s_R.val
    noise_std = s_noise.val

    los_gain = s_los_gain.val
    los_delay = s_los_delay.val

    ref1_gain = s_r1_gain.val
    ref1_delay = s_r1_delay.val

    ref2_gain = s_r2_gain.val
    ref2_delay = s_r2_delay.val

    results = run_simulation(
        R,
        noise_std,
        los_gain,
        los_delay,
        ref1_gain,
        ref1_delay,
        ref2_gain,
        ref2_delay
    )

    h = results["h"]
    los_d = results["los_delay_sample"]
    ref1_d = results["ref1_delay_sample"]
    ref2_d = results["ref2_delay_sample"]

    y_noiseless = results["y_noiseless"]
    y_noisy = results["y_noisy"]

    metrics = results["channel_metrics"]

    update_impulse_response_plot(h, los_d, ref1_d, ref2_d)

    line_y_noiseless.set_ydata(y_noiseless)
    line_y_noisy.set_ydata(y_noisy)

    set_stable_ylim(axes[2], y_noiseless)
    set_stable_ylim(axes[3], y_noisy)

    max_noiseless = np.max(y_noiseless) if y_noiseless.size else 0.0
    avg_noiseless_power = np.mean(y_noiseless ** 2) if y_noiseless.size else 0.0

    info_text.set_text(
        "Current VLC Channel Parameters\n"
        "------------------------------\n"
        f"R                     : {R:.2f} A/W\n"
        f"Noise std σ           : {noise_std:.3f}\n"
        f"SNR                   : {format_snr(results['snr_db'])}\n"
        "\n"
        f"LOS gain              : {los_gain:.2f}\n"
        f"LOS delay             : {delay_text(los_d)}\n"
        f"Ref1 gain             : {ref1_gain:.2f}\n"
        f"Ref1 delay            : {delay_text(ref1_d)}\n"
        f"Ref2 gain             : {ref2_gain:.2f}\n"
        f"Ref2 delay            : {delay_text(ref2_d)}\n"
        "\n"
        f"DC gain H(0)          : {metrics['dc_gain']:.4f}\n"
        f"Mean delay            : {metrics['mean_delay_us']:.2f} µs\n"
        f"RMS delay spread      : {metrics['rms_delay_spread_us']:.2f} µs\n"
        f"Max noiseless signal  : {max_noiseless:.4f}\n"
        f"Avg noiseless power   : {avg_noiseless_power:.6f}"
    )

    fig.canvas.draw_idle()


# ============================================================
# 12) Button functions
# ============================================================
def reset(_):
    """Reset all sliders to their initial values."""
    s_R.reset()
    s_noise.reset()
    s_los_gain.reset()
    s_los_delay.reset()
    s_r1_gain.reset()
    s_r1_delay.reset()
    s_r2_gain.reset()
    s_r2_delay.reset()


def save_png(_):
    """Save the current figure as a PNG file for report or presentation use."""
    filename = "vlc_channel_simulation_result.png"
    fig.savefig(filename, dpi=300, bbox_inches="tight")
    button_save.label.set_text("Saved PNG")
    fig.canvas.draw_idle()
    print(f"Figure saved as: {filename}")


# ============================================================
# 13) Connect sliders and buttons
# ============================================================
s_R.on_changed(update_plots)
s_noise.on_changed(update_plots)

s_los_gain.on_changed(update_plots)
s_los_delay.on_changed(update_plots)

s_r1_gain.on_changed(update_plots)
s_r1_delay.on_changed(update_plots)

s_r2_gain.on_changed(update_plots)
s_r2_delay.on_changed(update_plots)

button_reset.on_clicked(reset)
button_save.on_clicked(save_png)


# Initial update
update_plots(None)

plt.show()