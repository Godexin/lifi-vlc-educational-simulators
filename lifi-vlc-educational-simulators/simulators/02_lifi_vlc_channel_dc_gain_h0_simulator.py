import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, Button

# ============================================================
# Interactive Li-Fi / VLC Channel DC Gain Simulator
# ------------------------------------------------------------
# This script visualizes the relationship between:
#
#   h(t)  : VLC channel impulse response
#   H(0)  : channel DC gain
#
# Continuous-time definition:
#   H(0) = integral h(t) dt
#
# Discrete-time approximation:
#   H(0) ≈ sum h[n] * dt
#
# Important modeling note:
# - If h[n] is interpreted as a sampled continuous-time impulse response,
#   then sum(h) * dt is the integral approximation.
# - If h[n] is interpreted as a dimensionless discrete channel tap model,
#   then sum(h) is usually treated as the discrete DC gain.
#
# This simulator intentionally displays both interpretations.
# ============================================================


# ============================================================
# 1) Configuration
# ============================================================
FS = 1_000_000                  # Sampling frequency [Hz]
DT = 1 / FS                     # Time step [s]
H_LEN = 220                     # Number of samples in impulse response
N_FFT = 4096                    # FFT length for frequency response

T_H = np.arange(H_LEN) * DT     # Time axis [s]
T_US = T_H * 1e6                # Time axis [microseconds]

DEFAULTS = {
    "los_gain": 0.70,
    "los_delay": 25,
    "ref1_gain": 0.18,
    "ref1_delay": 45,
    "ref2_gain": 0.10,
    "ref2_delay": 75,
    "pt": 1.00,                 # Transmitted average optical power [W]
}

PRESETS = {
    "Strong LOS": {
        "los_gain": 1.00,
        "los_delay": 20,
        "ref1_gain": 0.08,
        "ref1_delay": 55,
        "ref2_gain": 0.03,
        "ref2_delay": 90,
        "pt": 1.00,
    },
    "Multipath Rich": {
        "los_gain": 0.45,
        "los_delay": 20,
        "ref1_gain": 0.35,
        "ref1_delay": 70,
        "ref2_gain": 0.25,
        "ref2_delay": 135,
        "pt": 1.00,
    },
}

PATH_COLORS = {
    "LOS": "C0",
    "Reflection 1": "C1",
    "Reflection 2": "C2",
}


# ============================================================
# 2) Helper functions
# ============================================================
def clip_delay(delay_sample, length):
    """Convert a slider delay value to a valid integer sample index."""
    return int(np.clip(round(delay_sample), 0, length - 1))


def build_channel_impulse_response(length, path_parameters):
    """
    Build a simple discrete multipath VLC impulse response.

    The channel consists of:
    - LOS path
    - First reflected path
    - Second reflected path

    Each path is represented as one non-negative discrete impulse/tap.
    """
    h = np.zeros(length)

    paths = {
        "LOS": {
            "gain": max(path_parameters["los_gain"], 0.0),
            "delay": clip_delay(path_parameters["los_delay"], length),
        },
        "Reflection 1": {
            "gain": max(path_parameters["ref1_gain"], 0.0),
            "delay": clip_delay(path_parameters["ref1_delay"], length),
        },
        "Reflection 2": {
            "gain": max(path_parameters["ref2_gain"], 0.0),
            "delay": clip_delay(path_parameters["ref2_delay"], length),
        },
    }

    for path in paths.values():
        h[path["delay"]] += path["gain"]

    return h, paths


def compute_time_domain_metrics(h, t, dt, pt):
    """
    Compute channel DC gain, cumulative integral, mean delay,
    RMS delay spread, and received power estimates.
    """
    h_sum = np.sum(h)

    # Two useful interpretations:
    h0_discrete = h_sum
    h0_continuous_approx = h_sum * dt

    cumulative_integral = np.cumsum(h) * dt

    # Delay metrics are power-weighted using h^2.
    power_weights = h ** 2
    total_power_weight = np.sum(power_weights)

    if total_power_weight > 1e-18:
        mean_delay = np.sum(t * power_weights) / total_power_weight
        rms_delay_spread = np.sqrt(
            np.sum(((t - mean_delay) ** 2) * power_weights) / total_power_weight
        )
    else:
        mean_delay = 0.0
        rms_delay_spread = 0.0

    # For this educational tap model, Pr based on discrete H(0) is more intuitive.
    pr_discrete = h0_discrete * pt
    pr_continuous_approx = h0_continuous_approx * pt

    return {
        "sum_h": h_sum,
        "h0_discrete": h0_discrete,
        "h0_continuous_approx": h0_continuous_approx,
        "cumulative_integral": cumulative_integral,
        "mean_delay": mean_delay,
        "rms_delay_spread": rms_delay_spread,
        "pr_discrete": pr_discrete,
        "pr_continuous_approx": pr_continuous_approx,
    }


def compute_frequency_response(h, dt, n_fft):
    """
    Compute the normalized magnitude frequency response |H(f)|.

    The normalization is performed with respect to the DC value |H(0)|.
    """
    freq = np.fft.rfftfreq(n_fft, d=dt)
    h_f = np.fft.rfft(h, n=n_fft)
    magnitude = np.abs(h_f)

    dc_value = magnitude[0]
    if dc_value > 1e-18:
        magnitude_normalized = magnitude / dc_value
    else:
        magnitude_normalized = np.zeros_like(magnitude)

    return freq, magnitude_normalized


def safe_ylim_positive(axis, data, top_margin=1.20, default_top=1.0):
    """Set stable positive y limits."""
    max_value = np.max(data) if len(data) else 0.0

    if max_value <= 1e-18:
        axis.set_ylim(0, default_top)
    else:
        axis.set_ylim(0, max_value * top_margin)


def get_slider_parameters():
    """Read all current slider values and return them as a dictionary."""
    return {
        "los_gain": s_los_gain.val,
        "los_delay": s_los_delay.val,
        "ref1_gain": s_ref1_gain.val,
        "ref1_delay": s_ref1_delay.val,
        "ref2_gain": s_ref2_gain.val,
        "ref2_delay": s_ref2_delay.val,
        "pt": s_pt.val,
    }


def format_metrics_text(params, paths, metrics):
    """Create compact metric text for the main information panel."""
    los_delay_us = paths["LOS"]["delay"] * DT * 1e6
    ref1_delay_us = paths["Reflection 1"]["delay"] * DT * 1e6
    ref2_delay_us = paths["Reflection 2"]["delay"] * DT * 1e6

    return (
        "Current VLC Channel Metrics\n"
        "---------------------------\n"
        f"LOS  g={paths['LOS']['gain']:.2f}, "
        f"d={paths['LOS']['delay']:3d} samp = {los_delay_us:6.2f} µs\n"
        f"R1   g={paths['Reflection 1']['gain']:.2f}, "
        f"d={paths['Reflection 1']['delay']:3d} samp = {ref1_delay_us:6.2f} µs\n"
        f"R2   g={paths['Reflection 2']['gain']:.2f}, "
        f"d={paths['Reflection 2']['delay']:3d} samp = {ref2_delay_us:6.2f} µs\n"
        "\n"
        f"sum(h)              = {metrics['sum_h']:.4f}\n"
        f"H0 discrete         = {metrics['h0_discrete']:.4f}\n"
        f"H0 continuous       = {metrics['h0_continuous_approx']:.4e}\n"
        "\n"
        f"Pt                  = {params['pt']:.3f} W\n"
        f"Pr discrete         = {metrics['pr_discrete']:.4f} W\n"
        f"Pr continuous       = {metrics['pr_continuous_approx']:.4e} W\n"
        "\n"
        f"Mean delay          = {metrics['mean_delay'] * 1e6:.3f} µs\n"
        f"RMS delay spread    = {metrics['rms_delay_spread'] * 1e6:.3f} µs"
    )


def format_notes_text():
    """Create compact educational note text."""
    return (
        "Educational Notes\n"
        "-----------------\n"
        "• Gain ↑  → H(0) ↑\n"
        "• Pt ↑    → Pr ↑\n"
        "• Delay changes do not\n"
        "  always change H(0).\n"
        "• Larger RMS delay\n"
        "  spread may increase\n"
        "  ISI risk.\n"
        "• Frequency ripples\n"
        "  come from multipath."
    )


def configure_axes():
    """Apply titles, labels, limits, legends, and grids to all axes."""
    ax_h.set_title("VLC Channel Impulse Response h(t)", fontsize=11)
    ax_h.set_xlabel("Time (µs)")
    ax_h.set_ylabel("Path gain")
    ax_h.set_xlim(0, T_US[-1])
    ax_h.grid(True, alpha=0.35)
    ax_h.legend(loc="upper right", fontsize=9)

    ax_cum.set_title("Cumulative Integral Approximation of h(t)", fontsize=11)
    ax_cum.set_xlabel("Time (µs)")
    ax_cum.set_ylabel("Cumulative area")
    ax_cum.set_xlim(0, T_US[-1])
    ax_cum.grid(True, alpha=0.35)

    ax_freq.set_title("Normalized Channel Frequency Response |H(f)| / |H(0)|", fontsize=11)
    ax_freq.set_xlabel("Frequency (MHz)")
    ax_freq.set_ylabel("Normalized magnitude")
    ax_freq.set_xlim(0, FS / 2 / 1e6)
    ax_freq.set_ylim(0, 1.05)
    ax_freq.grid(True, alpha=0.35)


def style_info_axis(axis):
    """Make a clean boxed panel without using oversized text bbox."""
    axis.set_xticks([])
    axis.set_yticks([])
    axis.set_facecolor("white")

    for spine in axis.spines.values():
        spine.set_visible(True)
        spine.set_edgecolor("gray")
        spine.set_linewidth(0.9)


# ============================================================
# 3) Initial channel calculation
# ============================================================
h_initial, paths_initial = build_channel_impulse_response(H_LEN, DEFAULTS)
metrics_initial = compute_time_domain_metrics(h_initial, T_H, DT, DEFAULTS["pt"])
freq_initial, h_norm_initial = compute_frequency_response(h_initial, DT, N_FFT)


# ============================================================
# 4) Figure layout
# ============================================================
plt.rcParams.update({
    "axes.titlesize": 11,
    "axes.labelsize": 10,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
})

fig = plt.figure(figsize=(16, 10.5))
fig.suptitle(
    "Interactive Li-Fi / VLC Channel DC Gain Simulator",
    fontsize=15,
    fontweight="bold",
    y=0.975
)

# Main plots: top region
ax_h = fig.add_axes([0.07, 0.785, 0.88, 0.125])
ax_cum = fig.add_axes([0.07, 0.610, 0.88, 0.125])
ax_freq = fig.add_axes([0.07, 0.435, 0.88, 0.125])

# Control region: bottom left
slider_color = "lightgoldenrodyellow"

slider_x = 0.10
slider_w = 0.33
slider_h = 0.020

ax_los_gain = fig.add_axes([slider_x, 0.345, slider_w, slider_h], facecolor=slider_color)
ax_los_delay = fig.add_axes([slider_x, 0.305, slider_w, slider_h], facecolor=slider_color)

ax_ref1_gain = fig.add_axes([slider_x, 0.260, slider_w, slider_h], facecolor=slider_color)
ax_ref1_delay = fig.add_axes([slider_x, 0.220, slider_w, slider_h], facecolor=slider_color)

ax_ref2_gain = fig.add_axes([slider_x, 0.175, slider_w, slider_h], facecolor=slider_color)
ax_ref2_delay = fig.add_axes([slider_x, 0.135, slider_w, slider_h], facecolor=slider_color)

ax_pt = fig.add_axes([slider_x, 0.090, slider_w, slider_h], facecolor=slider_color)

# Information panels: bottom right
info_ax = fig.add_axes([0.52, 0.145, 0.275, 0.235])
notes_ax = fig.add_axes([0.815, 0.145, 0.135, 0.235])

style_info_axis(info_ax)
style_info_axis(notes_ax)

info_text = info_ax.text(
    0.035,
    0.965,
    "",
    va="top",
    ha="left",
    fontsize=8.1,
    family="monospace",
    linespacing=1.06,
    clip_on=True,
)

notes_text = notes_ax.text(
    0.055,
    0.965,
    format_notes_text(),
    va="top",
    ha="left",
    fontsize=8.4,
    family="monospace",
    linespacing=1.15,
    clip_on=True,
)

# Buttons: separated from info panels
ax_reset = fig.add_axes([0.52, 0.055, 0.10, 0.045])
ax_strong_los = fig.add_axes([0.665, 0.055, 0.13, 0.045])
ax_multipath = fig.add_axes([0.835, 0.055, 0.115, 0.045])
ax_save = fig.add_axes([0.10, 0.035, 0.12, 0.040])


# ============================================================
# 5) Initial plots
# ============================================================
path_line_handles = {}
path_marker_handles = {}

for path_name, path in paths_initial.items():
    x_us = path["delay"] * DT * 1e6
    gain = path["gain"]
    color = PATH_COLORS[path_name]

    line_handle, = ax_h.plot(
        [x_us, x_us],
        [0, gain],
        color=color,
        linewidth=2.4,
        label=path_name,
    )

    marker_handle, = ax_h.plot(
        [x_us],
        [gain],
        marker="o",
        color=color,
        markersize=7.5,
    )

    path_line_handles[path_name] = line_handle
    path_marker_handles[path_name] = marker_handle

ax_h.axhline(0, color="black", linewidth=0.8)

line_cumulative, = ax_cum.plot(
    T_US,
    metrics_initial["cumulative_integral"],
    linewidth=2.0,
    color="C0",
)

line_frequency, = ax_freq.plot(
    freq_initial / 1e6,
    h_norm_initial,
    linewidth=2.0,
    color="C0",
)

configure_axes()
safe_ylim_positive(ax_cum, metrics_initial["cumulative_integral"], top_margin=1.15, default_top=1e-6)


# ============================================================
# 6) Sliders
# ============================================================
s_los_gain = Slider(
    ax_los_gain, "LOS gain", 0.00, 1.50,
    valinit=DEFAULTS["los_gain"], valstep=0.01, valfmt="%.2f"
)
s_los_delay = Slider(
    ax_los_delay, "LOS delay", 0, H_LEN - 1,
    valinit=DEFAULTS["los_delay"], valstep=1, valfmt="%0.0f"
)

s_ref1_gain = Slider(
    ax_ref1_gain, "Ref1 gain", 0.00, 1.00,
    valinit=DEFAULTS["ref1_gain"], valstep=0.01, valfmt="%.2f"
)
s_ref1_delay = Slider(
    ax_ref1_delay, "Ref1 delay", 0, H_LEN - 1,
    valinit=DEFAULTS["ref1_delay"], valstep=1, valfmt="%0.0f"
)

s_ref2_gain = Slider(
    ax_ref2_gain, "Ref2 gain", 0.00, 1.00,
    valinit=DEFAULTS["ref2_gain"], valstep=0.01, valfmt="%.2f"
)
s_ref2_delay = Slider(
    ax_ref2_delay, "Ref2 delay", 0, H_LEN - 1,
    valinit=DEFAULTS["ref2_delay"], valstep=1, valfmt="%0.0f"
)

s_pt = Slider(
    ax_pt, "Pt [W]", 0.00, 5.00,
    valinit=DEFAULTS["pt"], valstep=0.01, valfmt="%.2f"
)

ALL_SLIDERS = [
    s_los_gain,
    s_los_delay,
    s_ref1_gain,
    s_ref1_delay,
    s_ref2_gain,
    s_ref2_delay,
    s_pt,
]

# Slider label/value formatting to prevent overlap
for slider in ALL_SLIDERS:
    slider.label.set_fontsize(9)
    slider.valtext.set_fontsize(9)
    slider.valtext.set_x(1.05)


# ============================================================
# 7) Update function
# ============================================================
def update(_=None):
    """Update channel, metrics, plots, and information text."""
    params = get_slider_parameters()

    h, paths = build_channel_impulse_response(H_LEN, params)
    metrics = compute_time_domain_metrics(h, T_H, DT, params["pt"])
    freq, h_norm = compute_frequency_response(h, DT, N_FFT)

    # Update h(t) path lines
    max_gain = 0.05

    for path_name, path in paths.items():
        x_us = path["delay"] * DT * 1e6
        gain = path["gain"]

        path_line_handles[path_name].set_data([x_us, x_us], [0, gain])
        path_marker_handles[path_name].set_data([x_us], [gain])
        max_gain = max(max_gain, gain)

    ax_h.set_ylim(-0.04 * max_gain, 1.18 * max_gain)

    # Update cumulative integral
    line_cumulative.set_ydata(metrics["cumulative_integral"])
    safe_ylim_positive(
        ax_cum,
        metrics["cumulative_integral"],
        top_margin=1.15,
        default_top=1e-6,
    )

    # Update frequency response
    line_frequency.set_data(freq / 1e6, h_norm)
    ax_freq.set_xlim(0, FS / 2 / 1e6)
    ax_freq.set_ylim(0, 1.05)

    # Update information panel
    info_text.set_text(format_metrics_text(params, paths, metrics))

    fig.canvas.draw_idle()


# ============================================================
# 8) Button actions
# ============================================================
def reset(_):
    """Return all sliders to their initial values."""
    s_los_gain.reset()
    s_los_delay.reset()
    s_ref1_gain.reset()
    s_ref1_delay.reset()
    s_ref2_gain.reset()
    s_ref2_delay.reset()
    s_pt.reset()


def apply_preset(preset_name):
    """Apply one of the predefined VLC channel scenarios."""
    preset = PRESETS[preset_name]

    s_los_gain.set_val(preset["los_gain"])
    s_los_delay.set_val(preset["los_delay"])
    s_ref1_gain.set_val(preset["ref1_gain"])
    s_ref1_delay.set_val(preset["ref1_delay"])
    s_ref2_gain.set_val(preset["ref2_gain"])
    s_ref2_delay.set_val(preset["ref2_delay"])
    s_pt.set_val(preset["pt"])


def apply_strong_los(_):
    apply_preset("Strong LOS")


def apply_multipath_rich(_):
    apply_preset("Multipath Rich")


def save_png(_):
    filename = "vlc_dc_gain_simulation_result.png"
    fig.savefig(filename, dpi=300, bbox_inches="tight")
    button_save.label.set_text("Saved PNG")
    fig.canvas.draw_idle()
    print(f"Figure saved as: {filename}")


# ============================================================
# 9) Buttons
# ============================================================
button_reset = Button(ax_reset, "Reset")
button_strong_los = Button(ax_strong_los, "Strong LOS")
button_multipath = Button(ax_multipath, "Multipath")
button_save = Button(ax_save, "Save PNG")

button_reset.on_clicked(reset)
button_strong_los.on_clicked(apply_strong_los)
button_multipath.on_clicked(apply_multipath_rich)
button_save.on_clicked(save_png)


# ============================================================
# 10) Slider connections
# ============================================================
for slider in ALL_SLIDERS:
    slider.on_changed(update)


# Fill initial information panel
update()

plt.show()