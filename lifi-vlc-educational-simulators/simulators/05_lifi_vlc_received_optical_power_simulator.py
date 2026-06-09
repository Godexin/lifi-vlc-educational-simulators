"""
============================================================
Interactive Li-Fi / VLC Received Optical Power Simulator
============================================================

This script visualizes the received optical power in a Li-Fi /
Visible Light Communication (VLC) system using the basic relation:

    P_r = H(0) * P_t

where:
    P_r  : received optical power [W]
    H(0) : channel DC gain, dimensionless
    P_t  : transmitted optical power [W]

Main purpose:
    - Show how received optical power changes with channel DC gain.
    - Show how received optical power changes with transmitted power.
    - Show the combined multiplicative effect using a heatmap.

Important limitation:
    This script does not calculate H(0) physically from distance,
    angle, FOV, Lambertian order, detector area, filter gain, or
    concentrator gain. H(0) is used as a user-controlled abstract
    channel gain.

    This is not a complete Li-Fi communication simulator.
    It does not include NLOS reflections, channel impulse response
    h(t), noise, SNR, BER, modulation, or receiver electronics.

Recommended file name:
    vlc_received_optical_power_simulator.py
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, Button, RadioButtons, CheckButtons


# ============================================================
# 1) Default parameters and simulation ranges
# ============================================================

DEFAULTS = {
    "log10_H0": -4.0,     # H(0) = 10^-4, realistic starting point
    "Pt_W": 1.0,          # transmitted optical power in watts
}

H0_RANGE = np.logspace(-6, 0, 700)     # 10^-6 to 1
PT_RANGE_W = np.linspace(0.0, 5.0, 700)

H0_GRID, PT_GRID_W = np.meshgrid(H0_RANGE, PT_RANGE_W)


# ============================================================
# 2) Calculation and formatting helper functions
# ============================================================

def compute_received_power(H0, Pt_W):
    """
    Compute received optical power.

        P_r = H(0) * P_t

    Parameters
    ----------
    H0 : float or ndarray
        Channel DC gain, dimensionless.

    Pt_W : float or ndarray
        Transmitted optical power in watts.

    Returns
    -------
    float or ndarray
        Received optical power in watts.
    """
    H0 = np.asarray(H0, dtype=float)
    Pt_W = np.asarray(Pt_W, dtype=float)

    H0 = np.maximum(H0, 0.0)
    Pt_W = np.maximum(Pt_W, 0.0)

    return H0 * Pt_W


def watts_to_mw(power_W):
    """
    Convert watts to milliwatts.
    """
    return np.asarray(power_W, dtype=float) * 1000.0


def convert_power_unit(power_W, unit):
    """
    Convert power from W to the selected display unit.
    """
    if unit == "mW":
        return watts_to_mw(power_W)

    return np.asarray(power_W, dtype=float)


def power_unit_label(unit):
    """
    Return the display label for the selected power unit.
    """
    if unit == "mW":
        return "mW"

    return "W"


def safe_for_log_plot(y):
    """
    Replace non-positive values with NaN for logarithmic plotting.
    """
    y = np.asarray(y, dtype=float)
    return np.where(y > 0.0, y, np.nan)


def format_ratio(Pr_W, Pt_W):
    """
    Format P_r / P_t ratio.

    If P_t = 0, the ratio is undefined.
    """
    if Pt_W <= 0.0:
        return "undefined"

    return f"{Pr_W / Pt_W:.4e}"


# ============================================================
# 3) Main interactive application
# ============================================================

class VLCReceivedPowerApp:
    """
    Interactive simulator for received optical power in Li-Fi/VLC systems.
    """

    def __init__(self):
        self.fig = plt.figure(figsize=(15.5, 9))
        self.fig.canvas.manager.set_window_title(
            "Li-Fi / VLC Received Optical Power Simulator"
        )

        self._create_layout()
        self._create_initial_plots()
        self._create_widgets()
        self._connect_callbacks()
        self.update(None)

    # --------------------------------------------------------
    # Layout
    # --------------------------------------------------------
    def _create_layout(self):
        """
        Create a clean report/presentation-style layout.

        Top-left  : P_r versus H(0)
        Top-right : P_r versus P_t
        Bottom    : Heatmap
        Right     : Info and settings panel
        Bottom    : sliders
        """
        self.fig.suptitle(
            "Interactive Li-Fi / VLC Received Optical Power Simulator",
            fontsize=16,
            fontweight="bold",
            y=0.965,
        )

        # Main plots
        self.ax_H0 = self.fig.add_axes([0.07, 0.57, 0.29, 0.30])
        self.ax_Pt = self.fig.add_axes([0.41, 0.57, 0.29, 0.30])
        self.ax_heatmap = self.fig.add_axes([0.07, 0.18, 0.63, 0.29])

        # Right panel
        self.ax_info = self.fig.add_axes([0.74, 0.56, 0.23, 0.31])
        self.ax_info.axis("off")

        self.ax_unit = self.fig.add_axes([0.74, 0.40, 0.23, 0.10])
        self.ax_display = self.fig.add_axes([0.74, 0.27, 0.23, 0.09])
        self.ax_reset = self.fig.add_axes([0.80, 0.18, 0.11, 0.05])

        # Sliders
        self.ax_slider_H0 = self.fig.add_axes([0.14, 0.095, 0.45, 0.025])
        self.ax_slider_Pt = self.fig.add_axes([0.14, 0.055, 0.45, 0.025])

        # Small model note
        self.fig.text(
            0.07,
            0.025,
            "Model note: This tool visualizes only P_r = H(0)P_t. "
            "H(0) may come from a separate LOS/NLOS VLC channel model. "
            "Noise, modulation, SNR, BER and receiver electronics are not included.",
            fontsize=9,
            color="0.30",
        )

    # --------------------------------------------------------
    # Initial plots
    # --------------------------------------------------------
    def _create_initial_plots(self):
        H0 = self.current_H0()
        Pt_W = DEFAULTS["Pt_W"]
        Pr_W = compute_received_power(H0, Pt_W)

        # Initial display unit
        unit = "W"
        scale_Pr_vs_H0 = convert_power_unit(
            compute_received_power(H0_RANGE, Pt_W), unit
        )
        scale_Pr_vs_Pt = convert_power_unit(
            compute_received_power(H0, PT_RANGE_W), unit
        )
        scale_Pr_grid = convert_power_unit(
            compute_received_power(H0_GRID, PT_GRID_W), unit
        )

        # Plot 1: P_r versus H(0)
        self.line_H0, = self.ax_H0.plot(
            H0_RANGE,
            scale_Pr_vs_H0,
            linewidth=2.2,
            label=r"$P_r = H(0)P_t$",
        )

        self.point_H0, = self.ax_H0.plot(
            [H0],
            [convert_power_unit(Pr_W, unit)],
            "o",
            markersize=7,
            label="Operating point",
        )

        self.ax_H0.set_title(r"Received Power versus Channel DC Gain")
        self.ax_H0.set_xlabel(r"Channel DC gain, $H(0)$")
        self.ax_H0.set_ylabel(r"Received optical power, $P_r$ (W)")
        self.ax_H0.set_xscale("log")
        self.ax_H0.grid(True, alpha=0.30)
        self.ax_H0.legend(fontsize=8, loc="best")

        self.ax_H0.text(
            0.04,
            0.92,
            r"$P_r = H(0)P_t$",
            transform=self.ax_H0.transAxes,
            fontsize=11,
            bbox=dict(boxstyle="round", facecolor="white", alpha=0.85),
        )

        # Plot 2: P_r versus P_t
        self.line_Pt, = self.ax_Pt.plot(
            PT_RANGE_W,
            scale_Pr_vs_Pt,
            linewidth=2.2,
            label=r"$P_r = H(0)P_t$",
        )

        self.point_Pt, = self.ax_Pt.plot(
            [Pt_W],
            [convert_power_unit(Pr_W, unit)],
            "o",
            markersize=7,
            label="Operating point",
        )

        self.ax_Pt.set_title(r"Received Power versus Transmitted Power")
        self.ax_Pt.set_xlabel(r"Transmitted optical power, $P_t$ (W)")
        self.ax_Pt.set_ylabel(r"Received optical power, $P_r$ (W)")
        self.ax_Pt.grid(True, alpha=0.30)
        self.ax_Pt.legend(fontsize=8, loc="best")

        self.ax_Pt.text(
            0.04,
            0.92,
            r"$H(0)$ is fixed in this plot",
            transform=self.ax_Pt.transAxes,
            fontsize=10,
            bbox=dict(boxstyle="round", facecolor="white", alpha=0.85),
        )

        # Plot 3: heatmap
        self.heatmap = self.ax_heatmap.pcolormesh(
            H0_GRID,
            PT_GRID_W,
            scale_Pr_grid,
            shading="auto",
            cmap="viridis",
        )

        self.point_heatmap, = self.ax_heatmap.plot(
            [H0],
            [Pt_W],
            "o",
            markersize=8,
            markeredgecolor="white",
            markeredgewidth=1.3,
            label="Operating point",
        )

        self.heatmap_label = self.ax_heatmap.text(
            H0,
            Pt_W,
            "  current point",
            color="white",
            fontsize=9,
            va="center",
            ha="left",
        )

        self.ax_heatmap.set_title(
            r"Heatmap of Received Optical Power: $P_r = H(0)P_t$"
        )
        self.ax_heatmap.set_xlabel(r"Channel DC gain, $H(0)$")
        self.ax_heatmap.set_ylabel(r"Transmitted optical power, $P_t$ (W)")
        self.ax_heatmap.set_xscale("log")
        self.ax_heatmap.grid(False)
        self.ax_heatmap.legend(fontsize=8, loc="upper left")

        self.cbar = self.fig.colorbar(
            self.heatmap,
            ax=self.ax_heatmap,
            pad=0.02,
        )
        self.cbar.set_label(r"Received optical power, $P_r$ (W)")

    # --------------------------------------------------------
    # Widgets
    # --------------------------------------------------------
    def _create_widgets(self):
        self.s_logH0 = Slider(
            self.ax_slider_H0,
            r"log10 Channel gain, $\log_{10}(H(0))$",
            -6.0,
            0.0,
            valinit=DEFAULTS["log10_H0"],
            valstep=0.01,
        )

        self.s_Pt = Slider(
            self.ax_slider_Pt,
            r"Transmitted optical power, $P_t$ (W)",
            0.0,
            5.0,
            valinit=DEFAULTS["Pt_W"],
            valstep=0.01,
        )

        self.radio_unit = RadioButtons(
            self.ax_unit,
            ("W", "mW"),
            active=0,
        )
        self.ax_unit.set_title("Power unit", fontsize=10)

        self.check_display = CheckButtons(
            self.ax_display,
            ("Log H-axis", "Log P_r-axis"),
            (True, False),
        )
        self.ax_display.set_title("Display options", fontsize=10)

        self.button_reset = Button(self.ax_reset, "Reset")

    # --------------------------------------------------------
    # Callbacks
    # --------------------------------------------------------
    def _connect_callbacks(self):
        self.s_logH0.on_changed(self.update)
        self.s_Pt.on_changed(self.update)
        self.radio_unit.on_clicked(self.update)
        self.check_display.on_clicked(self.update)
        self.button_reset.on_clicked(self.reset)

    # --------------------------------------------------------
    # Current values
    # --------------------------------------------------------
    def current_H0(self):
        """
        Convert log10(H(0)) slider value into H(0).
        """
        if not hasattr(self, "s_logH0"):
            return 10.0 ** DEFAULTS["log10_H0"]

        return 10.0 ** self.s_logH0.val

    def current_unit(self):
        """
        Return selected power display unit.
        """
        if not hasattr(self, "radio_unit"):
            return "W"

        return self.radio_unit.value_selected

    # --------------------------------------------------------
    # Axis scaling helper
    # --------------------------------------------------------
    @staticmethod
    def set_y_limits(ax, y_values, log_y=False):
        """
        Apply clean y-limits for linear or logarithmic y-axis.
        """
        y = np.asarray(y_values, dtype=float)
        y = y[np.isfinite(y)]

        if log_y:
            y = y[y > 0.0]

        if y.size == 0:
            if log_y:
                ax.set_ylim(1e-12, 1e-3)
            else:
                ax.set_ylim(0.0, 1.0)
            return

        ymin = float(np.min(y))
        ymax = float(np.max(y))

        if np.isclose(ymin, ymax):
            pad = max(abs(ymax) * 0.1, 1e-12)
            ax.set_ylim(max(ymin - pad, 1e-15 if log_y else 0.0), ymax + pad)
            return

        if log_y:
            positive_y = y[y > 0.0]
            ax.set_ylim(np.min(positive_y) / 1.5, np.max(positive_y) * 1.5)
        else:
            ax.set_ylim(0.0, ymax * 1.10)

    # --------------------------------------------------------
    # Main update function
    # --------------------------------------------------------
    def update(self, _):
        H0 = self.current_H0()
        Pt_W = self.s_Pt.val
        Pr_W = float(compute_received_power(H0, Pt_W))

        unit = self.current_unit()
        unit_label = power_unit_label(unit)

        log_H_axis, log_Pr_axis = self.check_display.get_status()
        log_H_axis = bool(log_H_axis)
        log_Pr_axis = bool(log_Pr_axis)

        # Calculate curves in watts
        Pr_vs_H0_W = compute_received_power(H0_RANGE, Pt_W)
        Pr_vs_Pt_W = compute_received_power(H0, PT_RANGE_W)
        Pr_grid_W = compute_received_power(H0_GRID, PT_GRID_W)

        # Convert to selected unit
        Pr_vs_H0 = convert_power_unit(Pr_vs_H0_W, unit)
        Pr_vs_Pt = convert_power_unit(Pr_vs_Pt_W, unit)
        Pr_grid = convert_power_unit(Pr_grid_W, unit)
        Pr_display = float(convert_power_unit(Pr_W, unit))

        # Logarithmic y-axis safety
        y_H0_plot = safe_for_log_plot(Pr_vs_H0) if log_Pr_axis else Pr_vs_H0
        y_Pt_plot = safe_for_log_plot(Pr_vs_Pt) if log_Pr_axis else Pr_vs_Pt
        Pr_point_plot = Pr_display if (not log_Pr_axis or Pr_display > 0.0) else np.nan

        # Update line plots
        self.line_H0.set_ydata(y_H0_plot)
        self.point_H0.set_data([H0], [Pr_point_plot])

        self.line_Pt.set_ydata(y_Pt_plot)
        self.point_Pt.set_data([Pt_W], [Pr_point_plot])

        # Update heatmap
        self.heatmap.set_array(Pr_grid.ravel())
        self.heatmap.set_clim(np.nanmin(Pr_grid), np.nanmax(Pr_grid))
        self.cbar.update_normal(self.heatmap)
        self.cbar.set_label(rf"Received optical power, $P_r$ ({unit_label})")

        self.point_heatmap.set_data([H0], [Pt_W])
        self.heatmap_label.set_position((H0, Pt_W))

        # Axis labels
        self.ax_H0.set_ylabel(rf"Received optical power, $P_r$ ({unit_label})")
        self.ax_Pt.set_ylabel(rf"Received optical power, $P_r$ ({unit_label})")

        # Axis scales
        self.ax_H0.set_xscale("log" if log_H_axis else "linear")
        self.ax_heatmap.set_xscale("log" if log_H_axis else "linear")

        self.ax_H0.set_yscale("log" if log_Pr_axis else "linear")
        self.ax_Pt.set_yscale("log" if log_Pr_axis else "linear")

        # Limits
        self.ax_H0.set_xlim(H0_RANGE[0], H0_RANGE[-1])
        self.ax_Pt.set_xlim(PT_RANGE_W[0], PT_RANGE_W[-1])
        self.ax_heatmap.set_xlim(H0_RANGE[0], H0_RANGE[-1])
        self.ax_heatmap.set_ylim(PT_RANGE_W[0], PT_RANGE_W[-1])

        self.set_y_limits(self.ax_H0, y_H0_plot, log_Pr_axis)
        self.set_y_limits(self.ax_Pt, y_Pt_plot, log_Pr_axis)

        # Info panel
        self.ax_info.clear()
        self.ax_info.axis("off")

        Pt_mW = watts_to_mw(Pt_W)
        Pr_mW = watts_to_mw(Pr_W)

        if Pt_W > 0:
            interpretation = "Received power scales linearly with both H(0) and P_t."
        else:
            interpretation = "P_t is zero, so received power is also zero."

        info = (
            "Current Operating Point\n"
            "-----------------------\n"
            f"H(0)       = {H0:.4e}\n"
            f"log10 H(0) = {np.log10(H0):.2f}\n\n"
            f"P_t        = {Pt_W:.4f} W\n"
            f"P_t        = {Pt_mW:.2f} mW\n\n"
            f"P_r        = {Pr_W:.4e} W\n"
            f"P_r        = {Pr_mW:.4f} mW\n\n"
            f"P_r / P_t  = {format_ratio(Pr_W, Pt_W)}\n\n"
            "Comment\n"
            "-------\n"
            f"{interpretation}"
        )

        self.ax_info.text(
            0.02,
            0.98,
            info,
            va="top",
            ha="left",
            fontsize=9.5,
            family="monospace",
            bbox=dict(
                boxstyle="round,pad=0.6",
                facecolor="white",
                edgecolor="0.55",
                alpha=0.98,
            ),
        )

        self.fig.canvas.draw_idle()

    # --------------------------------------------------------
    # Reset button
    # --------------------------------------------------------
    def reset(self, _):
        self.s_logH0.reset()
        self.s_Pt.reset()
        self.update(None)


# ============================================================
# 4) Run application
# ============================================================

if __name__ == "__main__":
    app = VLCReceivedPowerApp()

    print("\nRecommended file name:")
    print("    vlc_received_optical_power_simulator.py")

    print("\nModel limitation:")
    print("    This program only models P_r = H(0)P_t.")
    print("    H(0) is not physically calculated inside this script.")
    print("    A complete Li-Fi/VLC simulator should also include distance, angle,")
    print("    FOV, Lambertian radiation, NLOS reflections, h(t), noise,")
    print("    modulation, SNR/BER analysis, and receiver electronics.\n")

    plt.show()