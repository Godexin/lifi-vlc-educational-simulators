"""
============================================================
Interactive Li-Fi / VLC LOS DC Channel Gain Simulator
============================================================

Clean-layout version.

This script visualizes the Line-of-Sight (LOS) DC channel gain
of a Li-Fi / Visible Light Communication (VLC) link.

LOS DC gain model:

    H_LOS(0) = ((m + 1) * A_PD / (2*pi*d^2))
               * cos(Phi)^m * T_s * g * cos(psi)

valid for:

    0 <= psi <= psi_c

otherwise:

    H_LOS(0) = 0

This version fixes the previous GUI layout problem:
    - no overlapping right-side panels
    - no clipped slider labels
    - cleaner plot/control separation
    - better report/presentation appearance
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, Button, RadioButtons, CheckButtons


# ============================================================
# 1) Constants and default values
# ============================================================

MIN_DISTANCE = 1e-6
MIN_ANGLE_DEG = 1e-6
MAX_ANGLE_DEG = 89.999

DEFAULT = {
    "m_manual": 1.0,
    "phi_half_deg": 60.0,
    "A_PD": 1e-4,
    "d": 1.5,
    "Phi_deg": 20.0,
    "psi_deg": 15.0,
    "psi_c_deg": 60.0,
    "T_s": 1.0,
    "g_manual": 1.0,
    "n": 1.5,
}

D_RANGE = np.linspace(0.1, 5.0, 700)
PSI_RANGE = np.linspace(0.0, 89.0, 700)


# ============================================================
# 2) Mathematical helper functions
# ============================================================

def safe_cos_deg(angle_deg):
    """Cosine of an angle in degrees, clipped to non-negative values."""
    angle_rad = np.deg2rad(angle_deg)
    return np.clip(np.cos(angle_rad), 0.0, None)


def safe_sin_deg(angle_deg):
    """Sine of an angle in degrees, protected from zero division."""
    angle_deg = np.clip(angle_deg, MIN_ANGLE_DEG, MAX_ANGLE_DEG)
    angle_rad = np.deg2rad(angle_deg)
    return np.clip(np.sin(angle_rad), 1e-12, None)


def lambertian_order(phi_half_deg):
    """
    Calculate Lambertian order from LED half-power semi-angle.

        m = ln(1/2) / ln(cos(Phi_1/2))
    """
    phi_half_deg = np.clip(phi_half_deg, MIN_ANGLE_DEG, MAX_ANGLE_DEG)
    cos_half = safe_cos_deg(phi_half_deg)
    cos_half = np.clip(cos_half, 1e-12, 1.0 - 1e-12)
    return float(np.log(0.5) / np.log(cos_half))


def concentrator_gain(n, psi_c_deg):
    """
    Calculate optical concentrator gain.

        g = n^2 / sin^2(psi_c)
    """
    n = max(float(n), 1.0)
    sin_psi_c = safe_sin_deg(psi_c_deg)
    return float((n ** 2) / (sin_psi_c ** 2))


def compute_h_los(m, A_PD, d, Phi_deg, psi_deg, psi_c_deg, T_s, g):
    """
    Vectorized LOS DC channel gain calculation.

    Works with scalar or NumPy array inputs.
    """
    m = max(float(m), 0.0)
    A_PD = max(float(A_PD), 0.0)
    T_s = max(float(T_s), 0.0)
    g = max(float(g), 0.0)

    d = np.maximum(np.asarray(d, dtype=float), MIN_DISTANCE)
    psi_deg = np.asarray(psi_deg, dtype=float)

    cos_phi = safe_cos_deg(Phi_deg)
    cos_psi = safe_cos_deg(psi_deg)

    H = (
        ((m + 1.0) * A_PD / (2.0 * np.pi * d**2))
        * (cos_phi ** m)
        * T_s
        * g
        * cos_psi
    )

    fov_mask = (psi_deg >= 0.0) & (psi_deg <= psi_c_deg)
    return np.where(fov_mask, H, 0.0)


def optical_path_loss_db(H):
    """
    Optical path loss:

        OPL = -10 log10(H)

    If H <= 0, OPL is infinite.
    """
    H = np.asarray(H, dtype=float)

    with np.errstate(divide="ignore", invalid="ignore"):
        opl = -10.0 * np.log10(H)

    return np.where(H > 0.0, opl, np.inf)


def plot_quantity(H, show_opl=False):
    """Return either H_LOS(0) or OPL for plotting."""
    if not show_opl:
        return np.asarray(H, dtype=float)

    opl = optical_path_loss_db(H)
    return np.where(np.isfinite(opl), opl, np.nan)


def format_opl(H):
    """Format scalar OPL value safely."""
    H = float(np.asarray(H))

    if H <= 0.0:
        return "infinite"

    return f"{float(optical_path_loss_db(H)):.2f} dB"


# ============================================================
# 3) Main simulator class
# ============================================================

class VLCLOSGainApp:
    """Clean interactive GUI for LOS DC gain visualization."""

    def __init__(self):
        self.fig = plt.figure(figsize=(15, 9))
        self.fig.canvas.manager.set_window_title("Li-Fi / VLC LOS DC Gain Simulator")

        self._create_layout()
        self._create_plots()
        self._create_widgets()
        self._connect_events()
        self.update(None)

    # --------------------------------------------------------
    # Layout
    # --------------------------------------------------------
    def _create_layout(self):
        """
        Manual layout.

        Left side:
            two plots

        Bottom:
            sliders in two columns

        Right side:
            information and mode controls
        """

        self.fig.suptitle(
            "Interactive Li-Fi / VLC LOS DC Channel Gain Simulator",
            fontsize=16,
            fontweight="bold",
            y=0.965,
        )

        # Main plot axes
        self.ax_dist = self.fig.add_axes([0.07, 0.62, 0.62, 0.25])
        self.ax_psi = self.fig.add_axes([0.07, 0.34, 0.62, 0.23])

        # Right-side panels
        self.ax_info = self.fig.add_axes([0.725, 0.55, 0.245, 0.32])
        self.ax_info.axis("off")

        self.ax_m_mode = self.fig.add_axes([0.725, 0.415, 0.245, 0.095])
        self.ax_g_mode = self.fig.add_axes([0.725, 0.285, 0.245, 0.095])
        self.ax_options = self.fig.add_axes([0.725, 0.165, 0.245, 0.075])
        self.ax_reset = self.fig.add_axes([0.795, 0.075, 0.105, 0.045])

        # Slider axes, two clean columns
        slider_h = 0.020
        row_gap = 0.035

        left_x = 0.12
        right_x = 0.47
        slider_w = 0.23
        y0 = 0.265

        self.slider_axes = {}

        left_labels = [
            "m",
            "Phi_half",
            "A_PD",
            "d",
            "Phi",
        ]

        right_labels = [
            "psi",
            "psi_c",
            "T_s",
            "g",
            "n",
        ]

        for i, key in enumerate(left_labels):
            y = y0 - i * row_gap
            self.slider_axes[key] = self.fig.add_axes(
                [left_x, y, slider_w, slider_h],
                facecolor="whitesmoke",
            )

        for i, key in enumerate(right_labels):
            y = y0 - i * row_gap
            self.slider_axes[key] = self.fig.add_axes(
                [right_x, y, slider_w, slider_h],
                facecolor="whitesmoke",
            )

        # Section labels
        self.fig.text(
            0.07,
            0.305,
            "Control Parameters",
            fontsize=11,
            fontweight="bold",
        )

        self.fig.text(
            0.07,
            0.025,
            "Model limitation: This tool models only LOS DC gain. "
            "NLOS reflections, channel impulse response h(t), noise, modulation, SNR and BER are not included.",
            fontsize=9,
            color="0.30",
        )

    # --------------------------------------------------------
    # Initial plots
    # --------------------------------------------------------
    def _create_plots(self):
        params = self.get_params()

        H_d = compute_h_los(
            params["m"],
            params["A_PD"],
            D_RANGE,
            params["Phi_deg"],
            params["psi_deg"],
            params["psi_c_deg"],
            params["T_s"],
            params["g"],
        )

        H_psi = compute_h_los(
            params["m"],
            params["A_PD"],
            params["d"],
            params["Phi_deg"],
            PSI_RANGE,
            params["psi_c_deg"],
            params["T_s"],
            params["g"],
        )

        H_point = compute_h_los(
            params["m"],
            params["A_PD"],
            params["d"],
            params["Phi_deg"],
            params["psi_deg"],
            params["psi_c_deg"],
            params["T_s"],
            params["g"],
        )

        H_point = float(np.asarray(H_point))

        # Distance plot
        self.line_d, = self.ax_dist.plot(
            D_RANGE,
            H_d,
            lw=2.2,
            label=r"$H_{LOS}(0)$",
        )

        self.point_d, = self.ax_dist.plot(
            [params["d"]],
            [H_point],
            "o",
            ms=7,
            label="Operating point",
        )

        self.ax_dist.set_title(r"LOS DC Channel Gain $H_{LOS}(0)$ versus Distance")
        self.ax_dist.set_xlabel("Distance, d (m)")
        self.ax_dist.set_ylabel(r"$H_{LOS}(0)$")
        self.ax_dist.grid(True, alpha=0.30)
        self.ax_dist.legend(loc="upper right", fontsize=9)

        # Incidence angle plot
        self.line_psi, = self.ax_psi.plot(
            PSI_RANGE,
            H_psi,
            lw=2.2,
            label=r"$H_{LOS}(0)$",
        )

        self.point_psi, = self.ax_psi.plot(
            [params["psi_deg"]],
            [H_point],
            "o",
            ms=7,
            label="Operating point",
        )

        self.vline_psi = self.ax_psi.axvline(
            params["psi_deg"],
            ls="--",
            lw=1.5,
            alpha=0.8,
            label=r"$\psi$",
        )

        self.vline_psic = self.ax_psi.axvline(
            params["psi_c_deg"],
            ls=":",
            lw=2.0,
            alpha=0.9,
            label=r"$\psi_c$",
        )

        self.fov_region = self.ax_psi.axvspan(
            0,
            params["psi_c_deg"],
            alpha=0.08,
            label="FOV region",
        )

        self.ax_psi.set_title(r"LOS DC Channel Gain $H_{LOS}(0)$ versus Incidence Angle")
        self.ax_psi.set_xlabel(r"Incidence angle, $\psi$ (deg)")
        self.ax_psi.set_ylabel(r"$H_{LOS}(0)$")
        self.ax_psi.grid(True, alpha=0.30)
        self.ax_psi.legend(loc="upper right", fontsize=9)

    # --------------------------------------------------------
    # Widgets
    # --------------------------------------------------------
    def _create_widgets(self):
        self.s_m = Slider(
            self.slider_axes["m"],
            "m",
            0.1,
            20.0,
            valinit=DEFAULT["m_manual"],
            valstep=0.1,
        )

        self.s_phi_half = Slider(
            self.slider_axes["Phi_half"],
            r"$\Phi_{1/2}$ (deg)",
            1.0,
            85.0,
            valinit=DEFAULT["phi_half_deg"],
            valstep=0.1,
        )

        self.s_apd = Slider(
            self.slider_axes["A_PD"],
            r"$A_{PD}$",
            1e-6,
            5e-4,
            valinit=DEFAULT["A_PD"],
            valfmt="%.1e",
        )

        self.s_d = Slider(
            self.slider_axes["d"],
            "d (m)",
            0.1,
            5.0,
            valinit=DEFAULT["d"],
            valstep=0.01,
        )

        self.s_phi = Slider(
            self.slider_axes["Phi"],
            r"$\Phi$ (deg)",
            0.0,
            89.0,
            valinit=DEFAULT["Phi_deg"],
            valstep=0.1,
        )

        self.s_psi = Slider(
            self.slider_axes["psi"],
            r"$\psi$ (deg)",
            0.0,
            89.0,
            valinit=DEFAULT["psi_deg"],
            valstep=0.1,
        )

        self.s_psic = Slider(
            self.slider_axes["psi_c"],
            r"$\psi_c$ (deg)",
            1.0,
            89.0,
            valinit=DEFAULT["psi_c_deg"],
            valstep=0.1,
        )

        self.s_ts = Slider(
            self.slider_axes["T_s"],
            r"$T_s$",
            0.0,
            2.0,
            valinit=DEFAULT["T_s"],
            valstep=0.01,
        )

        self.s_g = Slider(
            self.slider_axes["g"],
            "g",
            0.0,
            10.0,
            valinit=DEFAULT["g_manual"],
            valstep=0.01,
        )

        self.s_n = Slider(
            self.slider_axes["n"],
            "n",
            1.0,
            2.5,
            valinit=DEFAULT["n"],
            valstep=0.01,
        )

        self.radio_m = RadioButtons(
            self.ax_m_mode,
            ("Manual m", "From half-angle"),
            active=0,
        )
        self.ax_m_mode.set_title("Lambertian order", fontsize=10)

        self.radio_g = RadioButtons(
            self.ax_g_mode,
            ("Manual g", "From n and FOV"),
            active=0,
        )
        self.ax_g_mode.set_title("Concentrator gain", fontsize=10)

        self.checks = CheckButtons(
            self.ax_options,
            ("Log y-axis", "Plot OPL"),
            (False, False),
        )
        self.ax_options.set_title("Display", fontsize=10)

        self.reset_button = Button(self.ax_reset, "Reset")

    # --------------------------------------------------------
    # Event connections
    # --------------------------------------------------------
    def _connect_events(self):
        sliders = [
            self.s_m,
            self.s_phi_half,
            self.s_apd,
            self.s_d,
            self.s_phi,
            self.s_psi,
            self.s_psic,
            self.s_ts,
            self.s_g,
            self.s_n,
        ]

        for slider in sliders:
            slider.on_changed(self.update)

        self.radio_m.on_clicked(self.update)
        self.radio_g.on_clicked(self.update)
        self.checks.on_clicked(self.update)
        self.reset_button.on_clicked(self.reset)

    # --------------------------------------------------------
    # Current parameters
    # --------------------------------------------------------
    def get_params(self):
        if not hasattr(self, "s_m"):
            m = DEFAULT["m_manual"]
            g = DEFAULT["g_manual"]

            return {
                "m": m,
                "m_mode": "Manual m",
                "phi_half_deg": DEFAULT["phi_half_deg"],
                "A_PD": DEFAULT["A_PD"],
                "d": DEFAULT["d"],
                "Phi_deg": DEFAULT["Phi_deg"],
                "psi_deg": DEFAULT["psi_deg"],
                "psi_c_deg": DEFAULT["psi_c_deg"],
                "T_s": DEFAULT["T_s"],
                "g": g,
                "g_mode": "Manual g",
                "n": DEFAULT["n"],
            }

        if self.radio_m.value_selected == "Manual m":
            m = self.s_m.val
            m_mode = "Manual m"
        else:
            m = lambertian_order(self.s_phi_half.val)
            m_mode = "From half-angle"

        if self.radio_g.value_selected == "Manual g":
            g = self.s_g.val
            g_mode = "Manual g"
        else:
            g = concentrator_gain(self.s_n.val, self.s_psic.val)
            g_mode = "From n and FOV"

        return {
            "m": float(m),
            "m_mode": m_mode,
            "phi_half_deg": float(self.s_phi_half.val),
            "A_PD": float(self.s_apd.val),
            "d": float(self.s_d.val),
            "Phi_deg": float(self.s_phi.val),
            "psi_deg": float(self.s_psi.val),
            "psi_c_deg": float(self.s_psic.val),
            "T_s": float(self.s_ts.val),
            "g": float(g),
            "g_mode": g_mode,
            "n": float(self.s_n.val),
        }

    # --------------------------------------------------------
    # Axis scaling
    # --------------------------------------------------------
    @staticmethod
    def apply_y_limits(ax, y, log_axis=False, show_opl=False):
        y = np.asarray(y, dtype=float)
        y = y[np.isfinite(y)]

        if log_axis:
            y = y[y > 0]

        if y.size == 0:
            if show_opl:
                ax.set_ylim(0, 120)
            elif log_axis:
                ax.set_ylim(1e-12, 1e-2)
            else:
                ax.set_ylim(-1e-12, 1e-12)
            return

        ymin = float(np.min(y))
        ymax = float(np.max(y))

        if np.isclose(ymin, ymax):
            pad = max(abs(ymin) * 0.1, 1e-12)
            ax.set_ylim(ymin - pad, ymax + pad)
            return

        if log_axis:
            ax.set_ylim(ymin / 1.5, ymax * 1.5)
        else:
            pad = 0.08 * (ymax - ymin)
            ax.set_ylim(ymin - pad, ymax + pad)

    # --------------------------------------------------------
    # Main update
    # --------------------------------------------------------
    def update(self, _):
        params = self.get_params()
        log_axis, show_opl = self.checks.get_status()

        # OPL is already in dB, so log-axis is disabled for OPL.
        use_log_axis = bool(log_axis and not show_opl)

        H_d = compute_h_los(
            params["m"],
            params["A_PD"],
            D_RANGE,
            params["Phi_deg"],
            params["psi_deg"],
            params["psi_c_deg"],
            params["T_s"],
            params["g"],
        )

        H_psi = compute_h_los(
            params["m"],
            params["A_PD"],
            params["d"],
            params["Phi_deg"],
            PSI_RANGE,
            params["psi_c_deg"],
            params["T_s"],
            params["g"],
        )

        H_point = compute_h_los(
            params["m"],
            params["A_PD"],
            params["d"],
            params["Phi_deg"],
            params["psi_deg"],
            params["psi_c_deg"],
            params["T_s"],
            params["g"],
        )

        H_point = float(np.asarray(H_point))

        y_d = plot_quantity(H_d, show_opl)
        y_psi = plot_quantity(H_psi, show_opl)
        y_point = plot_quantity(H_point, show_opl)

        y_point = float(np.asarray(y_point)) if np.isfinite(y_point).all() else np.nan

        if use_log_axis:
            y_d = np.where(y_d > 0, y_d, np.nan)
            y_psi = np.where(y_psi > 0, y_psi, np.nan)
            if not np.isfinite(y_point) or y_point <= 0:
                y_point = np.nan

        self.line_d.set_ydata(y_d)
        self.point_d.set_data([params["d"]], [y_point])

        self.line_psi.set_ydata(y_psi)
        self.point_psi.set_data([params["psi_deg"]], [y_point])

        self.vline_psi.set_xdata([params["psi_deg"], params["psi_deg"]])
        self.vline_psic.set_xdata([params["psi_c_deg"], params["psi_c_deg"]])

        self.fov_region.remove()
        self.fov_region = self.ax_psi.axvspan(
            0,
            params["psi_c_deg"],
            alpha=0.08,
        )

        if show_opl:
            ylabel = "Optical Path Loss, OPL (dB)"
            title_1 = "Optical Path Loss versus Distance"
            title_2 = "Optical Path Loss versus Incidence Angle"
        else:
            ylabel = r"LOS DC channel gain, $H_{LOS}(0)$"
            title_1 = r"LOS DC Channel Gain $H_{LOS}(0)$ versus Distance"
            title_2 = r"LOS DC Channel Gain $H_{LOS}(0)$ versus Incidence Angle"

        self.ax_dist.set_title(title_1)
        self.ax_psi.set_title(title_2)

        self.ax_dist.set_ylabel(ylabel)
        self.ax_psi.set_ylabel(ylabel)

        self.ax_dist.set_xlim(D_RANGE[0], D_RANGE[-1])
        self.ax_psi.set_xlim(PSI_RANGE[0], PSI_RANGE[-1])

        self.ax_dist.set_yscale("log" if use_log_axis else "linear")
        self.ax_psi.set_yscale("log" if use_log_axis else "linear")

        self.apply_y_limits(self.ax_dist, y_d, use_log_axis, show_opl)
        self.apply_y_limits(self.ax_psi, y_psi, use_log_axis, show_opl)

        fov_active = params["psi_deg"] <= params["psi_c_deg"]

        if fov_active:
            fov_text = "FOV status: ACTIVE"
        else:
            fov_text = "FOV status: BLOCKED"

        self.ax_info.clear()
        self.ax_info.axis("off")

        info = (
            "Current Parameters\n"
            "------------------\n"
            f"m mode : {params['m_mode']}\n"
            f"m      : {params['m']:.3f}\n"
            f"Phi1/2 : {params['phi_half_deg']:.2f} deg\n\n"
            f"A_PD   : {params['A_PD']:.2e} m^2\n"
            f"d      : {params['d']:.2f} m\n"
            f"Phi    : {params['Phi_deg']:.2f} deg\n"
            f"psi    : {params['psi_deg']:.2f} deg\n"
            f"psi_c  : {params['psi_c_deg']:.2f} deg\n"
            f"T_s    : {params['T_s']:.2f}\n\n"
            f"g mode : {params['g_mode']}\n"
            f"g      : {params['g']:.3f}\n"
            f"n      : {params['n']:.2f}\n\n"
            f"{fov_text}\n"
            f"H_LOS  : {H_point:.4e}\n"
            f"OPL    : {format_opl(H_point)}"
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
                boxstyle="round,pad=0.55",
                facecolor="white",
                edgecolor="0.55",
                alpha=0.98,
            ),
        )

        self.fig.canvas.draw_idle()

    # --------------------------------------------------------
    # Reset
    # --------------------------------------------------------
    def reset(self, _):
        self.s_m.reset()
        self.s_phi_half.reset()
        self.s_apd.reset()
        self.s_d.reset()
        self.s_phi.reset()
        self.s_psi.reset()
        self.s_psic.reset()
        self.s_ts.reset()
        self.s_g.reset()
        self.s_n.reset()
        self.update(None)


# ============================================================
# 4) Run
# ============================================================

if __name__ == "__main__":
    app = VLCLOSGainApp()

    print("\nRecommended file name:")
    print("    vlc_los_dc_gain_simulator_clean_layout.py")

    print("\nModel limitation:")
    print("    This simulator only models LOS DC channel gain H_LOS(0).")
    print("    It does not include NLOS reflections, h(t), noise, modulation, SNR or BER.\n")

    plt.show()