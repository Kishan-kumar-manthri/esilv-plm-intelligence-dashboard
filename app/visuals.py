"""Conceptual product visuals derived from PLM metadata.

The export contains no CAD or geometry files. These diagrams are therefore
navigation aids, not representations of the OEM geometry.
"""

from html import escape


def product_svg(product, child_count: int = 0) -> str:
    name = product.name.lower()
    if "edrive" in name or "emotor" in name or "reducer" in name:
        shape = (
            '<circle cx="200" cy="145" r="80" fill="#e6f4fb" stroke="#0877b8" stroke-width="3"/>'
            '<circle cx="200" cy="145" r="42" fill="#ffffff" stroke="#1469a8" stroke-width="3"/>'
            '<path d="M200 45v35M200 210v35M100 145h35M265 145h35" stroke="#0877b8" stroke-width="8" stroke-linecap="round"/>'
        )
    elif any(term in name for term in ("gear", "shaft", "pin")):
        shape = (
            '<circle cx="200" cy="145" r="68" fill="#e6f4fb" stroke="#0877b8" stroke-width="3"/>'
            '<circle cx="200" cy="145" r="25" fill="#ffffff" stroke="#1469a8" stroke-width="3"/>'
            '<path d="M200 62v35M200 193v35M117 145h35M248 145h35" stroke="#0877b8" stroke-width="14"/>'
        )
    elif any(term in name for term in ("housing", "casing", "plate", "support")):
        shape = '<path d="M92 205V95l45-32h126l45 32v110l-45 32H137z" fill="#e6f4fb" stroke="#0877b8" stroke-width="3"/><circle cx="200" cy="150" r="42" fill="#ffffff" stroke="#1469a8" stroke-width="3"/>'
    elif any(term in name for term in ("bearing", "bea")):
        shape = '<circle cx="200" cy="145" r="78" fill="#e6f4fb" stroke="#0877b8" stroke-width="3"/><circle cx="200" cy="145" r="43" fill="#ffffff" stroke="#1469a8" stroke-width="3"/><circle cx="200" cy="145" r="15" fill="#0877b8"/>'
    elif any(term in name for term in ("screw", "bolt", "pipe", "joint")):
        shape = '<rect x="110" y="115" width="180" height="60" rx="28" fill="#e6f4fb" stroke="#0877b8" stroke-width="3"/><path d="M145 115v60M175 115v60M205 115v60M235 115v60" stroke="#1469a8" stroke-width="3"/>'
    else:
        shape = '<rect x="112" y="76" width="176" height="140" rx="16" fill="#e6f4fb" stroke="#0877b8" stroke-width="3"/><path d="M145 112h110M145 145h75M145 178h95" stroke="#1469a8" stroke-width="5" stroke-linecap="round"/>'
    label = escape(product.name[:34])
    return (
        '<div style="background:#f7faff;border:1px solid #dce5ef;border-radius:16px;padding:12px">'
        f'<svg viewBox="0 0 400 285" width="100%" role="img" aria-label="Conceptual schematic for {label}">'
        f'<text x="20" y="25" fill="#6b8194" font-family="DM Sans" font-size="12">CONCEPTUAL PLM SCHEMATIC</text>'
        f'{shape}<text x="200" y="270" text-anchor="middle" fill="#16324a" font-family="DM Sans" font-size="13">{label}</text>'
        '</svg><div class="visual-note">Visual aid only • XML contains no OEM geometry file</div></div>'
    )
