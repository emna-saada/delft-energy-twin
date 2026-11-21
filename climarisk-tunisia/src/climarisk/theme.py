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
# Validated with the dataviz palette checker (light surface): lightness band, chroma, CVD; heat/drought and
# flood/fire sit in the 6-8 CVD floor band, so every use carries direct labels.
HAZARD_COLORS = {"heat": "#D1495B", "drought": "#C98500", "flood": "#2A78D6", "fire": "#8E44AD"}
HAZARD_LABELS = {"heat": "Chaleur extrême", "drought": "Sécheresse", "flood": "Inondation", "fire": "Feux de forêt"}

# Sequential risk scale, low -> high (perceptually ordered, colour-blind friendly endpoints)
RISK_SCALE = ["#FFF4D6", "#FDD58A", "#F7A456", "#E2683C", "#B8323B", "#6E1434"]

PERIOD_ORDER = ["baseline", "ssp245_2030", "ssp245_2050", "ssp585_2030", "ssp585_2050"]
# SSP2-4.5 / SSP5-8.5 pass all checks; "today" is a neutral reference grey, always direct-labelled.
SCENARIO_COLORS = {"baseline": "#A3ACAE", "ssp245": "#008C9E", "ssp585": "#C2343F"}

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
