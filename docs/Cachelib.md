# CacheLib Setup

## Repository Information

Our forked CacheLib repo: https://github.com/eth-easl/CacheLib

### Branches:
- `binary-trace-replay`
- `benchmark-4mb-slab`
- `benchmark-1mb-slab`
- `benchmark-tx`

## Branch Workflow

I use `binary-trace-replay` as the master branch. Usually I check out a local branch from it, make changes, push to `binary-trace-replay` and then merge `binary-trace-replay` into `benchmark-4mb-slab`, `benchmark-1mb-slab`, `benchmark-tx`.

## Branch Purposes

- **`benchmark-4mb-slab`**: Same as `binary-trace-replay`, uses 4MB slab size
- **`benchmark-1mb-slab`**: Changes the slab size in `Slab.h` to use 1MB slab size. We have two branches for the two slab sizes, as slab size is a const static variable that cannot be changed at runtime
- **`benchmark-tx`**: Contains the setups necessary for micro-benchmarking, counting CPU cycles

## Build Instructions

### Prerequisites
- Ubuntu 22.04
- sudo permission

### Install Dependencies
```bash
sudo apt-get update -y
sudo apt-get install python3-pip libglib2.0-dev -y
```

### Build CacheLib
```bash
git clone git@github.com:eth-easl/CacheLib.git
git checkout benchmark-4mb-slab
sudo ./contrib/build.sh -j -T
```

### Verify Build
```bash
./opt/cachelib/bin/cachebench --help
```

## Code Structure

`cachelib/allocator` contains most things we are interested in: eviction policies and slab rebalance strategies.

### Eviction Policies

- **MMLru** ([link](https://github.com/eth-easl/CacheLib/blob/benchmark-4mb-slab/cachelib/allocator/MMLru.h)): The original LRU implementation in CacheLib, but we don't use it because it has custom insertion point which breaks the stack property of LRU

- **MMSimple2Q** ([link](https://github.com/eth-easl/CacheLib/blob/benchmark-4mb-slab/cachelib/allocator/MMSimple2Q.h)): The LRU we've been using. It's called 2Q because there is a main queue and tail queue, marginal-hits needs the tail queue

- **MMSimple3Q** ([link](https://github.com/eth-easl/CacheLib/blob/benchmark-4mb-slab/cachelib/allocator/MMSimple3Q.h)): A version of LRU that has 3 queues: main queue, second-to-last tail queue and the tail queue. We don't use this anymore

- **MM2Q** ([link](https://github.com/eth-easl/CacheLib/blob/benchmark-4mb-slab/cachelib/allocator/MM2Q.h)):This is the real TwoQ implementation in CacheLib

- **MMTinyLFU** ([link](https://github.com/eth-easl/CacheLib/blob/benchmark-4mb-slab/cachelib/allocator/MMTinyLFU.h)): The original TinyLFU in CacheLib

- **MMTinyLFUTail** ([link](https://github.com/eth-easl/CacheLib/blob/benchmark-4mb-slab/cachelib/allocator/MMTinyLFUTail.h)): Our custom implementation, TinyLFU with tail queue supported. Marginal-hits needs this

### Slab Rebalance

**PoolRebalancer** ([link](https://github.com/eth-easl/CacheLib/blob/benchmark-4mb-slab/cachelib/allocator/PoolRebalancer.cpp)): This class extends the PeriodicWorker class, is the daemon thread that performs slab rebalance. The [`tryRebalancing`](https://github.com/eth-easl/CacheLib/blob/7bca76509beac8775db91ecba7c89129abbda02a/cachelib/allocator/PoolRebalancer.cpp#L149C7-L149C36) method is the entry point for triggering slab rebalance. It calls the configured slab rebalance strategy to pick victims and receivers and then perform the actual slab transfer.

### Rebalance Strategies

**Base Class:**
- **RebalanceStrategy** ([link](https://github.com/eth-easl/CacheLib/blob/benchmark-4mb-slab/cachelib/allocator/RebalanceStrategy.h)): The base class

**Strategy Implementations:**
- **FreeMem** ([link](https://github.com/eth-easl/CacheLib/blob/benchmark-4mb-slab/cachelib/allocator/FreeMemStrategy.h))
- **HitsPerSlab** ([link](https://github.com/eth-easl/CacheLib/blob/benchmark-4mb-slab/cachelib/allocator/HitsPerSlabStrategy.h))
- **LruTailAge** ([link](https://github.com/eth-easl/CacheLib/blob/benchmark-4mb-slab/cachelib/allocator/LruTailAgeStrategy.h))
- **EvictionRate** ([link](https://github.com/eth-easl/CacheLib/blob/benchmark-4mb-slab/cachelib/allocator/EvictionRateStrategy.h))
- **MarginalHits** ([link](https://github.com/eth-easl/CacheLib/blob/benchmark-4mb-slab/cachelib/allocator/MarginalHitsStrategyOld.h)): The `MarginalHitsStrategyOld` class represents the original marginal-hits in CacheLib
- **MarginalHitsTuned** ([link](https://github.com/eth-easl/CacheLib/blob/benchmark-4mb-slab/cachelib/allocator/MarginalHitsStrategyNew.h)): The `MarginalHitsStrategyNew` class

> **Note:** Ignore `MarginalHitsStrategy.h` as I made too many custom modifications to it and added too many knobs I don't even understand it anymore. Think of `MarginalHitsStrategyOld` as the original `MarginalHitsStrategy`.


### CacheBench

`cachelib/cachebench` can be considered as a standalone project that is used to benchmark CacheLib.

#### Usage

We can call it by providing the configurations in a JSON config file. I will have another doc explaining what each configuration means in the JSON config.

Configuration reference: [CacheConfig.h](https://github.com/eth-easl/CacheLib/blob/benchmark-4mb-slab/cachelib/cachebench/util/CacheConfig.h)

**Basic usage:**
```bash
./bin/cachebench --json_test_config test.json
```

**Additional flags:**

Add this flag if you want to see detailed debug logs:
```bash
--enable_debug_log=true
```

Configure this if you want to see fewer progress updates:
```bash
--progress=100000
```

**Timer configuration:**

Another tricky thing is timer. If you want to use the trace time instead of the wall clock time, we need to load a shared library, and in the JSON config file set `useTraceTime` to true (another doc will explain the config file in details):

```bash
LD_PRELOAD=/abs/path/libmock_time.so \
MOCK_TIMER_LIB_PATH=/abs/path/libmock_time.so \
./bin/cachebench --json_test_config test.json
```

The `libmock_time.so` library can be compiled from `set_up_env/hook_time/libmock_time.cpp`:
```bash
g++ -shared -fPIC -o libmock_time.so libmock_time.cpp -ldl
```

#### Modifications

Most modifications to CacheBench are to support reading binary formatted trace files, and we added many different knobs (as I made too many changes along the way, some of the knobs are no longer meaningful).

## Testing CacheLib with Trace Replay

Once you have successfully built CacheLib, you can test it by replaying a trace file. Follow these steps:

### Step 1: Download a Trace File

Download a sample trace file:
```bash
wget https://ftp.pdl.cmu.edu/pub/datasets/twemcacheWorkload/cacheDatasets/metaKV/202210_kv_traces_all_sort.csv.oracleGeneral.zst
```

### Step 2: Prepare Configuration File

Copy the `config.json` file from this directory to your machine. Make sure to update the `traceFileName` field in the configuration file to point to the location where you downloaded the trace file.

### Step 3: Run CacheBench

Execute CacheBench with the trace replay:
```bash
LD_PRELOAD=/abs/path/libmock_time.so \
MOCK_TIMER_LIB_PATH=/abs/path/libmock_time.so \
opt/cachelib/bin/cachebench --json_test_config config.json --progress=100000
```

**Note:** Make sure to replace the paths with the correct locations of your `libmock_time.so` library and `config.json` file. 



## rebuild
```bash
cd into build-cachelib/
sudo make -j 
sudo make install
```