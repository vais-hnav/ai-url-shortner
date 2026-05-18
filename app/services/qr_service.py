from html import escape

import qrcode
from qrcode.constants import ERROR_CORRECT_H


QR_THEMES = {
    "ember": {
        "page": "#090909",
        "surface": "#17130f",
        "qr_bg": "#fffaf0",
        "module": "#11110e",
        "accent": "#ff4d2e",
        "accent_2": "#ffb000",
        "muted": "#b9b3a7",
    },
    "lime": {
        "page": "#080908",
        "surface": "#11140e",
        "qr_bg": "#fbfff0",
        "module": "#10140d",
        "accent": "#d8ff4f",
        "accent_2": "#72f7a4",
        "muted": "#b8c2aa",
    },
    "violet": {
        "page": "#0b090f",
        "surface": "#171220",
        "qr_bg": "#fffaff",
        "module": "#120f18",
        "accent": "#c084fc",
        "accent_2": "#f0abfc",
        "muted": "#c7b9d8",
    },
    "mono": {
        "page": "#080808",
        "surface": "#151515",
        "qr_bg": "#ffffff",
        "module": "#111111",
        "accent": "#ffffff",
        "accent_2": "#9b9b9b",
        "muted": "#b8b8b8",
    },
}

QR_EFFECTS = {"glow", "soft", "poster", "minimal"}


def _normalize_option(value: str, allowed: set[str] | dict[str, object], fallback: str) -> str:
    normalized = value.strip().lower()
    return normalized if normalized in allowed else fallback


def create_branded_qr_svg(
    *,
    short_url: str,
    short_code: str,
    theme: str = "ember",
    effect: str = "glow",
    label: str | None = None,
) -> str:
    selected_theme = _normalize_option(theme, QR_THEMES, "ember")
    selected_effect = _normalize_option(effect, QR_EFFECTS, "glow")
    colors = QR_THEMES[selected_theme]
    display_label = (label or f"AI URL Shortner / {short_code}").strip()[:72]

    qr = qrcode.QRCode(error_correction=ERROR_CORRECT_H, border=4, box_size=1)
    qr.add_data(short_url)
    qr.make(fit=True)
    matrix = qr.get_matrix()

    view_width = 960
    view_height = 1120
    qr_size = 720
    qr_x = 120
    qr_y = 120
    module_count = len(matrix)
    module_size = qr_size / module_count
    module_radius = module_size * (0.34 if selected_effect != "minimal" else 0.08)

    module_rects: list[str] = []
    for row_index, row in enumerate(matrix):
        for col_index, is_dark in enumerate(row):
            if not is_dark:
                continue
            x = qr_x + col_index * module_size
            y = qr_y + row_index * module_size
            module_rects.append(
                (
                    f'<rect x="{x:.3f}" y="{y:.3f}" '
                    f'width="{module_size + 0.02:.3f}" height="{module_size + 0.02:.3f}" '
                    f'rx="{module_radius:.3f}" ry="{module_radius:.3f}" />'
                )
            )

    glow_filter = ""
    if selected_effect == "glow":
        glow_filter = """
        <filter id="qrGlow" x="-30%" y="-30%" width="160%" height="160%">
          <feGaussianBlur stdDeviation="10" result="blur" />
          <feColorMatrix in="blur" type="matrix" values="1 0 0 0 1 0 0.45 0 0 0.24 0 0 0.16 0 0.08 0 0 0 0.55 0" result="glow" />
          <feMerge>
            <feMergeNode in="glow" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
        """

    poster_marks = ""
    if selected_effect == "poster":
        poster_marks = f"""
        <path d="M70 190 H32 V72 H190 V110 H70 Z" fill="{colors['accent']}" opacity="0.95" />
        <path d="M890 930 H928 V1048 H770 V1010 H890 Z" fill="{colors['accent_2']}" opacity="0.9" />
        <circle cx="820" cy="182" r="46" fill="{colors['accent']}" opacity="0.18" />
        <circle cx="146" cy="936" r="62" fill="{colors['accent_2']}" opacity="0.14" />
        """

    soft_texture = ""
    if selected_effect in {"glow", "soft"}:
        soft_texture = f"""
        <circle cx="156" cy="148" r="180" fill="{colors['accent']}" opacity="0.18" />
        <circle cx="806" cy="910" r="230" fill="{colors['accent_2']}" opacity="0.14" />
        <path d="M82 884 C270 760 408 1040 624 890 C762 794 796 690 904 704" fill="none" stroke="{colors['accent']}" stroke-width="3" opacity="0.24" />
        """

    module_filter = ' filter="url(#qrGlow)"' if selected_effect == "glow" else ""
    escaped_short_url = escape(short_url)
    escaped_short_code = escape(short_code)
    escaped_label = escape(display_label)

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{view_width}" height="{view_height}" viewBox="0 0 {view_width} {view_height}" role="img" aria-label="Branded QR code for {escaped_short_code}">
  <defs>
    <linearGradient id="pageGradient" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="{colors['surface']}" />
      <stop offset="54%" stop-color="{colors['page']}" />
      <stop offset="100%" stop-color="{colors['surface']}" />
    </linearGradient>
    <linearGradient id="accentGradient" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="{colors['accent']}" />
      <stop offset="100%" stop-color="{colors['accent_2']}" />
    </linearGradient>
    {glow_filter}
  </defs>
  <rect width="960" height="1120" rx="54" fill="url(#pageGradient)" />
  {soft_texture}
  {poster_marks}
  <rect x="86" y="86" width="788" height="788" rx="48" fill="{colors['qr_bg']}" />
  <rect x="96" y="96" width="768" height="768" rx="42" fill="none" stroke="url(#accentGradient)" stroke-width="3" opacity="0.72" />
  <g fill="{colors['module']}"{module_filter}>
    {''.join(module_rects)}
  </g>
  <rect x="96" y="914" width="768" height="128" rx="30" fill="{colors['surface']}" opacity="0.94" stroke="{colors['accent']}" stroke-opacity="0.28" />
  <text x="132" y="962" fill="{colors['accent_2']}" font-family="Inter, Arial, sans-serif" font-size="26" font-weight="800">AI URL Shortner</text>
  <text x="132" y="1002" fill="{colors['muted']}" font-family="Inter, Arial, sans-serif" font-size="22" font-weight="600">{escaped_label}</text>
  <text x="132" y="1074" fill="{colors['muted']}" font-family="Inter, Arial, sans-serif" font-size="18">{escaped_short_url}</text>
</svg>"""

