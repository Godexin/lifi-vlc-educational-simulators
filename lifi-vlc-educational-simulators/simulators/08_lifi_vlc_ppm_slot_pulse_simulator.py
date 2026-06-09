import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, Button


# ============================================================
# Interactive Single-Symbol PPM Slot Pulse Visualizer
# for Li-Fi / Visible Light Communication (VLC) Systems
# ============================================================
#
# Model:
#
# p_l(t) =
#   1, if ((l-1)T / L) <= t < (lT / L)
#   0, otherwise
#
# where:
#   p_l(t) : selected PPM slot pulse function
#   T      : symbol duration [s]
#   L      : PPM order / number of slots per symbol
#   l      : selected slot index, l in {1, 2, ..., L}
#   T_slot : slot duration, T / L
#
# Important note:
# This script visualizes only the single-symbol PPM slot pulse
# function p_l(t). It is not a complete Li-Fi/VLC transmitter,
# channel, receiver, or BER simulator.
#
# A complete PPM transmitter signal is usually written as:
#
#   x(t) = sum_k A * p_{l_k}(t - kT)
#
# In real VLC systems, additional blocks such as LED bandwidth,
# optical power, photodetector responsivity, channel DC gain,
# ambient-light noise, filtering, synchronization, and receiver
# decision logic must also be considered.
# ============================================================


# ------------------------------------------------------------
# 1) Simulation constants
# ------------------------------------------------------------
FS = 200_000                         # Sampling frequency [Hz]
PPM_ORDERS = (2, 4, 8, 16)            # Classical power-of-two PPM orders

DEFAULT_T_MS = 1.0                    # Initial symbol duration [ms]
DEFAULT_ORDER_INDEX = 1               # Index 1 -> L = 4
DEFAULT_SLOT_INDEX = 2                # Initial selected slot, 1-based

MIN_T_MS = 0.2                        # Minimum symbol duration [ms]
MAX_T_MS = 3.0                        # Maximum symbol duration [ms]
T_STEP_MS = 0.05                      # Slider step [ms]


# ------------------------------------------------------------
# 2) Core PPM signal-generation function
# ------------------------------------------------------------
def build_single_symbol_ppm_pulse(
    symbol_duration_s: float,
    ppm_order: int,
    selected_slot: int,
    sampling_frequency_hz: float
) -> dict:
    """
    Generate a discrete-time approximation of a single-symbol
    PPM slot pulse function p_l(t).

    Parameters
    ----------
    symbol_duration_s : float
        The theoretical symbol duration T in seconds.
    ppm_order : int
        Number of slots per symbol, also called the PPM order L.
    selected_slot : int
        Selected slot index l, using 1-based indexing.
    sampling_frequency_hz : float
        Sampling frequency in Hz.

    Returns
    -------
    dict
        Dictionary containing time axis, pulse samples, theoretical
        timing values, actual discrete-time timing values, sample counts,
        and validated PPM parameters.
    """
    if symbol_duration_s <= 0:
        raise ValueError("symbol_duration_s must be positive.")

    if sampling_frequency_hz <= 0:
        raise ValueError("sampling_frequency_hz must be positive.")

    if ppm_order < 2:
        raise ValueError("ppm_order must be at least 2.")

    ppm_order = int(ppm_order)
    selected_slot = int(np.clip(round(selected_slot), 1, ppm_order))

    theoretical_slot_duration_s = symbol_duration_s / ppm_order

    # Discrete-time approximation:
    # The ideal slot duration may not correspond to an integer number
    # of samples, so it is rounded to the nearest integer sample count.
    samples_per_slot = max(
        1,
        int(round(theoretical_slot_duration_s * sampling_frequency_hz))
    )

    samples_per_symbol = ppm_order * samples_per_slot

    actual_slot_duration_s = samples_per_slot / sampling_frequency_hz
    actual_symbol_duration_s = samples_per_symbol / sampling_frequency_hz

    slot_duration_error_s = actual_slot_duration_s - theoretical_slot_duration_s
    symbol_duration_error_s = actual_symbol_duration_s - symbol_duration_s

    time_s = np.arange(samples_per_symbol) / sampling_frequency_hz
    pulse = np.zeros(samples_per_symbol)

    start_index = (selected_slot - 1) * samples_per_slot
    end_index = selected_slot * samples_per_slot
    pulse[start_index:end_index] = 1.0

    bits_per_symbol = int(np.log2(ppm_order))
    bit_pattern = format(selected_slot - 1, f"0{bits_per_symbol}b")

    return {
        "time_s": time_s,
        "pulse": pulse,
        "symbol_duration_s": symbol_duration_s,
        "theoretical_slot_duration_s": theoretical_slot_duration_s,
        "actual_slot_duration_s": actual_slot_duration_s,
        "actual_symbol_duration_s": actual_symbol_duration_s,
        "slot_duration_error_s": slot_duration_error_s,
        "symbol_duration_error_s": symbol_duration_error_s,
        "samples_per_slot": samples_per_slot,
        "samples_per_symbol": samples_per_symbol,
        "ppm_order": ppm_order,
        "selected_slot": selected_slot,
        "bits_per_symbol": bits_per_symbol,
        "bit_pattern": bit_pattern,
    }


def make_step_plot_arrays(time_s: np.ndarray, pulse: np.ndarray, fs_hz: float) -> tuple:
    """
    Convert sampled signal arrays into step-plot arrays.

    A step plot needs one extra time point at the end so that the final
    sample interval is displayed correctly.

    Parameters
    ----------
    time_s : np.ndarray
        Original sampled time axis.
    pulse : np.ndarray
        Pulse samples.
    fs_hz : float
        Sampling frequency in Hz.

    Returns
    -------
    tuple
        x-axis in milliseconds and y-axis values for a step plot.
    """
    if len(time_s) == 0:
        return np.array([]), np.array([])

    final_time_s = time_s[-1] + 1.0 / fs_hz
    time_step_s = np.append(time_s, final_time_s)
    pulse_step = np.append(pulse, pulse[-1])

    return time_step_s * 1e3, pulse_step


# ------------------------------------------------------------
# 3) Interactive visualization class
# ------------------------------------------------------------
class SingleSymbolPPMVisualizer:
    """
    Interactive Matplotlib visualizer for the single-symbol
    PPM slot pulse function p_l(t).
    """

    def __init__(self) -> None:
        self.rng = np.random.default_rng()
        self.dynamic_artists = []
        self.is_updating = False

        self.fig, self.ax = plt.subplots(figsize=(13.5, 6.3))
        plt.subplots_adjust(
            left=0.08,
            right=0.70,
            top=0.84,
            bottom=0.28
        )

        initial_order = PPM_ORDERS[DEFAULT_ORDER_INDEX]
        initial_data = build_single_symbol_ppm_pulse(
            symbol_duration_s=DEFAULT_T_MS * 1e-3,
            ppm_order=initial_order,
            selected_slot=DEFAULT_SLOT_INDEX,
            sampling_frequency_hz=FS
        )

        x_ms, y = make_step_plot_arrays(
            initial_data["time_s"],
            initial_data["pulse"],
            FS
        )

        self.waveform_line = self.ax.step(
            x_ms,
            y,
            where="post",
            linewidth=2.5,
            label=r"$p_l(t)$"
        )[0]

        self.info_text = self.ax.text(
            1.03,
            0.98,
            "",
            transform=self.ax.transAxes,
            fontsize=9.5,
            va="top",
            ha="left",
            bbox=dict(
                boxstyle="round,pad=0.45",
                facecolor="white",
                edgecolor="0.55",
                alpha=0.95
            )
        )

        self.note_text = self.ax.text(
            1.03,
            0.18,
            "",
            transform=self.ax.transAxes,
            fontsize=9,
            va="top",
            ha="left",
            bbox=dict(
                boxstyle="round,pad=0.45",
                facecolor="white",
                edgecolor="0.65",
                alpha=0.95
            )
        )

        self._configure_main_axes()
        self._create_controls()
        self.update_plot(None)

    def _configure_main_axes(self) -> None:
        """Configure static axis properties."""
        self.ax.set_title(
            r"Single-Symbol PPM Slot Pulse Function $p_l(t)$ for Li-Fi/VLC",
            fontsize=13,
            pad=12
        )
        self.ax.set_xlabel("Time [ms]", fontsize=11)
        self.ax.set_ylabel("Normalized optical intensity / amplitude", fontsize=11)
        self.ax.set_ylim(-0.15, 1.25)
        self.ax.grid(True, linestyle=":", alpha=0.65)
        self.ax.legend(loc="upper left")

    def _create_controls(self) -> None:
        """Create sliders and buttons."""
        slider_facecolor = "lightgoldenrodyellow"

        ax_symbol_time = plt.axes(
            [0.11, 0.17, 0.50, 0.035],
            facecolor=slider_facecolor
        )
        ax_order = plt.axes(
            [0.11, 0.11, 0.50, 0.035],
            facecolor=slider_facecolor
        )
        ax_slot = plt.axes(
            [0.11, 0.05, 0.50, 0.035],
            facecolor=slider_facecolor
        )

        self.symbol_time_slider = Slider(
            ax=ax_symbol_time,
            label="Symbol duration T [ms]",
            valmin=MIN_T_MS,
            valmax=MAX_T_MS,
            valinit=DEFAULT_T_MS,
            valstep=T_STEP_MS
        )

        self.order_slider = Slider(
            ax=ax_order,
            label="PPM order L",
            valmin=0,
            valmax=len(PPM_ORDERS) - 1,
            valinit=DEFAULT_ORDER_INDEX,
            valstep=1
        )

        self.slot_slider = Slider(
            ax=ax_slot,
            label="Selected slot l",
            valmin=1,
            valmax=PPM_ORDERS[DEFAULT_ORDER_INDEX],
            valinit=DEFAULT_SLOT_INDEX,
            valstep=1
        )

        reset_ax = plt.axes([0.74, 0.105, 0.13, 0.055])
        random_ax = plt.axes([0.74, 0.035, 0.13, 0.055])

        self.reset_button = Button(reset_ax, "Reset")
        self.random_button = Button(random_ax, "Random Slot")

        self.symbol_time_slider.on_changed(self.update_plot)
        self.order_slider.on_changed(self.update_plot)
        self.slot_slider.on_changed(self.update_plot)

        self.reset_button.on_clicked(self.reset)
        self.random_button.on_clicked(self.randomize_slot)

    def _current_ppm_order(self) -> int:
        """Return the current PPM order selected by the order slider."""
        order_index = int(round(self.order_slider.val))
        order_index = int(np.clip(order_index, 0, len(PPM_ORDERS) - 1))
        return PPM_ORDERS[order_index]

    def _remove_dynamic_artists(self) -> None:
        """Remove previously drawn dynamic artists."""
        for artist in self.dynamic_artists:
            try:
                artist.remove()
            except ValueError:
                pass
        self.dynamic_artists = []

    def _draw_slot_boundaries_and_labels(self, data: dict) -> None:
        """
        Draw symbol boundaries, slot boundaries, slot labels,
        and selected-slot highlighting.
        """
        ppm_order = data["ppm_order"]
        selected_slot = data["selected_slot"]
        actual_slot_duration_ms = data["actual_slot_duration_s"] * 1e3
        actual_symbol_duration_ms = data["actual_symbol_duration_s"] * 1e3

        selected_start_ms = (selected_slot - 1) * actual_slot_duration_ms
        selected_end_ms = selected_slot * actual_slot_duration_ms
        selected_center_ms = 0.5 * (selected_start_ms + selected_end_ms)

        selected_span = self.ax.axvspan(
            selected_start_ms,
            selected_end_ms,
            alpha=0.18,
            color="tab:orange",
            zorder=0
        )
        self.dynamic_artists.append(selected_span)

        left_boundary = self.ax.axvline(
            0,
            color="black",
            linestyle="--",
            linewidth=1.1,
            alpha=0.75
        )
        right_boundary = self.ax.axvline(
            actual_symbol_duration_ms,
            color="black",
            linestyle="--",
            linewidth=1.1,
            alpha=0.75
        )
        self.dynamic_artists.extend([left_boundary, right_boundary])

        for slot_number in range(1, ppm_order):
            boundary_ms = slot_number * actual_slot_duration_ms
            boundary = self.ax.axvline(
                boundary_ms,
                color="0.45",
                linestyle=":",
                linewidth=1.0,
                alpha=0.75
            )
            self.dynamic_artists.append(boundary)

        label_fontsize = 8.5 if ppm_order <= 8 else 7.0
        label_rotation = 0 if ppm_order <= 8 else 90

        for slot_number in range(1, ppm_order + 1):
            center_ms = (slot_number - 0.5) * actual_slot_duration_ms
            slot_label = self.ax.text(
                center_ms,
                -0.08,
                f"Slot {slot_number}",
                ha="center",
                va="center",
                fontsize=label_fontsize,
                rotation=label_rotation
            )
            self.dynamic_artists.append(slot_label)

        selected_label = self.ax.text(
            selected_center_ms,
            1.08,
            (
                f"Selected slot: {selected_slot}\n"
                f"bits: {data['bit_pattern']}"
            ),
            ha="center",
            va="bottom",
            fontsize=9.5,
            color="tab:red",
            bbox=dict(
                boxstyle="round,pad=0.25",
                facecolor="white",
                edgecolor="tab:red",
                alpha=0.95
            )
        )
        self.dynamic_artists.append(selected_label)

    def _update_information_boxes(self, data: dict) -> None:
        """Update the parameter and interpretation text boxes."""
        symbol_duration_ms = data["symbol_duration_s"] * 1e3
        theoretical_slot_ms = data["theoretical_slot_duration_s"] * 1e3
        actual_slot_ms = data["actual_slot_duration_s"] * 1e3
        actual_symbol_ms = data["actual_symbol_duration_s"] * 1e3
        slot_error_us = data["slot_duration_error_s"] * 1e6
        symbol_error_us = data["symbol_duration_error_s"] * 1e6

        self.info_text.set_text(
            "Current parameters\n"
            "------------------\n"
            f"T = {symbol_duration_ms:.3f} ms\n"
            f"L = {data['ppm_order']}\n"
            f"l = {data['selected_slot']}\n"
            f"bits/symbol = {data['bits_per_symbol']}\n"
            f"slot bit label = {data['bit_pattern']}\n\n"
            "Theoretical timing\n"
            "------------------\n"
            f"T_slot = T/L = {theoretical_slot_ms:.6f} ms\n\n"
            "Discrete-time timing\n"
            "--------------------\n"
            f"fs = {FS/1e3:.1f} kHz\n"
            f"samples/slot = {data['samples_per_slot']}\n"
            f"samples/symbol = {data['samples_per_symbol']}\n"
            f"T_slot,actual = {actual_slot_ms:.6f} ms\n"
            f"T_actual = {actual_symbol_ms:.6f} ms\n"
            f"slot error = {slot_error_us:+.3f} us\n"
            f"symbol error = {symbol_error_us:+.3f} us"
        )

        self.note_text.set_text(
            "Interpretation\n"
            "--------------\n"
            "The symbol duration is divided\n"
            "into L equal time slots.\n\n"
            "Only the selected slot is active;\n"
            "all other slots are zero.\n\n"
            "This is a teaching model of p_l(t),\n"
            "not a complete VLC channel or\n"
            "receiver simulation."
        )

    def update_plot(self, _event) -> None:
        """Update the waveform, slot markers, labels, and information boxes."""
        if self.is_updating:
            return

        self.is_updating = True

        try:
            symbol_duration_s = self.symbol_time_slider.val * 1e-3
            ppm_order = self._current_ppm_order()
            selected_slot = int(round(self.slot_slider.val))
            selected_slot = int(np.clip(selected_slot, 1, ppm_order))

            # Keep the selected-slot slider valid when L changes.
            self.slot_slider.valmax = ppm_order
            self.slot_slider.ax.set_xlim(1, ppm_order)

            if int(round(self.slot_slider.val)) != selected_slot:
                self.slot_slider.set_val(selected_slot)

            self.order_slider.valtext.set_text(str(ppm_order))
            self.slot_slider.valtext.set_text(str(selected_slot))

            data = build_single_symbol_ppm_pulse(
                symbol_duration_s=symbol_duration_s,
                ppm_order=ppm_order,
                selected_slot=selected_slot,
                sampling_frequency_hz=FS
            )

            x_ms, y = make_step_plot_arrays(
                data["time_s"],
                data["pulse"],
                FS
            )

            self.waveform_line.set_data(x_ms, y)

            self._remove_dynamic_artists()
            self._draw_slot_boundaries_and_labels(data)
            self._update_information_boxes(data)

            actual_symbol_ms = data["actual_symbol_duration_s"] * 1e3
            theoretical_symbol_ms = data["symbol_duration_s"] * 1e3
            x_max_ms = max(actual_symbol_ms, theoretical_symbol_ms)

            self.ax.set_xlim(0, x_max_ms)
            self.ax.set_ylim(-0.15, 1.25)

            self.fig.canvas.draw_idle()

        finally:
            self.is_updating = False

    def reset(self, _event) -> None:
        """Reset all controls to their initial values."""
        self.symbol_time_slider.reset()
        self.order_slider.reset()
        self.slot_slider.reset()
        self.update_plot(None)

    def randomize_slot(self, _event) -> None:
        """Select a random valid PPM slot for the current PPM order."""
        ppm_order = self._current_ppm_order()
        random_slot = int(self.rng.integers(1, ppm_order + 1))
        self.slot_slider.set_val(random_slot)


# ------------------------------------------------------------
# 4) Run the interactive visualizer
# ------------------------------------------------------------
if __name__ == "__main__":
    visualizer = SingleSymbolPPMVisualizer()
    plt.show()