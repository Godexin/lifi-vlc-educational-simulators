"""
vlc_lambertian_order_visualizer.py

Interactive Li-Fi / VLC educational simulator for visualizing the relationship
between the LED half-power semi-angle and the Lambertian order.

Main concepts:
    m = ln(0.5) / ln(cos(Phi_half))

    I(phi) = cos^m(phi)

Purpose:
    - Show how the Lambertian order m changes as the LED half-power
      semi-angle Phi_half changes.
    - Visualize the normalized Lambertian radiation pattern in both
      Cartesian and polar forms.
    - Provide an educational and presentation-ready visualization for
      Li-Fi / Visible Light Communication (VLC) channel studies.

Important note:
    This script models only the normalized angular radiation pattern of an
    ideal Lambertian LED. It does not calculate the full VLC channel DC gain
    H(0), received optical power, receiver FOV effect, photodetector area,
    optical filter gain, optical concentrator gain, or multipath reflections.
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, Button


# ============================================================
# 1) Simulation constants
# ============================================================

PHI_HALF_MIN_DEG = 5.0
PHI_HALF_MAX_DEG = 85.0
PHI_HALF_INITIAL_DEG = 60.0
PHI_HALF_STEP_DEG = 0.1

SAFE_MIN_HALF_ANGLE_DEG = 1.0
SAFE_MAX_HALF_ANGLE_DEG = 89.0

PHI_PATTERN_MAX_DEG = 89.9
NUMBER_OF_SAMPLES = 800

REFERENCE_HALF_ANGLES_DEG = [30.0, 60.0, 75.0]


# ============================================================
# 2) Mathematical functions
# ============================================================

def compute_lambertian_order(phi_half_deg):
    """
    Compute the Lambertian order m from the LED half-power semi-angle.

    Parameters
    ----------
    phi_half_deg : float or np.ndarray
        LED half-power semi-angle in degrees.

    Returns
    -------
    float or np.ndarray
        Lambertian order m.

    Notes
    -----
    The theoretical formula is:

        m = ln(0.5) / ln(cos(Phi_half))

    where Phi_half must be between 0 and 90 degrees.

    The input is clipped to a safe numerical range to avoid:
    - division by a near-zero logarithmic denominator near 0 degrees
    - numerical instability near 90 degrees
    """
    phi_half_array = np.asarray(phi_half_deg, dtype=float)

    phi_half_safe = np.clip(
        phi_half_array,
        SAFE_MIN_HALF_ANGLE_DEG,
        SAFE_MAX_HALF_ANGLE_DEG
    )

    phi_half_rad = np.deg2rad(phi_half_safe)

    lambertian_order = np.log(0.5) / np.log(np.cos(phi_half_rad))

    if np.ndim(phi_half_deg) == 0:
        return float(lambertian_order)

    return lambertian_order


def lambertian_pattern(phi_deg, m):
    """
    Compute the normalized Lambertian radiation pattern.

    Parameters
    ----------
    phi_deg : float or np.ndarray
        Irradiance angle in degrees.

    m : float
        Lambertian order.

    Returns
    -------
    float or np.ndarray
        Normalized radiation intensity I(phi) = cos^m(phi).

    Notes
    -----
    This is a normalized educational model. It does not include the absolute
    radiant intensity scaling factor (m + 1) / (2*pi), transmitted optical
    power, or channel gain terms.

    The function is written to support both scalar and NumPy array inputs.
    """
    phi_array = np.asarray(phi_deg, dtype=float)

    valid_angle_mask = np.abs(phi_array) <= PHI_PATTERN_MAX_DEG

    phi_safe = np.clip(
        phi_array,
        -PHI_PATTERN_MAX_DEG,
        PHI_PATTERN_MAX_DEG
    )

    cosine_term = np.maximum(np.cos(np.deg2rad(phi_safe)), 0.0)

    pattern = np.where(
        valid_angle_mask,
        cosine_term ** m,
        0.0
    )

    if np.ndim(phi_deg) == 0:
        return float(pattern)

    return pattern


# ============================================================
# 3) Precomputed simulation data
# ============================================================

phi_half_range_deg = np.linspace(
    PHI_HALF_MIN_DEG,
    PHI_HALF_MAX_DEG,
    NUMBER_OF_SAMPLES
)

m_range = compute_lambertian_order(phi_half_range_deg)

phi_cartesian_deg = np.linspace(
    0.0,
    PHI_PATTERN_MAX_DEG,
    NUMBER_OF_SAMPLES
)

phi_polar_deg = np.linspace(
    -PHI_PATTERN_MAX_DEG,
    PHI_PATTERN_MAX_DEG,
    NUMBER_OF_SAMPLES
)

theta_polar_rad = np.deg2rad(phi_polar_deg)

m_initial = compute_lambertian_order(PHI_HALF_INITIAL_DEG)
pattern_cartesian_initial = lambertian_pattern(phi_cartesian_deg, m_initial)
pattern_polar_initial = lambertian_pattern(phi_polar_deg, m_initial)


# ============================================================
# 4) Figure and axes
# ============================================================

fig = plt.figure(figsize=(14, 9))
fig.suptitle(
    "Interactive Li-Fi / VLC Lambertian LED Radiation Model",
    fontsize=15,
    fontweight="bold"
)

grid = fig.add_gridspec(
    2,
    2,
    height_ratios=[1.0, 1.15],
    width_ratios=[1.1, 1.0]
)

ax_order = fig.add_subplot(grid[0, :])
ax_cartesian = fig.add_subplot(grid[1, 0])
ax_polar = fig.add_subplot(grid[1, 1], projection="polar")

plt.subplots_adjust(
    left=0.08,
    right=0.95,
    top=0.88,
    bottom=0.22,
    hspace=0.42,
    wspace=0.30
)


# ============================================================
# 5) Plot 1: Lambertian order versus half-power angle
# ============================================================

order_curve, = ax_order.plot(
    phi_half_range_deg,
    m_range,
    linewidth=2.4,
    label=r"$m=\ln(0.5)/\ln(\cos(\Phi_{half}))$"
)

current_order_point, = ax_order.plot(
    [PHI_HALF_INITIAL_DEG],
    [m_initial],
    marker="o",
    markersize=8,
    linestyle="None",
    label="Selected operating point"
)

current_order_vline = ax_order.axvline(
    PHI_HALF_INITIAL_DEG,
    linestyle="--",
    linewidth=1.5,
    alpha=0.8
)

order_value_text = ax_order.text(
    0.02,
    0.82,
    "",
    transform=ax_order.transAxes,
    fontsize=10,
    bbox=dict(boxstyle="round", facecolor="white", edgecolor="gray", alpha=0.95)
)

ax_order.set_title(
    "Lambertian Order as a Function of LED Half-Power Semi-Angle"
)
ax_order.set_xlabel(r"Half-power semi-angle, $\Phi_{half}$ [degrees]")
ax_order.set_ylabel("Lambertian order, m")
ax_order.grid(True, alpha=0.35)
ax_order.legend(loc="upper right")


# ============================================================
# 6) Plot 2: Cartesian normalized radiation pattern
# ============================================================

cartesian_selected_line, = ax_cartesian.plot(
    phi_cartesian_deg,
    pattern_cartesian_initial,
    linewidth=2.6,
    label="Selected radiation pattern"
)

for reference_angle in REFERENCE_HALF_ANGLES_DEG:
    reference_m = compute_lambertian_order(reference_angle)
    reference_pattern = lambertian_pattern(phi_cartesian_deg, reference_m)

    ax_cartesian.plot(
        phi_cartesian_deg,
        reference_pattern,
        linestyle=":",
        linewidth=1.3,
        alpha=0.65,
        label=fr"Reference $\Phi_{{half}}={reference_angle:.0f}^\circ$"
    )

half_power_hline = ax_cartesian.axhline(
    0.5,
    linestyle="--",
    linewidth=1.4,
    alpha=0.85,
    label="Half-power level = 0.5"
)

cartesian_half_angle_vline = ax_cartesian.axvline(
    PHI_HALF_INITIAL_DEG,
    linestyle="--",
    linewidth=1.5,
    alpha=0.85,
    label=r"Selected $\Phi_{half}$"
)

cartesian_half_power_point, = ax_cartesian.plot(
    [PHI_HALF_INITIAL_DEG],
    [0.5],
    marker="o",
    markersize=7,
    linestyle="None",
    label="Half-power point"
)

ax_cartesian.set_title(
    r"Normalized Lambertian Radiation Pattern: $I(\phi)=\cos^m(\phi)$"
)
ax_cartesian.set_xlabel(r"Irradiance angle, $\phi$ [degrees]")
ax_cartesian.set_ylabel("Normalized optical power")
ax_cartesian.set_xlim(0, PHI_PATTERN_MAX_DEG)
ax_cartesian.set_ylim(0, 1.05)
ax_cartesian.grid(True, alpha=0.35)
ax_cartesian.legend(loc="upper right", fontsize=8)


# ============================================================
# 7) Plot 3: Polar normalized radiation pattern
# ============================================================

polar_selected_line, = ax_polar.plot(
    theta_polar_rad,
    pattern_polar_initial,
    linewidth=2.6,
    label="Selected pattern"
)

for reference_angle in REFERENCE_HALF_ANGLES_DEG:
    reference_m = compute_lambertian_order(reference_angle)
    reference_pattern = lambertian_pattern(phi_polar_deg, reference_m)

    ax_polar.plot(
        theta_polar_rad,
        reference_pattern,
        linestyle=":",
        linewidth=1.2,
        alpha=0.55
    )

initial_half_angle_rad = np.deg2rad(PHI_HALF_INITIAL_DEG)

polar_half_angle_positive, = ax_polar.plot(
    [initial_half_angle_rad, initial_half_angle_rad],
    [0.0, 0.5],
    linestyle="--",
    linewidth=1.5,
    alpha=0.85,
    label=r"$+\Phi_{half}$"
)

polar_half_angle_negative, = ax_polar.plot(
    [-initial_half_angle_rad, -initial_half_angle_rad],
    [0.0, 0.5],
    linestyle="--",
    linewidth=1.5,
    alpha=0.85,
    label=r"$-\Phi_{half}$"
)

ax_polar.set_title("Polar Radiation Pattern")
ax_polar.set_theta_zero_location("N")
ax_polar.set_theta_direction(-1)
ax_polar.set_thetamin(-90)
ax_polar.set_thetamax(90)
ax_polar.set_rlim(0, 1.05)
ax_polar.grid(True, alpha=0.35)
ax_polar.legend(loc="lower center", bbox_to_anchor=(0.5, -0.18), fontsize=8)


# ============================================================
# 8) Slider, reset button, and information box
# ============================================================

slider_axis = plt.axes([0.12, 0.12, 0.48, 0.035])
phi_half_slider = Slider(
    ax=slider_axis,
    label=r"$\Phi_{half}$ [degrees]",
    valmin=PHI_HALF_MIN_DEG,
    valmax=PHI_HALF_MAX_DEG,
    valinit=PHI_HALF_INITIAL_DEG,
    valstep=PHI_HALF_STEP_DEG
)

reset_axis = plt.axes([0.65, 0.105, 0.10, 0.055])
reset_button = Button(reset_axis, "Reset")

info_text = fig.text(
    0.78,
    0.075,
    "",
    fontsize=10,
    verticalalignment="center",
    bbox=dict(
        boxstyle="round",
        facecolor="white",
        edgecolor="gray",
        alpha=0.95
    )
)


# ============================================================
# 9) Interactive update functions
# ============================================================

def update_plots(_=None):
    """
    Update all plots when the half-power semi-angle slider changes.
    """
    phi_half = phi_half_slider.val
    m_value = compute_lambertian_order(phi_half)

    updated_cartesian_pattern = lambertian_pattern(phi_cartesian_deg, m_value)
    updated_polar_pattern = lambertian_pattern(phi_polar_deg, m_value)

    # Update plot 1
    current_order_point.set_data([phi_half], [m_value])
    current_order_vline.set_xdata([phi_half, phi_half])

    order_value_text.set_text(
        f"Selected LED parameter\n"
        f"$\\Phi_{{half}}$ = {phi_half:.2f}°\n"
        f"m = {m_value:.4f}"
    )

    # Update plot 2
    cartesian_selected_line.set_ydata(updated_cartesian_pattern)
    cartesian_half_angle_vline.set_xdata([phi_half, phi_half])
    cartesian_half_power_point.set_data([phi_half], [0.5])

    # Update plot 3
    polar_selected_line.set_ydata(updated_polar_pattern)

    half_angle_rad = np.deg2rad(phi_half)

    polar_half_angle_positive.set_data(
        [half_angle_rad, half_angle_rad],
        [0.0, 0.5]
    )

    polar_half_angle_negative.set_data(
        [-half_angle_rad, -half_angle_rad],
        [0.0, 0.5]
    )

    # Update information box
    if phi_half < 35:
        beam_comment = "Narrow beam / focused LED emission"
    elif phi_half < 65:
        beam_comment = "Moderate beam width"
    else:
        beam_comment = "Wide beam / diffuse LED emission"

    info_text.set_text(
        f"Current values\n"
        f"$\\Phi_{{half}}$ = {phi_half:.2f}°\n"
        f"m = {m_value:.4f}\n\n"
        f"Physical interpretation\n"
        f"• Smaller $\\Phi_{{half}}$ → larger m\n"
        f"• Larger m → narrower optical beam\n"
        f"• Larger $\\Phi_{{half}}$ → wider beam\n"
        f"• Current case: {beam_comment}"
    )

    fig.canvas.draw_idle()


def reset_simulation(_=None):
    """
    Reset the slider to the initial half-power semi-angle.
    """
    phi_half_slider.reset()


phi_half_slider.on_changed(update_plots)
reset_button.on_clicked(reset_simulation)

update_plots()

plt.show()