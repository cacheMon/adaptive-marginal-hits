# Result Schema

The miss ratio benchmarking results are available at: [efficiency_result_processed.csv](https://github.com/cacheMon/adaptive-marginal-hits/blob/main/exp/result/efficiency_result_processed.csv)

## Configuration Fields

- **trace_name**: Name of trace (e.g., `twitter_cluster25`, `meta_202210_kv`)
- **category**: Category of the trace, e.g. meta-kv, meta-cdn, twitter-kv, wiki-cdn
- **wsr**: Working set ratio
- **slab_size**: 1 or 4 MB
- **slab_cnt**: Total memory in units of slabs
- **rebalance_strategy**: Rebalance strategy used
- **allocator**: Eviction policy
- **tag**: Only relevant for TwoQ + marginal-hits or marginal-hits-tuned
  - `cold-only`: Use only cold tail hits (now we only use this version)
  - `warm-cold`: Use weighted average of warm + cold tail hits
- **monitor_interval**: Rebalance interval (how often pool rebalancer runs, in number of requests)

### Trace Metadata
- **compulsory_miss_ratio_req**
- **wss**
- **number_of_req_GiB**
- **number_of_obj_GiB**
- **number_of_objects**
- **qps**
- **compulsory_miss_ratio_byte**
- **number_of_requests**

## Result Fields

### Miss Ratio Metrics
- **miss_ratio**: Miss ratio
- **miss_ratio_reduction_from_disabled**: Delta from same eviction policy without rebalancing
- **miss_ratio_percent_reduction_from_disabled**: Percentage reduction from disabled baseline
- **miss_ratio_reduction_from_lru_disabled**: Delta from LRU without rebalancing
- **miss_ratio_percent_reduction_from_lru_disabled**: Percentage reduction from LRU disabled baseline

- **tuned_improvement**: Only for marginal-hits-tuned; delta from marginal-hits baseline
- **tuned_percent_improvement**: Percentage improvement over marginal-hits

### Others
- **rebalanced_slabs**: Number of rebalanced slabs
- **throughput**: Operations per second
- **n_alloc_failures**: Number of allocation failures