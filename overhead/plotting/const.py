
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
    "disabled": "#636EFA",
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
allocator_order = ['LRU', 'TwoQ', 'TinyLFU']
allocator_labels = ['LRU', 'TwoQ', 'TinyLFU']

# Define markers and line styles for allocators
allocator_markers = {
    'LRU': 'o',
    'TwoQ': 's', 
    'TinyLFU': '^'
}

allocator_linestyles = {
    'LRU': '-',
    'TwoQ': '--',
    'TinyLFU': '-.'
}

rcParams = {
    'font.size': 40,
    'axes.titlesize': 50,
    'axes.labelsize': 40,
    'xtick.labelsize': 40,
    'ytick.labelsize': 30,
    'legend.fontsize': 20,     # Increased from 18
    'figure.titlesize': 40,
    'figure.dpi': 300,
    'savefig.dpi': 300,
    'savefig.bbox': 'tight',
    'axes.linewidth': 1.2,
    'grid.linewidth': 0.8,
    'grid.alpha': 0.3
}