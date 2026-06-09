import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, Button

# ============================================================
# Interactive Li-Fi / VLC L-PPM Bits-per-Symbol Visualization
# ============================================================
#
# Model:
#     b = log2(L)
#
# where:
#     L : PPM order / number of slots per symbol
#     b : number of bits carried by one PPM symbol
#
# Notes:
# - This code does not generate a complete PPM waveform.
# - It only visualizes the theoretical relationship between
#   PPM order L and bits per symbol b.
# - For binary mapping, L is commonly selected as a power of two.
# ============================================================


# ------------------------------------------------------------
# 1) Configuration parameters
# ------------------------------------------------------------
VALID_L_VALUES = np.array([2, 4, 8, 16, 32], dtype=int)
INITIAL_INDEX = 1  # VALID_L_VALUES[1] = 4

FIGURE_SIZE = (10.5, 6.5)
SLIDER_FACE_COLOR = "lightgoldenrodyellow"

TITLE_FONT_SIZE = 13
LABEL_FONT_SIZE = 11
TICK_FONT_SIZE = 10
INFO_FONT_SIZE = 10
ANNOTATION_FONT_SIZE = 10


# ------------------------------------------------------------
# 2) Validation and calculation functions
# ------------------------------------------------------------
def validate_ppm_orders(L_values):
    """
    Validate PPM order values.

    A valid PPM order L must:
    - be an integer,
    - be greater than or equal to 2,
    - be a power of two.

    Parameters
    ----------
    L_values : int, float, list, tuple, or np.ndarray
        PPM order value or values.

    Returns
    -------
    np.ndarray
        Validated PPM order values as integers.

    Raises
    ------
    ValueError
        If any L value is invalid.
    """
    values = np.asarray(L_values)

    if values.ndim == 0:
        values = values.reshape(1)

    if np.any(values < 2):
        raise ValueError("All PPM order values must be greater than or equal to 2.")

    if not np.all(np.equal(np.mod(values, 1), 0)):
        raise ValueError("All PPM order values must be integers.")

    values = values.astype(int)

    is_power_of_two = (values & (values - 1)) == 0
    if not np.all(is_power_of_two):
        raise ValueError("All PPM order values must be powers of two.")

    return values


def compute_bits_per_symbol(L):
    """
    Compute the number of bits per PPM symbol.

    Formula:
        b = log2(L)

    Parameters
    ----------
    L : int, float, list, tuple, or np.ndarray
        PPM order value or values.

    Returns
    -------
    float or np.ndarray
        Bits per symbol.
    """
    validated_L = validate_ppm_orders(L)
    bits = np.log2(validated_L).astype(float)

    if bits.size == 1:
        return float(bits[0])

    return bits


def validate_initial_index(index, valid_values):
    """
    Validate the initial slider index.

    Parameters
    ----------
    index : int
        Initial index.
    valid_values : np.ndarray
        Valid PPM order values.

    Raises
    ------
    ValueError
        If index is outside the valid range.
    """
    if not 0 <= index < len(valid_values):
        raise ValueError("INITIAL_INDEX is outside the range of VALID_L_VALUES.")


# ------------------------------------------------------------
# 3) Validate configuration and compute initial values
# ------------------------------------------------------------
VALID_L_VALUES = validate_ppm_orders(VALID_L_VALUES)
validate_initial_index(INITIAL_INDEX, VALID_L_VALUES)

INITIAL_L = VALID_L_VALUES[INITIAL_INDEX]
INITIAL_B = compute_bits_per_symbol(INITIAL_L)

B_VALUES = compute_bits_per_symbol(VALID_L_VALUES)


# ------------------------------------------------------------
# 4) Create figure and main axis
# ------------------------------------------------------------
fig, ax = plt.subplots(figsize=FIGURE_SIZE)
plt.subplots_adjust(left=0.11, right=0.92, top=0.88, bottom=0.27)

# Main theoretical curve
line_bits, = ax.plot(
    VALID_L_VALUES,
    B_VALUES,
    linewidth=2.2,
    marker="o",
    markersize=7,
    label=r"Theoretical relation: $b = \log_2(L)$"
)

# Current selected point
current_point, = ax.plot(
    INITIAL_L,
    INITIAL_B,
    marker="o",
    markersize=11,
    color="red",
    linestyle="None",
    label="Selected PPM order"
)

# Annotation for the selected point
current_annotation = ax.annotate(
    "",
    xy=(INITIAL_L, INITIAL_B),
    xytext=(12, 12),
    textcoords="offset points",
    fontsize=ANNOTATION_FONT_SIZE,
    bbox=dict(boxstyle="round,pad=0.3", facecolor="white", edgecolor="gray"),
    arrowprops=dict(arrowstyle="->", linewidth=1.0)
)

# Add value labels for all valid L points
for L_value, b_value in zip(VALID_L_VALUES, B_VALUES):
    ax.annotate(
        f"b = {b_value:.0f}",
        xy=(L_value, b_value),
        xytext=(0, 10),
        textcoords="offset points",
        ha="center",
        fontsize=9
    )

# Axis titles and formatting
ax.set_title(
    "Bits per Symbol in L-PPM for Li-Fi / VLC Systems",
    fontsize=TITLE_FONT_SIZE,
    fontweight="bold"
)
ax.set_xlabel(
    r"PPM order $L$ / number of slots per symbol",
    fontsize=LABEL_FONT_SIZE
)
ax.set_ylabel(
    r"Bits per symbol $b = \log_2(L)$",
    fontsize=LABEL_FONT_SIZE
)

ax.set_xticks(VALID_L_VALUES)
ax.set_yticks(B_VALUES)

ax.tick_params(axis="both", labelsize=TICK_FONT_SIZE)
ax.grid(True, linestyle="--", alpha=0.6)
ax.legend(loc="upper left", fontsize=9)

# Add explanatory note inside the plot
model_note = (
    r"$L = 2^b$  $\Rightarrow$  $b = \log_2(L)$" "\n"
    "Each doubling of L increases b by 1 bit/symbol."
)

ax.text(
    0.03,
    0.78,
    model_note,
    transform=ax.transAxes,
    fontsize=INFO_FONT_SIZE,
    bbox=dict(boxstyle="round,pad=0.4", facecolor="white", edgecolor="gray")
)


# ------------------------------------------------------------
# 5) Information box
# ------------------------------------------------------------
info_text = fig.text(
    0.68,
    0.08,
    "",
    fontsize=INFO_FONT_SIZE,
    va="bottom",
    bbox=dict(
        boxstyle="round,pad=0.5",
        facecolor="white",
        edgecolor="gray"
    )
)


# ------------------------------------------------------------
# 6) Slider and reset button
# ------------------------------------------------------------
slider_axis = plt.axes(
    [0.13, 0.13, 0.48, 0.04],
    facecolor=SLIDER_FACE_COLOR
)

ppm_slider = Slider(
    ax=slider_axis,
    label="PPM order selection",
    valmin=0,
    valmax=len(VALID_L_VALUES) - 1,
    valinit=INITIAL_INDEX,
    valstep=1
)

reset_axis = plt.axes([0.13, 0.055, 0.12, 0.055])
reset_button = Button(reset_axis, "Reset")


# ------------------------------------------------------------
# 7) Update function
# ------------------------------------------------------------
def update(_):
    """
    Update the selected point, annotation, and information box
    when the slider value changes.
    """
    selected_index = int(round(ppm_slider.val))

    selected_L = VALID_L_VALUES[selected_index]
    selected_b = compute_bits_per_symbol(selected_L)

    # Update selected point
    current_point.set_data([selected_L], [selected_b])

    # Update annotation
    current_annotation.xy = (selected_L, selected_b)
    current_annotation.set_text(
        f"L = {selected_L}\n"
        f"b = {selected_b:.0f} bit/symbol"
    )

    # Update information box
    info_text.set_text(
        "Selected PPM parameters\n"
        f"L = {selected_L} slots/symbol\n"
        f"b = log2(L) = {selected_b:.0f} bits/symbol\n\n"
        "Interpretation\n"
        "- Larger L increases bits per symbol.\n"
        "- The increase is logarithmic.\n"
        "- Higher L provides more symbol states.\n"
        "- In practical VLC systems, higher L may require\n"
        "  narrower slots, better timing synchronization,\n"
        "  higher receiver sensitivity, and wider bandwidth."
    )

    fig.canvas.draw_idle()


# ------------------------------------------------------------
# 8) Reset function
# ------------------------------------------------------------
def reset(_):
    """
    Reset the slider to its initial value.
    """
    ppm_slider.reset()


ppm_slider.on_changed(update)
reset_button.on_clicked(reset)

# Show initial state
update(None)

plt.show()