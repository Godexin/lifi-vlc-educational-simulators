"""
Interactive Li-Fi / VLC SNR Performance Analyzer
================================================

This script visualizes the effect of main Li-Fi / VLC link parameters
on the signal-to-noise ratio (SNR).

Simplified SNR model:

    SNR = (R^2 * H(0)^2 * P_t^2) / sigma_n^2

where:

    R         : Photodetector responsivity [A/W]
    H(0)      : Channel DC gain [dimensionless]
    P_t       : Transmitted optical power [normalized optical power]
    sigma_n^2 : Receiver noise variance
    SNR       : Signal-to-noise ratio

Important model note:
---------------------
This is a simplified parametric SNR visualization model.

It does not calculate the full Lambertian VLC channel gain from geometry.
In a complete physical VLC channel model, H(0) depends on distance,
LED semi-angle, Lambertian order, receiver area, irradiance angle,
incidence angle, optical filter gain, concentrator gain, and receiver FOV.

Here, H(0) is treated as an adjustable channel DC gain parameter.
The purpose is educational visualization of SNR sensitivity.
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, Button


# ============================================================
# 1) Global constants and initial values
# ============================================================

EPS = 1e-12
DB_FLOOR = -80.0

R_INIT = 0.40
H0_INIT = 0.20
PT_INIT = 1.00
SIGMA_N2_INIT = 0.02

H0_RANGE = np.linspace(0.0, 1.0, 600)
PT_RANGE = np.linspace(0.0, 5.0, 600)
SIGMA_N2_RANGE = np.linspace(0.001, 0.20, 600)

H0_GRID, PT_GRID = np.meshgrid(H0_RANGE, PT_RANGE)

display_mode = {"value": "linear"}


# ============================================================
# 2) SNR calculation functions
# ============================================================

def compute_snr_linear(R, H0, Pt, sigma_n2):
    """
    Compute SNR in linear scale.
    """
    R_safe = np.maximum(R, 0.0)
    H0_safe = np.maximum(H0, 0.0)
    Pt_safe = np.maximum(Pt, 0.0)
    sigma_safe = np.maximum(sigma_n2, EPS)

    return (R_safe**2 * H0_safe**2 * Pt_safe**2) / sigma_safe


def compute_snr_db(snr_linear):
    """
    Convert linear SNR to dB scale.
    """
    snr_safe = np.maximum(snr_linear, EPS)
    return 10.0 * np.log10(snr_safe)


def compute_snr_db_for_plot(snr_linear):
    """
    Convert SNR to dB and clip extremely low values for clean plotting.
    """
    return np.maximum(compute_snr_db(snr_linear), DB_FLOOR)


def get_displayed_snr(snr_linear):
    """
    Return SNR according to selected display mode.
    """
    if display_mode["value"] == "db":
        return compute_snr_db_for_plot(snr_linear)

    return snr_linear


def get_y_label():
    """
    Return y-axis label according to selected display mode.
    """
    if display_mode["value"] == "db":
        return "SNR (dB)"

    return "SNR (linear)"


def format_snr_quality_comment(snr_db):
    """
    Return qualitative communication-link comment based on SNR in dB.
    """
    if snr_db < 0:
        return "Very poor link"
    elif snr_db < 10:
        return "Weak / moderate link"
    elif snr_db < 20:
        return "Good link"
    else:
        return "Strong link"


# ============================================================
# 3) Initial calculations
# ============================================================

snr_init = compute_snr_linear(
    R_INIT,
    H0_INIT,
    PT_INIT,
    SIGMA_N2_INIT
)

snr_vs_H0_init = compute_snr_linear(
    R_INIT,
    H0_RANGE,
    PT_INIT,
    SIGMA_N2_INIT
)

snr_vs_Pt_init = compute_snr_linear(
    R_INIT,
    H0_INIT,
    PT_RANGE,
    SIGMA_N2_INIT
)

snr_vs_sigma_init = compute_snr_linear(
    R_INIT,
    H0_INIT,
    PT_INIT,
    SIGMA_N2_RANGE
)

snr_grid_init = compute_snr_linear(
    R_INIT,
    H0_GRID,
    PT_GRID,
    SIGMA_N2_INIT
)

snr_grid_init_db = compute_snr_db_for_plot(snr_grid_init)


# ============================================================
# 4) Figure layout
# ============================================================

fig = plt.figure(figsize=(16, 9))

try:
    fig.canvas.manager.set_window_title(
        "Interactive Li-Fi / VLC SNR Performance Analyzer"
    )
except Exception:
    pass

fig.suptitle(
    "Interactive Li-Fi / VLC SNR Performance Analyzer",
    fontsize=17,
    fontweight="bold",
    y=0.965
)

# Main plot area: 2 x 2 layout on the left
ax_H0 = fig.add_axes([0.060, 0.565, 0.300, 0.320])
ax_Pt = fig.add_axes([0.405, 0.565, 0.300, 0.320])
ax_sigma = fig.add_axes([0.060, 0.115, 0.300, 0.320])
ax_heatmap = fig.add_axes([0.405, 0.115, 0.300, 0.320])

# Dedicated colorbar axis
cax_heatmap = fig.add_axes([0.715, 0.115, 0.012, 0.320])

# Right-side information and control panels
ax_info = fig.add_axes([0.755, 0.515, 0.215, 0.370])
ax_info.axis("off")


# ============================================================
# 5) Plot 1: SNR vs H(0)
# ============================================================

line_H0, = ax_H0.plot(
    H0_RANGE,
    get_displayed_snr(snr_vs_H0_init),
    linewidth=2.2,
    color="C0",
    label="SNR curve"
)

point_H0, = ax_H0.plot(
    H0_INIT,
    get_displayed_snr(snr_init),
    "ro",
    markersize=7,
    label="Operating point"
)

ax_H0.set_title(
    r"SNR vs Channel DC Gain $H(0)$",
    fontsize=11,
    pad=8
)
ax_H0.set_xlabel(
    r"$H(0)$ [dimensionless]",
    fontsize=10
)
ax_H0.set_ylabel(
    get_y_label(),
    fontsize=10
)
ax_H0.set_xlim(H0_RANGE.min(), H0_RANGE.max())
ax_H0.grid(True, alpha=0.35)
ax_H0.legend(loc="upper left", fontsize=8.5)


# ============================================================
# 6) Plot 2: SNR vs P_t
# ============================================================

line_Pt, = ax_Pt.plot(
    PT_RANGE,
    get_displayed_snr(snr_vs_Pt_init),
    linewidth=2.2,
    color="C2",
    label="SNR curve"
)

point_Pt, = ax_Pt.plot(
    PT_INIT,
    get_displayed_snr(snr_init),
    "ro",
    markersize=7,
    label="Operating point"
)

ax_Pt.set_title(
    r"SNR vs Transmitted Optical Power $P_t$",
    fontsize=11,
    pad=8
)
ax_Pt.set_xlabel(
    r"$P_t$ [normalized optical power]",
    fontsize=10
)
ax_Pt.set_ylabel(
    get_y_label(),
    fontsize=10
)
ax_Pt.set_xlim(PT_RANGE.min(), PT_RANGE.max())
ax_Pt.grid(True, alpha=0.35)
ax_Pt.legend(loc="upper left", fontsize=8.5)


# ============================================================
# 7) Plot 3: SNR vs noise variance
# ============================================================

line_sigma, = ax_sigma.plot(
    SIGMA_N2_RANGE,
    get_displayed_snr(snr_vs_sigma_init),
    linewidth=2.2,
    color="C3",
    label="SNR curve"
)

point_sigma, = ax_sigma.plot(
    SIGMA_N2_INIT,
    get_displayed_snr(snr_init),
    "ro",
    markersize=7,
    label="Operating point"
)

ax_sigma.set_title(
    r"SNR vs Receiver Noise Variance $\sigma_n^2$",
    fontsize=11,
    pad=8
)
ax_sigma.set_xlabel(
    r"$\sigma_n^2$ [noise variance]",
    fontsize=10
)
ax_sigma.set_ylabel(
    get_y_label(),
    fontsize=10
)
ax_sigma.set_xlim(SIGMA_N2_RANGE.min(), SIGMA_N2_RANGE.max())
ax_sigma.grid(True, alpha=0.35)
ax_sigma.legend(loc="upper right", fontsize=8.5)


# ============================================================
# 8) Plot 4: H(0)-P_t SNR heatmap
# ============================================================

heatmap = ax_heatmap.imshow(
    snr_grid_init_db,
    extent=[
        H0_RANGE.min(),
        H0_RANGE.max(),
        PT_RANGE.min(),
        PT_RANGE.max()
    ],
    origin="lower",
    aspect="auto",
    cmap="viridis",
    vmin=DB_FLOOR,
    vmax=np.nanmax(snr_grid_init_db)
)

point_heatmap, = ax_heatmap.plot(
    H0_INIT,
    PT_INIT,
    "ro",
    markersize=7,
    label="Operating point"
)

ax_heatmap.set_title(
    r"SNR Heatmap: $H(0)$ and $P_t$",
    fontsize=11,
    pad=8
)
ax_heatmap.set_xlabel(
    r"$H(0)$ [dimensionless]",
    fontsize=10
)
ax_heatmap.set_ylabel(
    r"$P_t$ [normalized]",
    fontsize=10
)
ax_heatmap.legend(loc="upper left", fontsize=8.5)

cbar = fig.colorbar(
    heatmap,
    cax=cax_heatmap
)
cbar.set_label("SNR (dB)", fontsize=10)
cbar.ax.tick_params(labelsize=8.5)


# ============================================================
# 9) Threshold lines for dB mode
# ============================================================

threshold_lines = []

for ax in [ax_H0, ax_Pt, ax_sigma]:
    threshold_lines.append(
        ax.axhline(
            0,
            color="gray",
            linestyle="--",
            linewidth=0.9,
            alpha=0.0
        )
    )
    threshold_lines.append(
        ax.axhline(
            10,
            color="gray",
            linestyle="--",
            linewidth=0.9,
            alpha=0.0
        )
    )
    threshold_lines.append(
        ax.axhline(
            20,
            color="gray",
            linestyle="--",
            linewidth=0.9,
            alpha=0.0
        )
    )


def update_threshold_visibility():
    """
    Show SNR threshold lines only in dB mode.
    """
    alpha_value = 0.45 if display_mode["value"] == "db" else 0.0

    for line in threshold_lines:
        line.set_alpha(alpha_value)


# ============================================================
# 10) Information panel
# ============================================================

info_text = ax_info.text(
    0.03,
    0.98,
    "",
    transform=ax_info.transAxes,
    va="top",
    ha="left",
    fontsize=8.8,
    bbox=dict(
        boxstyle="round,pad=0.55",
        facecolor="white",
        edgecolor="gray",
        alpha=0.96
    )
)


# ============================================================
# 11) Controls: sliders and buttons
# ============================================================

fig.text(
    0.755,
    0.455,
    "Controls",
    fontsize=11,
    fontweight="bold"
)

slider_left = 0.800
slider_width = 0.135
slider_height = 0.025

slider_color = "lightgoldenrodyellow"

ax_slider_R = fig.add_axes(
    [slider_left, 0.410, slider_width, slider_height],
    facecolor=slider_color
)

ax_slider_H0 = fig.add_axes(
    [slider_left, 0.365, slider_width, slider_height],
    facecolor=slider_color
)

ax_slider_Pt = fig.add_axes(
    [slider_left, 0.320, slider_width, slider_height],
    facecolor=slider_color
)

ax_slider_sigma = fig.add_axes(
    [slider_left, 0.275, slider_width, slider_height],
    facecolor=slider_color
)

s_R = Slider(
    ax=ax_slider_R,
    label=r"$R$",
    valmin=0.01,
    valmax=2.00,
    valinit=R_INIT,
    valstep=0.01,
    valfmt="%.2f"
)

s_H0 = Slider(
    ax=ax_slider_H0,
    label=r"$H(0)$",
    valmin=0.0,
    valmax=1.0,
    valinit=H0_INIT,
    valstep=0.001,
    valfmt="%.3f"
)

s_Pt = Slider(
    ax=ax_slider_Pt,
    label=r"$P_t$",
    valmin=0.0,
    valmax=5.0,
    valinit=PT_INIT,
    valstep=0.01,
    valfmt="%.2f"
)

s_sigma = Slider(
    ax=ax_slider_sigma,
    label=r"$\sigma_n^2$",
    valmin=0.001,
    valmax=0.20,
    valinit=SIGMA_N2_INIT,
    valstep=0.001,
    valfmt="%.3f"
)

fig.text(
    0.755,
    0.238,
    r"Units: $R$ [A/W], $H(0)$ [-], $P_t$ [normalized]",
    fontsize=8.5
)

ax_button_mode = fig.add_axes([0.765, 0.165, 0.170, 0.050])
button_mode = Button(ax_button_mode, "Linear / dB")

ax_button_reset = fig.add_axes([0.765, 0.095, 0.170, 0.050])
button_reset = Button(ax_button_reset, "Reset")


# ============================================================
# 12) Axis limit update
# ============================================================

def update_axis_limits(R, H0, Pt, sigma_n2):
    """
    Update y-axis limits of the first three plots.
    """
    snr_H0 = compute_snr_linear(
        R,
        H0_RANGE,
        Pt,
        sigma_n2
    )

    snr_Pt = compute_snr_linear(
        R,
        H0,
        PT_RANGE,
        sigma_n2
    )

    snr_sigma = compute_snr_linear(
        R,
        H0,
        Pt,
        SIGMA_N2_RANGE
    )

    axes = [ax_H0, ax_Pt, ax_sigma]
    data = [
        get_displayed_snr(snr_H0),
        get_displayed_snr(snr_Pt),
        get_displayed_snr(snr_sigma)
    ]

    for ax, y_data in zip(axes, data):
        y_min = np.nanmin(y_data)
        y_max = np.nanmax(y_data)

        if display_mode["value"] == "linear":
            ax.set_ylim(0.0, max(y_max * 1.12, 1e-6))
        else:
            margin = max(3.0, 0.08 * (y_max - y_min + EPS))
            ax.set_ylim(y_min - margin, y_max + margin)

        ax.set_ylabel(get_y_label(), fontsize=10)


# ============================================================
# 13) Main update function
# ============================================================

def update_plots(_=None):
    """
    Recompute SNR and update all plots.
    """
    R = s_R.val
    H0 = s_H0.val
    Pt = s_Pt.val
    sigma_n2 = s_sigma.val

    snr_current = compute_snr_linear(
        R,
        H0,
        Pt,
        sigma_n2
    )

    snr_current_db = compute_snr_db(snr_current)
    snr_current_displayed = get_displayed_snr(snr_current)

    snr_vs_H0 = compute_snr_linear(
        R,
        H0_RANGE,
        Pt,
        sigma_n2
    )

    snr_vs_Pt = compute_snr_linear(
        R,
        H0,
        PT_RANGE,
        sigma_n2
    )

    snr_vs_sigma = compute_snr_linear(
        R,
        H0,
        Pt,
        SIGMA_N2_RANGE
    )

    # Update line plots
    line_H0.set_ydata(get_displayed_snr(snr_vs_H0))
    point_H0.set_data([H0], [snr_current_displayed])

    line_Pt.set_ydata(get_displayed_snr(snr_vs_Pt))
    point_Pt.set_data([Pt], [snr_current_displayed])

    line_sigma.set_ydata(get_displayed_snr(snr_vs_sigma))
    point_sigma.set_data([sigma_n2], [snr_current_displayed])

    # Update heatmap
    snr_grid = compute_snr_linear(
        R,
        H0_GRID,
        PT_GRID,
        sigma_n2
    )

    snr_grid_db = compute_snr_db_for_plot(snr_grid)

    heatmap.set_data(snr_grid_db)

    vmax = np.nanmax(snr_grid_db)
    if vmax <= DB_FLOOR:
        vmax = DB_FLOOR + 1.0

    heatmap.set_clim(
        vmin=DB_FLOOR,
        vmax=vmax
    )

    point_heatmap.set_data([H0], [Pt])

    # Update axes and guide lines
    update_axis_limits(R, H0, Pt, sigma_n2)
    update_threshold_visibility()

    # Update information panel
    quality_comment = format_snr_quality_comment(snr_current_db)

    info_text.set_text(
        "Current Operating Point\n"
        "-----------------------\n"
        f"R = {R:.3f} A/W\n"
        f"H(0) = {H0:.4f} [-]\n"
        f"P_t = {Pt:.3f} [norm.]\n"
        f"sigma_n^2 = {sigma_n2:.4f}\n\n"
        f"SNR = {snr_current:.4e} linear\n"
        f"SNR = {snr_current_db:.2f} dB\n"
        f"Quality: {quality_comment}\n\n"
        "Model Relations\n"
        "---------------\n"
        "SNR ∝ R²\n"
        "SNR ∝ H(0)²\n"
        "SNR ∝ P_t²\n"
        "SNR ∝ 1 / sigma_n²\n\n"
        "Model Note\n"
        "----------\n"
        "H(0) is treated as a\n"
        "parametric channel DC\n"
        "gain. This script does\n"
        "not calculate a full\n"
        "Lambertian VLC channel."
    )

    fig.canvas.draw_idle()


# ============================================================
# 14) Button functions
# ============================================================

def reset_sliders(_=None):
    """
    Reset all sliders to initial values.
    """
    s_R.reset()
    s_H0.reset()
    s_Pt.reset()
    s_sigma.reset()


def toggle_display_mode(_=None):
    """
    Toggle first three plots between linear SNR and dB SNR.
    The heatmap always remains in dB scale.
    """
    if display_mode["value"] == "linear":
        display_mode["value"] = "db"
    else:
        display_mode["value"] = "linear"

    update_plots()


# ============================================================
# 15) Connect callbacks
# ============================================================

s_R.on_changed(update_plots)
s_H0.on_changed(update_plots)
s_Pt.on_changed(update_plots)
s_sigma.on_changed(update_plots)

button_reset.on_clicked(reset_sliders)
button_mode.on_clicked(toggle_display_mode)


# ============================================================
# 16) Initial view
# ============================================================

update_plots()
plt.show()