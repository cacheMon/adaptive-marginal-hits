# CacheBench Configuration

The configuration consists of two main parts:

## cache_config
Used to configure the cache instance.

### Basic Configuration
- **cacheSizeMB**: Total cache size. Note that some memory will be reserved for slab metadata. For example, if slab size is 4MB and you configure cache size as 8MB, there will only be 1 slab, as a small amount will be reserved for slab metadata. The amount of metadata overhead is related to the number of slabs. Detailed logic can be referenced [here](https://github.com/cacheMon/adaptive-marginal-hits/blob/59e5160dc3fb9031722cedddebf0a072110f9388/exp/prepare_exp_configs/gen_demo_config.py#L137).

- **moveOnSlabRelease**: Whether to enable move on slab releases. See [here](https://cachelib.org/docs/Cache_Library_Architecture_Guide/slab_rebalancing#3-how-do-we-maintain-strict-lru-ordering) for a detailed explanation. We haven't enabled this so far.

### Allocation Size Configuration
- **minAllocSize, maxAllocSize, allocFactor**: Size range grows exponentially by the allocation factor
- **allocSizes**: Alternatively, you can pass in an array of specific sizes

### Rebalancing Configuration
- **poolRebalanceIntervalSec**: This parameter has no effect, as we don't rely on wall clock time to trigger rebalancing
- **wakeUpRebalancerEveryXReqs**: This is the actual rebalance interval we use

### Eviction Policy Configuration
- **lruRefreshSec**: In current experiments we've been using 0. This is a throughput-related optimization but breaks the stack property of LRU. You can search for this in MMLru for more details.
- **allocator**: The eviction policy to use
- **rebalanceStrategy**: The rebalance strategy to use

For rebalance strategy-specific parameters, see [here](https://github.com/eth-easl/CacheLib/blob/da2dcafd0601fa104a24bd07dae0bb0720001fcb/cachelib/cachebench/util/CacheConfig.cpp#L196).

## test_config
Used to configure the cache stressor.

### Generator Configuration
- **generator**: Which generator to generate workloads. There are some other workload generators in cachebench, but we only use `"oracle-general-replay"`.
- **useTraceTimer**: If true, use trace time instead of wall clock time. When enabling this, remember to pass the environment variable: `MOCK_TIMER_LIB_PATH="libmock_time.so" ./bin/cachebench` and also `LD_PRELOAD`.

### Thread and Request Configuration
- **numThreads**: Number of concurrent threads (we've been using 1)
- **ignoreLargeReq**: Whether to ignore requests larger than the slab size. We use `true` since the current code doesn't handle chained allocation.
- **traceFileName**: Absolute path to the trace file
- **numOps**: Number of operations. It's okay to set this to an infinitely large value, as CacheBench will automatically stop when the trace file's EOF is reached.

### Trace File Format
- **zstdTrace** and **compressed**:
  - If `zstdTrace` is `false`: Treats the trace file as a CSV file (uncompressed)
  - If `zstdTrace` is `true` and `compressed` is `true`: Binary trace file that is zstd compressed
  - If `zstdTrace` is `true` and `compressed` is `false`: Binary trace file without compression

**Note:** The `zstdTrace` parameter name is misleading; it should have been named `binaryTrace`.

numOps: number of operations, it's okay to set to an infinite large value, as when the trace file's EOF is reached cachebenh will automatically stop