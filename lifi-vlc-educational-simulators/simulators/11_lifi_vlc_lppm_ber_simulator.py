from __future__ import annotations

import math
from typing import Iterable, Union

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Button, Slider

try:
    from scipy.special import erfc as _erfc
    ERFC_BACKEND = "scipy.special.erfc"
except ImportError:
    ERFC_BACKEND = "math.erfc + numpy.vectorize"

    def _erfc(x: Union[float, np.ndarray]) -> Union[float, np.ndarray]:
        x_array = np.asarray(x, dtype=float)
        vectorized_erfc = np.vectorize(math.erfc, otypes=[float])
        result = vectorized_erfc(x_array)

        if np.isscalar(x):
            return float(result)

        return result


# ============================================================
# Li-Fi / VLC L-PPM için etkileşimli teorik BER analizi
#
# Bu kod Monte Carlo BER simülasyonu değildir.
# Verilen analitik PPM BER ifadesini kullanarak SNR ve PPM
# mertebesi L'nin BER üzerindeki etkisini görselleştirir.
#
# BER_PPM = 1/2 * erfc( 1/(2*sqrt(2)) *
#                       sqrt( SNR * L/(2*log2(L)) ) )
# ============================================================


PPM_ORDERS = np.array([2, 4, 8, 16, 32], dtype=int)

SNR_DB_MIN = 0.0
SNR_DB_MAX = 40.0
SNR_DB_STEP = 0.1
SNR_DB_DEFAULT = 15.0

DEFAULT_L_INDEX = 1  # PPM_ORDERS[1] = 4

N_SNR_POINTS = 600

SNR_LINEAR_FLOOR = 1e-12
BER_FLOOR = 1e-20
BER_Y_MAX = 5e-1

SLIDER_FACE_COLOR = "#f5f2d0"


def validate_ppm_orders(ppm_orders: Union[int, Iterable[int], np.ndarray]) -> np.ndarray:
    orders = np.asarray(ppm_orders)

    if np.any(orders <= 1):
        raise ValueError("PPM order L must be greater than 1.")

    if not np.all(np.isclose(orders, np.round(orders))):
        raise ValueError("PPM order L must be an integer.")

    orders_int = np.asarray(np.round(orders), dtype=int)

    is_power_of_two = (orders_int & (orders_int - 1)) == 0
    if not np.all(is_power_of_two):
        raise ValueError(
            "PPM order L must be a power of two, e.g., 2, 4, 8, 16, 32."
        )

    return orders_int


def snr_db_to_linear(snr_db: Union[float, np.ndarray]) -> Union[float, np.ndarray]:
    snr_linear = 10.0 ** (np.asarray(snr_db, dtype=float) / 10.0)

    if np.isscalar(snr_db):
        return float(snr_linear)

    return snr_linear


def bits_per_symbol(ppm_order: Union[int, np.ndarray]) -> Union[float, np.ndarray]:
    orders = validate_ppm_orders(ppm_order)
    b = np.log2(orders)

    if np.isscalar(ppm_order):
        return float(b)

    return b


def compute_ppm_ber(
    snr_linear: Union[float, np.ndarray],
    ppm_order: Union[int, np.ndarray],
    ber_floor: float = BER_FLOOR,
) -> Union[float, np.ndarray]:

    snr_array = np.asarray(snr_linear, dtype=float)
    orders = validate_ppm_orders(ppm_order).astype(float)

    if np.any(snr_array < 0):
        raise ValueError("SNR must be non-negative in linear scale.")

    snr_safe = np.maximum(snr_array, SNR_LINEAR_FLOOR)

    ppm_factor = orders / (2.0 * np.log2(orders))
    erfc_argument = (1.0 / (2.0 * np.sqrt(2.0))) * np.sqrt(
        snr_safe * ppm_factor
    )

    ber = 0.5 * _erfc(erfc_argument)
    ber = np.maximum(ber, ber_floor)

    if np.isscalar(snr_linear) and np.isscalar(ppm_order):
        return float(np.asarray(ber).item())

    return ber


def configure_ber_axis(ax: plt.Axes, title: str, xlabel: str) -> None:
    ax.set_title(title, fontsize=12, fontweight="bold", pad=8)
    ax.set_xlabel(xlabel)
    ax.set_ylabel("Bit Error Rate, BER")
    ax.set_yscale("log")
    ax.set_ylim(BER_FLOOR, BER_Y_MAX)
    ax.grid(True, which="major", linestyle="-", linewidth=0.7, alpha=0.75)
    ax.grid(True, which="minor", linestyle=":", linewidth=0.5, alpha=0.45)


def create_interactive_ppm_ber_analysis() -> None:
    validate_ppm_orders(PPM_ORDERS)

    snr_db_values = np.linspace(SNR_DB_MIN, SNR_DB_MAX, N_SNR_POINTS)
    l_values = PPM_ORDERS.copy()

    initial_l = int(l_values[DEFAULT_L_INDEX])
    initial_snr_linear = snr_db_to_linear(SNR_DB_DEFAULT)

    initial_ber_vs_snr = compute_ppm_ber(
        snr_db_to_linear(snr_db_values),
        initial_l,
    )

    initial_ber_vs_l = compute_ppm_ber(
        initial_snr_linear,
        l_values,
    )

    initial_operating_ber = compute_ppm_ber(
        initial_snr_linear,
        initial_l,
    )

    fig, axes = plt.subplots(2, 1, figsize=(13.2, 9.2))

    try:
        fig.canvas.manager.set_window_title("Li-Fi / VLC L-PPM BER Analysis")
    except Exception:
        pass

    fig.suptitle(
        "Li-Fi / VLC Systems: Interactive Theoretical BER Analysis of L-PPM",
        fontsize=14,
        fontweight="bold",
    )

    # Alt kısım geniş bırakıldı. Slider, bilgi kutusu ve reset tuşu çakışmaz.
    plt.subplots_adjust(
        left=0.10,
        right=0.96,
        top=0.90,
        bottom=0.34,
        hspace=0.50,
    )

    # ------------------------------------------------------------
    # Grafik 1: BER vs SNR(dB)
    # ------------------------------------------------------------
    line_snr, = axes[0].plot(
        snr_db_values,
        initial_ber_vs_snr,
        linewidth=2.2,
        label="Theoretical BER curve",
    )

    point_snr, = axes[0].plot(
        [SNR_DB_DEFAULT],
        [initial_operating_ber],
        "o",
        markersize=8,
        color="red",
        label="Selected operating point",
    )

    configure_ber_axis(
        axes[0],
        "Theoretical L-PPM BER versus SNR",
        "SNR (dB)",
    )

    axes[0].set_xlim(SNR_DB_MIN, SNR_DB_MAX)
    axes[0].legend(loc="upper right")

    annotation_snr = axes[0].annotate(
        "",
        xy=(SNR_DB_DEFAULT, initial_operating_ber),
        xytext=(10, 12),
        textcoords="offset points",
        fontsize=8.5,
        bbox=dict(
            boxstyle="round,pad=0.25",
            facecolor="white",
            edgecolor="gray",
            alpha=0.88,
        ),
    )

    # ------------------------------------------------------------
    # Grafik 2: BER vs PPM order L
    # ------------------------------------------------------------
    line_l, = axes[1].plot(
        l_values,
        initial_ber_vs_l,
        linewidth=2.2,
        marker="o",
        label="Theoretical BER at selected SNR",
    )

    point_l, = axes[1].plot(
        [initial_l],
        [initial_operating_ber],
        "o",
        markersize=8,
        color="red",
        label="Selected operating point",
    )

    configure_ber_axis(
        axes[1],
        "Theoretical BER versus PPM Order L",
        "PPM order, L",
    )

    axes[1].set_xscale("log", base=2)
    axes[1].set_xticks(l_values)
    axes[1].set_xticklabels([str(value) for value in l_values])
    axes[1].legend(loc="upper right")

    annotation_l = axes[1].annotate(
        "",
        xy=(initial_l, initial_operating_ber),
        xytext=(10, 12),
        textcoords="offset points",
        fontsize=8.5,
        bbox=dict(
            boxstyle="round,pad=0.25",
            facecolor="white",
            edgecolor="gray",
            alpha=0.88,
        ),
    )

    # ------------------------------------------------------------
    # Kontrol paneli
    # ------------------------------------------------------------
    fig.text(0.10, 0.247, "Controls", fontsize=11, fontweight="bold")

    fig.text(0.10, 0.210, "SNR (dB)", fontsize=9.5, va="center")
    ax_snr_slider = fig.add_axes(
        [0.18, 0.190, 0.46, 0.035],
        facecolor=SLIDER_FACE_COLOR,
    )

    fig.text(0.10, 0.132, "PPM order L", fontsize=9.5, va="center")
    ax_l_slider = fig.add_axes(
        [0.18, 0.112, 0.46, 0.035],
        facecolor=SLIDER_FACE_COLOR,
    )

    # Bilgi kutusu ayrı axes içinde. Reset tuşunun üzerine taşmaz.
    ax_info = fig.add_axes([0.69, 0.105, 0.27, 0.145])
    ax_info.set_axis_off()

    info_text = ax_info.text(
        0.00,
        1.00,
        "",
        fontsize=9.0,
        va="top",
        ha="left",
        transform=ax_info.transAxes,
        bbox=dict(
            boxstyle="round,pad=0.45",
            facecolor="white",
            edgecolor="gray",
            alpha=0.96,
        ),
    )

    # Reset tuşu bilgi kutusundan ayrı ve güvenli bölgede.
    ax_reset = fig.add_axes([0.75, 0.045, 0.14, 0.045])

    snr_slider = Slider(
        ax=ax_snr_slider,
        label="",
        valmin=SNR_DB_MIN,
        valmax=SNR_DB_MAX,
        valinit=SNR_DB_DEFAULT,
        valstep=SNR_DB_STEP,
        valfmt="%0.1f",
    )

    l_slider = Slider(
        ax=ax_l_slider,
        label="",
        valmin=0,
        valmax=len(l_values) - 1,
        valinit=DEFAULT_L_INDEX,
        valstep=1,
        valfmt="%0.0f",
    )

    # Slider teknik olarak indeksle çalışır.
    # Ama kullanıcı doğrudan L değerlerini görür.
    ax_l_slider.set_xticks(np.arange(len(l_values)))
    ax_l_slider.set_xticklabels([str(value) for value in l_values], fontsize=8)

    reset_button = Button(
        ax_reset,
        "Reset",
        color="#eeeeee",
        hovercolor="#dceeff",
    )
    reset_button.label.set_fontweight("bold")

    def update(_event=None) -> None:
        snr_db = float(snr_slider.val)

        l_index = int(np.clip(round(l_slider.val), 0, len(l_values) - 1))
        current_l = int(l_values[l_index])

        snr_linear = float(snr_db_to_linear(snr_db))
        current_bits = float(bits_per_symbol(current_l))
        current_ber = float(compute_ppm_ber(snr_linear, current_l))

        ber_vs_snr = compute_ppm_ber(
            snr_db_to_linear(snr_db_values),
            current_l,
        )

        ber_vs_l = compute_ppm_ber(
            snr_linear,
            l_values,
        )

        line_snr.set_ydata(ber_vs_snr)
        point_snr.set_data([snr_db], [current_ber])

        line_l.set_ydata(ber_vs_l)
        point_l.set_data([current_l], [current_ber])

        annotation_snr.xy = (snr_db, current_ber)
        annotation_snr.set_text(
            f"L = {current_l}\n"
            f"BER = {current_ber:.2e}"
        )

        annotation_l.xy = (current_l, current_ber)
        annotation_l.set_text(
            f"SNR = {snr_db:.1f} dB\n"
            f"BER = {current_ber:.2e}"
        )

        # Slider göstergesinde indeks değil gerçek L değeri görünür.
        l_slider.valtext.set_text(f"L = {current_l}")

        info_text.set_text(
            "Selected operating point\n"
            f"SNR = {snr_db:.2f} dB\n"
            f"SNR(linear) = {snr_linear:.4g}\n"
            f"PPM order L = {current_l}\n"
            f"Bits/symbol b = {current_bits:.0f}\n"
            f"BER = {current_ber:.4e}\n\n"
            "Interpretation\n"
            "Higher SNR lowers BER.\n"
            "Larger L improves this ideal curve,\n"
            "but timing/bandwidth demand increases."
        )

        fig.canvas.draw_idle()

    def reset(_event=None) -> None:
        """
        Reset fonksiyonu düzeltildi.

        Slider.reset() yerine kontrollü set_val kullanılıyor.
        Böylece iki slider art arda resetlenirken gereksiz ara çizimler
        oluşmaz ve L göstergesi doğru şekilde güncellenir.
        """
        snr_slider.eventson = False
        l_slider.eventson = False

        snr_slider.set_val(SNR_DB_DEFAULT)
        l_slider.set_val(DEFAULT_L_INDEX)

        snr_slider.eventson = True
        l_slider.eventson = True

        update()

    snr_slider.on_changed(update)
    l_slider.on_changed(update)
    reset_button.on_clicked(reset)

    # Bazı Matplotlib backend'lerinde widget referansı korunmazsa
    # reset/slider tepkisiz kalabilir. Bu yüzden referanslar saklanır.
    fig._interactive_widgets = {
        "snr_slider": snr_slider,
        "l_slider": l_slider,
        "reset_button": reset_button,
    }

    update()
    plt.show()


if __name__ == "__main__":
    create_interactive_ppm_ber_analysis()