"""Estilo común de los gráficos (paleta fija: el color sigue a la serie, nunca al orden)."""
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

C = {
    "azul": "#2a78d6", "naranja": "#eb6834", "aqua": "#1baf7a", "amarillo": "#eda100",
    "magenta": "#e87ba4", "verde": "#008300", "violeta": "#6250d6", "rojo": "#e34948",
}
TINTA, TINTA_2, TINTA_SUAVE = "#0b0b0b", "#52514e", "#898781"
REJILLA, EJE, FONDO = "#e1e0d9", "#c3c2b7", "#fcfcfb"
DIVERGENTE = LinearSegmentedColormap.from_list("divergente", [C["rojo"], "#f0efec", C["azul"]])


def aplicar_estilo():
    plt.rcParams.update({
        "figure.figsize": (12, 4.5), "figure.dpi": 110,
        "figure.facecolor": FONDO, "axes.facecolor": FONDO, "savefig.facecolor": FONDO,
        "axes.edgecolor": EJE, "axes.labelcolor": TINTA_2, "text.color": TINTA,
        "axes.titlesize": 12, "axes.titleweight": "bold", "axes.titlelocation": "left",
        "axes.titlecolor": TINTA, "axes.grid": True, "grid.color": REJILLA, "grid.linewidth": 0.6,
        "axes.spines.top": False, "axes.spines.right": False,
        "xtick.color": TINTA_SUAVE, "ytick.color": TINTA_SUAVE,
        "lines.linewidth": 1.4, "legend.frameon": False,
    })


def eje_años(ax, cada=2):
    """Eje X con un rótulo cada `cada` años."""
    ax.xaxis.set_major_locator(mdates.YearLocator(cada))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
