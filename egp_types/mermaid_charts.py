"""Mermaid charts for EGP types."""

# Mermaid chart constants
MERMAID_IGRAPH_COLORS: dict[str, dict[str, str]] = {
    "I": {"fill": "#999", "link": "#CCC"},
    "C": {"fill": "#444", "link": "#666"},
    "A": {"fill": "#900", "link": "#C66"},
    "B": {"fill": "#009", "link": "#66C"},
    "O": {"fill": "#000", "link": "#000"},
    "P": {"fill": "#090", "link": "#6C6"},
    "F": {"fill": "#099", "link": "#6CC"},
    "U": {"fill": "#990", "link": "#CC6"},
    "W": {"fill": "#518", "link": "#A2F"},
}
MERMAID_IGRAPH_CLASS_DEF_STR: str = (
    f"classDef Iclass fill:{MERMAID_IGRAPH_COLORS['I']['fill']},stroke:#333,stroke-width:4px\n"
    f"classDef Cclass fill:{MERMAID_IGRAPH_COLORS['C']['fill']},stroke:#333,stroke-width:4px\n"
    f"classDef Fclass fill:{MERMAID_IGRAPH_COLORS['F']['fill']},stroke:#333,stroke-width:4px\n"
    f"classDef Aclass fill:{MERMAID_IGRAPH_COLORS['A']['fill']},stroke:#333,stroke-width:4px\n"
    f"classDef Bclass fill:{MERMAID_IGRAPH_COLORS['B']['fill']},stroke:#333,stroke-width:4px\n"
    f"classDef Oclass fill:{MERMAID_IGRAPH_COLORS['O']['fill']},stroke:#333,stroke-width:4px\n"
    f"classDef Pclass fill:{MERMAID_IGRAPH_COLORS['P']['fill']},stroke:#333,stroke-width:4px\n"
    f"classDef Wclass fill:{MERMAID_IGRAPH_COLORS['W']['fill']},stroke:#333,stroke-width:4px\n"
)
