
strategy_order = ["disabled", "tail-age", "eviction-rate", "hits", "lama", "marginal-hits", "marginal-hits-tuned"]
    

strategy_labels = {
    "disabled": r"$\mathit{Disabled}$",
    "tail-age": r"$\mathit{Tail\text{-}Age}$",
    "eviction-rate": r"$\mathit{Eviction\text{-}Rate}$",
    "hits": r"$\mathit{Hits\text{-}Per\text{-}Slab}$",
    "lama": r"$\mathit{LAMA}$",
    "marginal-hits": r"$\mathit{Marginal\text{-}Hits}$",
    "marginal-hits-tuned": r"$\mathit{Adaptive\text{-}Marginal\text{-}Hits}$"
}

strategy_colors = {
    "disabled": "#B0D5DE",
    "tail-age": "#FFDB99",
    "eviction-rate": "#FFBF47",
    "hits": "#CC8500",
    "lama": "#FB9489",
    "marginal-hits": "#11C0FB",
    "marginal-hits-tuned": "#3DB472"
}

# Define line styles for variety
strategy_linestyles = {
    "disabled": '-',
    "tail-age": '--',
    "eviction-rate": '-.',
    "hits": ':',
    "lama": (0, (3, 1, 1, 1)),
    "marginal-hits": '--',
    "marginal-hits-tuned": '-'
}

# Define marker styles
strategy_markers = {
    "disabled": 'o',
    "tail-age": 's',
    "eviction-rate": '^',
    "hits": 'D',
    "lama": 'v',
    "marginal-hits": 'p',
    "marginal-hits-tuned": 'H'  
}

# Define allocator order and labels
allocator_order = ['LRU', 'LRU2Q', 'TINYLFU']
allocator_labels = ['LRU', 'TwoQ', 'TinyLFU']

# Define markers and line styles for allocators
allocator_markers = {
    'LRU': 'o',
    'LRU2Q': 's', 
    'TINYLFU': '^'
}

allocator_linestyles = {
    'LRU': '-',
    'LRU2Q': '--',
    'TINYLFU': '-.'
}

# strategy_colors: Figs 9-11, strategy_colors_muted: Figs 7-8,
# strategy_colors_hatched (with strategy_hatches): Figs 1 and 4
strategy_colors_muted = {
    "disabled": "#B4B8BF",
    "tail-age": "#F5C05F",
    "eviction-rate": "#D49113",
    "hits": "#754D02",
    "lama": "#D9756A",
    "marginal-hits": "#07A6DB",
    "marginal-hits-tuned": "#297F4F"
}

strategy_colors_hatched = dict(strategy_colors, disabled="#D0D5DE")

strategy_hatches = {
    "disabled": "",
    "tail-age": "/",
    "eviction-rate": "\\",
    "hits": "x",
    "lama": "-",
    "marginal-hits": "+",
    "marginal-hits-tuned": "."
}

# legends are drawn separately by plot_legends.py
rcParams = {
    'font.size': 40,
    'axes.titlesize': 50,
    'axes.labelsize': 25,
    'xtick.labelsize': 25,
    'ytick.labelsize': 25,
    'legend.fontsize': 20,
    'figure.titlesize': 40,
    'figure.dpi': 300,
    'savefig.dpi': 300,
    'savefig.bbox': 'tight',
}
