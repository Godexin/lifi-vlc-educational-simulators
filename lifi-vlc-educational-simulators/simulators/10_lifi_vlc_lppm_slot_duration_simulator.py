import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, Button

# ============================================================
# Interactive Li-Fi / VLC L-PPM Slot Duration Visualization
# ============================================================
#
# Model:
#   T_slot = T / L
#
# Purpose:
#   This code visualizes the fundamental timing relationship
#   between symbol duration T, PPM order L, and slot duration T_slot.
#
# Important note:
#   This is NOT a complete PPM transmitter/receiver simulation.
#   It does not model bit mapping, optical pulses, channel effects,
#   noise, photodetection, SNR, or BER.
#
#   It is an educational timing-analysis tool for L-PPM systems.
# ============================================================


# ------------------------------------------------------------
# 1) Simulation constants
# ------------------------------------------------------------
VALID_PPM_ORDERS = np.array([2, 4, 8, 16, 32], dtype=int)

T_MIN_MS = 0.20
T_MAX_MS = 5.00
T_STEP_MS = 0.05
T_INITIAL_MS = 1.00

L_INITIAL_INDEX = 1       # VALID_PPM_ORDERS[1] = 4
NUM_T_SAMPLES = 500

SLIDER_COLOR = "lightgoldenrodyellow"


# ------------------------------------------------------------
# 2) Utility and validation functions
# ------------------------------------------------------------
def is_power_of_two(values):
    """
    Check whether all given integer values are positive powers of two.
    """
    values = np.asarray(values, dtype=int)
    return np.all((values > 0) & ((values & (values - 1)) == 0))


def validate_ppm_orders(ppm_orders):
    """
    Validate that all PPM orders are positive powers of two.
    """
    ppm_orders = np.asarray(ppm_orders, dtype=int)

    if ppm_orders.ndim != 1:
        raise ValueError("PPM order array must be one-dimensional.")

    if not np.all(ppm_orders > 0):
        raise ValueError("All PPM orders must be positive.")

    if not is_power_of_two(ppm_orders):
        raise ValueError("All PPM orders should be powers of two for standard L-PPM.")

    return ppm_orders


def ms_to_s(value_ms):
    """
    Convert milliseconds to seconds.
    """
    return np.asarray(value_ms, dtype=float) * 1e-3


def s_to_us(value_s):
    """
    Convert seconds to microseconds.
    """
    return np.asarray(value_s, dtype=float) * 1e6


def compute_slot_duration(symbol_duration_s, ppm_order):
    """
    Compute the slot duration of an L-PPM symbol.

    Parameters
    ----------
    symbol_duration_s : float or ndarray
        Symbol duration T in seconds.
    ppm_order : int or ndarray
        PPM order L, i.e., number of slots per symbol.

    Returns
    -------
    float or ndarray
        Slot duration T_slot in seconds.
    """
    symbol_duration_s = np.asarray(symbol_duration_s, dtype=float)
    ppm_order = np.asarray(ppm_order, dtype=float)

    if np.any(symbol_duration_s <= 0):
        raise ValueError("Symbol duration T must be positive.")

    if np.any(ppm_order <= 0):
        raise ValueError("PPM order L must be positive.")

    return symbol_duration_s / ppm_order


def compute_slot_duration_us(symbol_duration_ms, ppm_order):
    """
    Compute slot duration directly in microseconds for plotting.
    """
    return s_to_us(compute_slot_duration(ms_to_s(symbol_duration_ms), ppm_order))


def make_edges_from_centers(center_values):
    """
    Create bin edges from center values for pcolormesh.
    """
    center_values = np.asarray(center_values, dtype=float)

    if center_values.size < 2:
        raise ValueError("At least two center values are required.")

    edges = np.empty(center_values.size + 1)
    edges[1:-1] = 0.5 * (center_values[:-1] + center_values[1:])
    edges[0] = center_values[0] - 0.5 * (center_values[1] - center_values[0])
    edges[-1] = center_values[-1] + 0.5 * (center_values[-1] - center_values[-2])

    return edges


# ------------------------------------------------------------
# 3) Validate constants and prepare data
# ------------------------------------------------------------
VALID_PPM_ORDERS = validate_ppm_orders(VALID_PPM_ORDERS)

T_VALUES_MS = np.linspace(T_MIN_MS, T_MAX_MS, NUM_T_SAMPLES)
L_POSITIONS = np.arange(len(VALID_PPM_ORDERS))

T_INITIAL_S = ms_to_s(T_INITIAL_MS)
L_INITIAL = VALID_PPM_ORDERS[L_INITIAL_INDEX]
T_SLOT_INITIAL_US = compute_slot_duration_us(T_INITIAL_MS, L_INITIAL)

# Curves for initial state
slot_vs_L_initial_us = compute_slot_duration_us(T_INITIAL_MS, VALID_PPM_ORDERS)
slot_vs_T_initial_us = compute_slot_duration_us(T_VALUES_MS, L_INITIAL)

# Heatmap grid
T_GRID_MS, L_GRID_INDEX = np.meshgrid(T_VALUES_MS, L_POSITIONS, indexing="ij")
L_GRID_VALUES = VALID_PPM_ORDERS[L_GRID_INDEX]
SLOT_GRID_US = compute_slot_duration_us(T_GRID_MS, L_GRID_VALUES)

# pcolormesh needs bin edges
T_EDGES_MS = make_edges_from_centers(T_VALUES_MS)
L_EDGES = np.arange(len(VALID_PPM_ORDERS) + 1) - 0.5


# ------------------------------------------------------------
# 4) Figure layout
# ------------------------------------------------------------
fig = plt.figure(figsize=(13.5, 10.0))

grid = fig.add_gridspec(
    nrows=3,
    ncols=2,
    left=0.07,
    right=0.96,
    top=0.92,
    bottom=0.20,
    wspace=0.28,
    hspace=0.55,
    width_ratios=[3.2, 1.25]
)

ax_L = fig.add_subplot(grid[0, 0])
ax_T = fig.add_subplot(grid[1, 0])
ax_heatmap = fig.add_subplot(grid[2, 0])
ax_info = fig.add_subplot(grid[:, 1])
ax_info.axis("off")

fig.suptitle(
    "Interactive Slot Duration Analysis for Li-Fi / VLC L-PPM Systems",
    fontsize=15,
    fontweight="bold"
)


# ------------------------------------------------------------
# 5) Plot 1: Slot duration versus discrete PPM order L
# ------------------------------------------------------------
line_L, = ax_L.plot(
    L_POSITIONS,
    slot_vs_L_initial_us,
    marker="o",
    linewidth=2,
    label=r"$T_{slot}=T/L$"
)

point_L, = ax_L.plot(
    [L_INITIAL_INDEX],
    [T_SLOT_INITIAL_US],
    marker="o",
    markersize=9,
    color="red",
    label="Selected point"
)

annotation_L = ax_L.annotate(
    "",
    xy=(L_INITIAL_INDEX, T_SLOT_INITIAL_US),
    xytext=(12, 10),
    textcoords="offset points",
    fontsize=9,
    bbox=dict(boxstyle="round,pad=0.25", facecolor="white", edgecolor="gray"),
    arrowprops=dict(arrowstyle="->", linewidth=0.8)
)

ax_L.set_title(r"Effect of PPM Order $L$ on Slot Duration")
ax_L.set_xlabel("PPM order L / number of slots per symbol")
ax_L.set_ylabel(r"$T_{slot}$ ($\mu$s)")
ax_L.set_xticks(L_POSITIONS)
ax_L.set_xticklabels([str(L) for L in VALID_PPM_ORDERS])
ax_L.grid(True, alpha=0.35)
ax_L.legend(loc="upper right")


# ------------------------------------------------------------
# 6) Plot 2: Slot duration versus symbol duration T
# ------------------------------------------------------------
line_T, = ax_T.plot(
    T_VALUES_MS,
    slot_vs_T_initial_us,
    linewidth=2,
    label=r"$T_{slot}=T/L$"
)

point_T, = ax_T.plot(
    [T_INITIAL_MS],
    [T_SLOT_INITIAL_US],
    marker="o",
    markersize=9,
    color="red",
    label="Selected point"
)

annotation_T = ax_T.annotate(
    "",
    xy=(T_INITIAL_MS, T_SLOT_INITIAL_US),
    xytext=(12, 10),
    textcoords="offset points",
    fontsize=9,
    bbox=dict(boxstyle="round,pad=0.25", facecolor="white", edgecolor="gray"),
    arrowprops=dict(arrowstyle="->", linewidth=0.8)
)

ax_T.set_title(r"Effect of Symbol Duration $T$ on Slot Duration")
ax_T.set_xlabel("Symbol duration T (ms)")
ax_T.set_ylabel(r"$T_{slot}$ ($\mu$s)")
ax_T.grid(True, alpha=0.35)
ax_T.legend(loc="upper left")


# ------------------------------------------------------------
# 7) Plot 3: Heatmap for combined effect of T and L
# ------------------------------------------------------------
heatmap = ax_heatmap.pcolormesh(
    L_EDGES,
    T_EDGES_MS,
    SLOT_GRID_US,
    shading="auto",
    cmap="viridis"
)

point_heatmap, = ax_heatmap.plot(
    [L_INITIAL_INDEX],
    [T_INITIAL_MS],
    marker="o",
    markersize=9,
    color="red"
)

annotation_heatmap = ax_heatmap.annotate(
    "",
    xy=(L_INITIAL_INDEX, T_INITIAL_MS),
    xytext=(12, 10),
    textcoords="offset points",
    fontsize=9,
    bbox=dict(boxstyle="round,pad=0.25", facecolor="white", edgecolor="gray"),
    arrowprops=dict(arrowstyle="->", linewidth=0.8)
)

ax_heatmap.set_title(r"Combined Effect of $T$ and $L$ on $T_{slot}$")
ax_heatmap.set_xlabel("PPM order L / discrete slot count")
ax_heatmap.set_ylabel("Symbol duration T (ms)")
ax_heatmap.set_xticks(L_POSITIONS)
ax_heatmap.set_xticklabels([str(L) for L in VALID_PPM_ORDERS])

colorbar = fig.colorbar(heatmap, ax=ax_heatmap)
colorbar.set_label(r"$T_{slot}$ ($\mu$s)")


# ------------------------------------------------------------
# 8) Information panel
# ------------------------------------------------------------
info_text = ax_info.text(
    0.02,
    0.98,
    "",
    transform=ax_info.transAxes,
    fontsize=10,
    va="top",
    ha="left",
    linespacing=1.35,
    bbox=dict(
        boxstyle="round,pad=0.55",
        facecolor="white",
        edgecolor="gray"
    )
)

model_note = ax_info.text(
    0.02,
    0.22,
    (
        "Model scope\n"
        "------------------------\n"
        "This visualization focuses only on\n"
        "the timing relation of L-PPM.\n\n"
        "Not included:\n"
        "• bit-to-symbol mapping\n"
        "• optical pulse waveform\n"
        "• VLC channel response\n"
        "• receiver noise\n"
        "• photodetector model\n"
        "• BER / SNR analysis"
    ),
    transform=ax_info.transAxes,
    fontsize=9.5,
    va="top",
    ha="left",
    linespacing=1.35,
    bbox=dict(
        boxstyle="round,pad=0.55",
        facecolor="#f7f7f7",
        edgecolor="gray"
    )
)


# ------------------------------------------------------------
# 9) Slider and button axes
# ------------------------------------------------------------
ax_slider_T = fig.add_axes([0.14, 0.115, 0.52, 0.028], facecolor=SLIDER_COLOR)
ax_slider_L = fig.add_axes([0.14, 0.070, 0.52, 0.028], facecolor=SLIDER_COLOR)
ax_button_reset = fig.add_axes([0.72, 0.060, 0.12, 0.055])


slider_T = Slider(
    ax=ax_slider_T,
    label="Symbol duration T (ms)",
    valmin=T_MIN_MS,
    valmax=T_MAX_MS,
    valinit=T_INITIAL_MS,
    valstep=T_STEP_MS
)

slider_L_index = Slider(
    ax=ax_slider_L,
    label="PPM order L",
    valmin=0,
    valmax=len(VALID_PPM_ORDERS) - 1,
    valinit=L_INITIAL_INDEX,
    valstep=1
)

button_reset = Button(ax_button_reset, "Reset")


# ------------------------------------------------------------
# 10) Axis update function
# ------------------------------------------------------------
def update_axis_limits(symbol_duration_ms, ppm_order):
    """
    Update y-axis limits according to the current operating point.
    """
    max_slot_vs_L = compute_slot_duration_us(symbol_duration_ms, VALID_PPM_ORDERS.min())
    ax_L.set_ylim(0, max_slot_vs_L * 1.18)

    max_slot_vs_T = compute_slot_duration_us(T_MAX_MS, ppm_order)
    ax_T.set_ylim(0, max_slot_vs_T * 1.18)


# ------------------------------------------------------------
# 11) Main update callback
# ------------------------------------------------------------
def update(_):
    """
    Update all plots and text panels when sliders are changed.
    """
    symbol_duration_ms = slider_T.val

    selected_index = int(round(slider_L_index.val))
    selected_index = int(np.clip(selected_index, 0, len(VALID_PPM_ORDERS) - 1))

    ppm_order = VALID_PPM_ORDERS[selected_index]
    bits_per_symbol = int(np.log2(ppm_order))

    slot_duration_us = compute_slot_duration_us(symbol_duration_ms, ppm_order)
    slot_duration_ms = slot_duration_us / 1000.0

    # Update slider value text so that the real L value is visible
    slider_L_index.valtext.set_text(f"L = {ppm_order}")

    # Plot 1 update
    new_slot_vs_L_us = compute_slot_duration_us(symbol_duration_ms, VALID_PPM_ORDERS)
    line_L.set_ydata(new_slot_vs_L_us)
    point_L.set_data([selected_index], [slot_duration_us])

    annotation_L.xy = (selected_index, slot_duration_us)
    annotation_L.set_text(
        f"L={ppm_order}\n"
        f"{slot_duration_us:.2f} µs"
    )

    # Plot 2 update
    new_slot_vs_T_us = compute_slot_duration_us(T_VALUES_MS, ppm_order)
    line_T.set_ydata(new_slot_vs_T_us)
    point_T.set_data([symbol_duration_ms], [slot_duration_us])

    annotation_T.xy = (symbol_duration_ms, slot_duration_us)
    annotation_T.set_text(
        f"T={symbol_duration_ms:.2f} ms\n"
        f"{slot_duration_us:.2f} µs"
    )

    # Heatmap selected point update
    point_heatmap.set_data([selected_index], [symbol_duration_ms])

    annotation_heatmap.xy = (selected_index, symbol_duration_ms)
    annotation_heatmap.set_text(
        f"L={ppm_order}\n"
        f"T={symbol_duration_ms:.2f} ms"
    )

    # Axis limits
    update_axis_limits(symbol_duration_ms, ppm_order)

    # Information panel
    info_text.set_text(
        "Current operating point\n"
        "------------------------\n"
        f"Symbol duration, T:\n"
        f"  {symbol_duration_ms:.3f} ms\n\n"
        f"PPM order, L:\n"
        f"  {ppm_order} slots/symbol\n\n"
        f"Bits per symbol:\n"
        f"  log2(L) = {bits_per_symbol} bits\n\n"
        f"Slot duration:\n"
        f"  T_slot = T / L\n"
        f"  T_slot = {slot_duration_us:.3f} µs\n"
        f"  T_slot = {slot_duration_ms:.6f} ms\n\n"
        "Interpretation\n"
        "------------------------\n"
        "• Increasing T makes each slot wider.\n"
        "• Increasing L divides the same symbol\n"
        "  duration into more slots.\n"
        "• Therefore, larger L gives shorter\n"
        "  slot duration."
    )

    fig.canvas.draw_idle()


# ------------------------------------------------------------
# 12) Reset callback
# ------------------------------------------------------------
def reset(_):
    """
    Reset sliders to their initial values.
    """
    slider_T.reset()
    slider_L_index.reset()


slider_T.on_changed(update)
slider_L_index.on_changed(update)
button_reset.on_clicked(reset)

# Initial rendering
update(None)

plt.show()