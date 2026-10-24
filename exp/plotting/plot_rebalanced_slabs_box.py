import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os
from const import (strategy_order, strategy_labels, strategy_colors, 
                   allocator_order, allocator_labels, rcParams)

def create_twitter_prod_boxplots(csv_file, output_dir=None, need_all_strategy=False):
    """
    Create box plots for Twitter production data showing number of rebalanced slabs.
    
    Args:
        csv_file (str): Path to the CSV file containing the data
        output_dir (str): Directory to save output plots. If None, uses current directory.
        need_all_strategy (bool): If True, only keep trace_names that have data for all 
                                 allocator and rebalance_strategy combinations for each WSR.
    """
    
    # Set output directory
    if output_dir is None:
        output_dir = os.getcwd()
    elif not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    
    # Read the CSV file
    df = pd.read_csv(csv_file)
    df = df[(df['trace_name'].str.startswith('twitter')) & (df['tag'] != 'warm-cold') & 
            df['rebalanced_slabs'].notna() & (df['rebalance_strategy'] != 'disabled')]
    
    # Set up matplotlib for publication quality
    plt.rcParams.update(rcParams)
    plt.rcParams.update({'axes.labelsize': 40, 'xtick.labelsize': 40,
                         'ytick.labelsize': 30})
    
    # Create plots for both WSR values
    wsr_values = [0.1, 0.01]
    
    for wsr in wsr_values:
        # Filter data for current WSR
        wsr_data = df[df['wsr'] == wsr].copy()
        
        if wsr_data.empty:
            print(f"No data found for WSR = {wsr}")
            continue
        
        # If need_all_strategy is True, filter to only keep traces with complete data
        if need_all_strategy:
            # Get all combinations that actually exist in the data for this WSR
            existing_combinations = set()
            for _, row in wsr_data.iterrows():
                combination = (row['allocator'], row['rebalance_strategy'])
                existing_combinations.add(combination)
            
            print(f"WSR {wsr}: Found {len(existing_combinations)} existing combinations: {existing_combinations}")
            
            # Find traces that have all existing combinations
            trace_combinations = {}
            for _, row in wsr_data.iterrows():
                trace_name = row['trace_name']
                combination = (row['allocator'], row['rebalance_strategy'])
                
                if trace_name not in trace_combinations:
                    trace_combinations[trace_name] = set()
                trace_combinations[trace_name].add(combination)
            
            # Keep only traces that have all existing combinations
            complete_traces = [trace for trace, combinations in trace_combinations.items() 
                             if combinations == existing_combinations]
            
            if not complete_traces:
                print(f"WSR {wsr}: No traces have data for all existing allocator-strategy combinations")
                # Print debug info
                print("Trace coverage:")
                for trace, combinations in trace_combinations.items():
                    missing = existing_combinations - combinations
                    print(f"  {trace}: {len(combinations)}/{len(existing_combinations)} combinations, missing: {missing}")
                continue
            
            wsr_data = wsr_data[wsr_data['trace_name'].isin(complete_traces)]
            print(f"WSR {wsr}: Filtered to {len(complete_traces)} complete traces: {complete_traces}")
        
        if wsr_data.empty:
            print(f"No data found for WSR = {wsr} after filtering")
            continue
        
        # Create figure - slightly narrower and taller for better proportions
        fig, ax = plt.subplots(figsize=(14,9.5))
        
        # Prepare data for box plots
        box_data = []
        box_labels = []
        box_colors = []
        positions = []
        mean_values = []  # Store mean values for triangle markers
        
        pos = 0
        
        for i, allocator in enumerate(allocator_order):
            allocator_data = wsr_data[wsr_data['allocator'] == allocator]
            
            if allocator_data.empty:
                print(f"WSR {wsr}: No data for {allocator}")
                continue
            
            print(f"WSR {wsr}, {allocator}: {len(allocator_data)} rows, strategies: {list(allocator_data['rebalance_strategy'].unique())}")
            
            # Add vertical separator line (except before first allocator)
            if i > 0:
                ax.axvline(x=pos - 0.5, color='gray', linestyle='--', alpha=0.5, linewidth=1)
            
            boxes_added = 0
            # Use strategy order from const.py (same for all allocators now)
            
            for strategy in strategy_order:
                strategy_data = allocator_data[allocator_data['rebalance_strategy'] == strategy]
                
                if not strategy_data.empty:
                    values = strategy_data['rebalanced_slabs'].values
                    print(f"  {strategy} values: min={values.min():.6f}, max={values.max():.6f}, mean={values.mean():.6f}")
                    
                    # Check for NaN values
                    if np.any(np.isnan(values)):
                        print(f"  WARNING: {strategy} has NaN values!")
                        continue
                    
                    box_data.append(values)
                    box_labels.append(f"{allocator_labels[i]}")
                    box_colors.append(strategy_colors[strategy])
                    positions.append(pos)
                    mean_values.append(values.mean())  # Store mean for triangle marker
                    pos += 1
                    boxes_added += 1
                    print(f"  Added box for {strategy}: {len(values)} values")
                else:
                    print(f"  No data for {strategy}")
            
            print(f"  Total boxes added for {allocator}: {boxes_added}")
            
            # Add larger spacing between allocators
            pos += 0.5
        
        # Create box plots with tighter spacing - academic style without outliers
        bp = ax.boxplot(box_data, positions=positions, patch_artist=True, 
                       widths=0.8, showfliers=False)  # Hide outliers for clean academic look
        
        # Color the boxes with full saturation (alpha=1)
        for patch, color in zip(bp['boxes'], box_colors):
            patch.set_facecolor(color)
            patch.set_alpha(1)  # Full saturation to match legend
            patch.set_edgecolor('black')
            patch.set_linewidth(1)
        
        # Add inverted triangle markers for mean values with outstanding color
        for i, (pos, mean_val, color) in enumerate(zip(positions, mean_values, box_colors)):
            ax.scatter(pos, mean_val, marker='v', s=110, color='red', 
                      edgecolors='black', linewidth=1.5, zorder=10)
        
        # Style other box plot elements
        for element in ['whiskers', 'fliers', 'medians', 'caps']:
            plt.setp(bp[element], color='black', linewidth=1.2)
        
        # Set x-axis labels - simplified approach
        allocator_positions = []
        allocator_display_labels = []
        
        # Calculate center position for each allocator that has data
        pos_idx = 0
        for i, allocator in enumerate(allocator_order):
            allocator_data = wsr_data[wsr_data['allocator'] == allocator]
            if allocator_data.empty:
                continue
                
            # Find positions for this allocator
            start_pos = pos_idx
            strategy_count = 0
            
            for strategy in strategy_order:
                strategy_data = allocator_data[allocator_data['rebalance_strategy'] == strategy]
                if not strategy_data.empty:
                    strategy_count += 1
                    pos_idx += 1
            
            if strategy_count > 0:
                # Calculate center position for this allocator's boxes
                center_pos = np.mean(positions[start_pos:start_pos + strategy_count])
                allocator_positions.append(center_pos)
                allocator_display_labels.append(allocator_labels[i])
        
        # Set x-axis ticks and labels
        ax.set_xticks(allocator_positions)
        ax.set_xticklabels(allocator_display_labels)
        ax.set_yscale('log')
        
        # Customize the plot
        ax.set_xlabel('Eviction Policy')
        ax.set_ylabel('# of Rebalanced Slabs')
        ax.grid(True, alpha=0.3, axis='y')
        
        # Create legend with matching saturation (alpha=1)
        legend_elements = []
        # Use strategy order from const.py
        strategies_in_data = set(wsr_data['rebalance_strategy'].unique())
        
        # Only include strategies that exist in the data
        for strategy in strategy_order:
            if strategy in strategies_in_data:
                legend_elements.append(plt.Rectangle((0,0),1,1, 
                                     facecolor=strategy_colors[strategy], 
                                     alpha=1, edgecolor='black',  # Match box alpha
                                     label=strategy_labels[strategy]))
        
        # Style the plot
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_linewidth(1.2)
        ax.spines['bottom'].set_linewidth(1.2)
        
        # Adjust layout to accommodate legend outside plot area
        plt.tight_layout()
        
        # Save to PDF in the specified output directory
        output_file = os.path.join(output_dir, f'twitter_prod_rebalanced_slabs_boxplot_wsr_{wsr:.2f}.pdf')
        plt.savefig(output_file, format='pdf', dpi=300, bbox_inches='tight',
                   facecolor='white', edgecolor='none')
        
        plt.show()
        print(f"Plot saved to: {output_file}")

# Example usage
if __name__ == "__main__":
    input_file = "../result/efficiency_result_processed.csv"
    output_dir = "figures/twitterKV"
    create_twitter_prod_boxplots(input_file, output_dir, need_all_strategy=True)