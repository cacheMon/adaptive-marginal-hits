import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os
from pathlib import Path
from const import (strategy_order, strategy_labels, strategy_colors,
                   strategy_colors_muted, strategy_colors_hatched, strategy_hatches,
                   allocator_order, allocator_labels, rcParams)

CDN_BAR_RC = {'axes.labelsize': 50, 'xtick.labelsize': 45, 'ytick.labelsize': 35}

def plot_cdn_bars(trace_name, csv_file, output_dir=None, wsr=None):
    """
    Plot bar chart of miss ratios for different allocators and rebalance strategies.
    Creates one bar plot per trace_name with allocators on x-axis and strategies as colored bars.
    
    Parameters:
    trace_name (str): The trace name to filter the data
    csv_file (str): Path to the CSV file containing the data
    output_dir (str): Directory to save output plots. If None, uses current directory.
    """
    
    # Set output directory
    if output_dir is None:
        output_dir = os.getcwd()
    elif not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    
    # Read the data
    df = pd.read_csv(csv_file)
    
    # Filter by trace_name
    df_filtered = df[df['trace_name'] == trace_name].copy()
    if wsr is not None:
        df_filtered = df_filtered[df_filtered['wsr'] == wsr]
    
    if df_filtered.empty:
        print(f"No data found for trace_name: {trace_name}")
        return
    
    # Set up matplotlib for publication quality
    plt.rcParams.update(rcParams)
    plt.rcParams.update(CDN_BAR_RC)
    
    # Create the bar plot
    fig, ax = plt.subplots(figsize=(16, 8), constrained_layout=True)
    
    # Get unique strategies in this data and order them
    available_strategies = df_filtered['rebalance_strategy'].unique()
    strategies = [s for s in strategy_order if s in available_strategies]
    
    # Set up bar positions
    x_positions = np.arange(len(allocator_order))
    
    # For each allocator, determine which strategies have data
    allocator_strategies = {}
    for allocator in allocator_order:
        allocator_strategies[allocator] = []
        for strategy in strategies:
            strategy_data = df_filtered[df_filtered['rebalance_strategy'] == strategy]
            allocator_data = strategy_data[strategy_data['allocator'] == allocator]
            if not allocator_data.empty:
                allocator_strategies[allocator].append(strategy)
    
    # Plot bars for each strategy
    legend_elements = []  # Track legend elements to avoid duplicates
    
    for strategy in strategies:
        strategy_data = df_filtered[df_filtered['rebalance_strategy'] == strategy]
        
        if strategy_data.empty:
            continue
        
        # Get styling
        color = strategy_colors_muted.get(strategy, '#000000')
        label = strategy_labels.get(strategy, strategy)
        
        # Track if we've added this strategy to legend
        strategy_added_to_legend = False
        
        # Plot bars for each allocator where this strategy has data
        for j, allocator in enumerate(allocator_order):
            allocator_data = strategy_data[strategy_data['allocator'] == allocator]
            
            if not allocator_data.empty:
                miss_ratio = allocator_data['miss_ratio'].mean()
                
                # Calculate bar position based on strategies available for this allocator
                strategies_for_allocator = allocator_strategies[allocator]
                n_strategies = len(strategies_for_allocator)
                bar_width = 0.8 / n_strategies
                
                # Find the index of this strategy within the available strategies for this allocator
                strategy_index = strategies_for_allocator.index(strategy)
                bar_position = x_positions[j] + (strategy_index - n_strategies/2 + 0.5) * bar_width
                
                # Plot the bar
                bar = ax.bar(bar_position, miss_ratio, bar_width,
                           color=color,
                           edgecolor='black', linewidth=1)
                
                # Add to legend elements only once per strategy
                if not strategy_added_to_legend:
                    legend_elements.append(plt.Rectangle((0,0),1,1, facecolor=color, edgecolor='black', linewidth=1, label=label))
                    strategy_added_to_legend = True
    
    # Customize the plot
    ax.set_xlabel('Eviction Policy')
    ax.set_ylabel('Miss Ratio')
    ax.set_xticks(x_positions)
    ax.set_xticklabels(allocator_labels)
    ax.grid(True, alpha=0.3, axis='y')
    
    # Add vertical dashed lines between different eviction policies
    for i in range(len(allocator_order) - 1):
        # Position the line between allocator groups
        line_x = x_positions[i] + 0.5
        ax.axvline(x=line_x, color='gray', linestyle='--', alpha=0.7, linewidth=1)
    
    # Save the figure in the specified output directory
    output_path = os.path.join(output_dir, f"cdn_bars_{str(wsr)}_miss_ratio_{trace_name}.pdf")
    plt.savefig(output_path, bbox_inches='tight')
    plt.close()
    
    print(f"Saved plot for {trace_name}: {output_path}")



def plot_strategy_vs_eviction_bars(trace_name, csv_file, output_path, wsr=0.01,
                                   figsize=(10.06, 4.85)):
    """Fig 1: miss ratio of every strategy under each eviction algorithm, for one trace and cache size."""
    df = pd.read_csv(csv_file)
    df = df[(df['trace_name'] == trace_name) & (df['wsr'] == wsr)]
    if df.empty:
        print(f"No data for {trace_name} at wsr={wsr}")
        return

    plt.rcParams.update(rcParams)
    plt.rcParams.update({'axes.labelsize': 27, 'xtick.labelsize': 25,
                         'ytick.labelsize': 25, 'hatch.linewidth': 1.0})

    strategies = [s for s in strategy_order if s in set(df['rebalance_strategy'])]
    group_width = 0.9
    bar_width = group_width / len(strategies)
    x = np.arange(len(allocator_order))

    fig, ax = plt.subplots(figsize=figsize)
    for k, strategy in enumerate(strategies):
        offs = (k - len(strategies) / 2 + 0.5) * bar_width
        for j, allocator in enumerate(allocator_order):
            sel = df[(df['rebalance_strategy'] == strategy) & (df['allocator'] == allocator)]
            if sel.empty:
                continue
            ax.bar(x[j] + offs, sel['miss_ratio'].mean(), bar_width,
                   color=strategy_colors_hatched[strategy],
                   hatch=strategy_hatches[strategy],
                   edgecolor='#444444', linewidth=1)

    ax.set_xticks(x)
    ax.set_xticklabels(allocator_labels)
    ax.set_xlabel('Eviction Algorithm')
    ax.set_ylabel('Miss Ratio')
    ax.yaxis.set_major_locator(plt.MultipleLocator(0.025))
    ax.yaxis.set_major_formatter(plt.FormatStrFormatter('%.3f'))
    ax.grid(True, alpha=0.3, axis='y')
    ax.set_axisbelow(True)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
    fig.savefig(output_path, bbox_inches='tight')
    plt.close(fig)
    print(f"Saved Figure 1 for {trace_name}: {output_path}")


def plot_all_cdn_traces(csv_file, output_dir=None):
    """Plot bar charts for all CDN trace names
    
    Parameters:
    csv_file (str): Path to the CSV file containing the data
    output_dir (str): Directory to save output plots. If None, uses current directory.
    """
    trace_names = [
        'wiki_2019u',
        'wiki_2016u',
        'wiki_2019t'
    ]
    
    for trace_name in trace_names:
        plot_cdn_bars(trace_name, csv_file, output_dir, wsr=0.01)

    print(f"\nCreated bar plots for {len(trace_names)} CDN traces")

if __name__ == "__main__":
    csv_file = "../result/efficiency_result_processed.csv"
    output_dir = "figures/cdn_bars"
    plot_all_cdn_traces(csv_file, output_dir)
    plot_strategy_vs_eviction_bars('meta_202210_kv', csv_file,
                                   'figures/metaKV/rebalance_strategy_vs_eviction_alg_bar_202210.pdf', wsr=0.01)