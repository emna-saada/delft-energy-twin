"""Shared visual identity (dashboard, maps, report, video)."""

INK = "#0F2A33"
PETROL = "#0E5E6F"
TEAL = "#12808F"
SAND = "#F6F4EF"
CARD = "#FFFFFF"
MUTED = "#5B6B70"
BORDER = "#E3E0D8"
AMBER = "#D97706"

# Hazard identity colours (distinct hue + lightness, readable on white)
HAZARD_COLORS = {"heat": "#D1495B", "drought": "#B7791F", "flood": "#2B6CB0", "fire": "#7B2D5B"}
HAZARD_LABELS = {"heat": "Chaleur extrême", "drought": "Sécheresse", "flood": "Inondation", "fire": "Feux de forêt"}

# Sequential risk scale, low -> high (perceptually ordered, colour-blind friendly endpoints)
RISK_SCALE = ["#FFF4D6", "#FDD58A", "#F7A456", "#E2683C", "#B8323B", "#6E1434"]

PERIOD_ORDER = ["baseline", "ssp245_2030", "ssp245_2050", "ssp585_2030", "ssp585_2050"]
SCENARIO_COLORS = {"baseline": "#7A8B8F", "ssp245": TEAL, "ssp585": "#B8323B"}

FONT_UI = "Fira Sans"
FONT_NUM = "Fira Code"


def mpl_style() -> None:
    import matplotlib as mpl

    mpl.rcParams.update({
        "font.family": "DejaVu Sans", "font.size": 10, "axes.edgecolor": BORDER,
        "axes.labelcolor": INK, "xtick.color": MUTED, "ytick.color": MUTED,
        "axes.spines.top": False, "axes.spines.right": False, "figure.dpi": 150,
        "savefig.bbox": "tight", "axes.titleweight": "bold", "axes.titlecolor": INK,
        "axes.titlesize": 11, "axes.titlelocation": "left",
    })


def risk_cmap():
    from matplotlib.colors import LinearSegmentedColormap

    return LinearSegmentedColormap.from_list("climarisk", RISK_SCALE)
