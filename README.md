# slab-rebalance-bench

Benchmark harness for the paper **"Demystifying and Optimizing Slab Rebalance in Memory Caches"** (Adaptive-Marginal-Hits). It replays production cache traces through a forked [CacheLib](https://github.com/eth-easl/CacheLib) `cachebench` binary under different slab-rebalance strategies, collects miss ratio / slab-movement / CPU-overhead metrics, and plots the paper figures.

A detailed walkthrough of the distributed setup is in [docs/Miss ratio bench mark set up.md](docs/Miss%20ratio%20bench%20mark%20set%20up.md).

---

## Two ways to reproduce

| | What it needs | Time | Reproduces |
|---|---|---|---|
| **A. Re-plot from shipped results** | Python + the CSVs already committed in `exp/result/` | minutes | The figures, from the exact numbers used in the paper |
| **B. Run experiments from scratch** | CacheLib built + trace files + compute | hours–days (depends on cluster size) | The raw numbers, then the figures |

You can start with **Path A** to confirm the plotting works and to see the main results immediately. Use **Path B** to regenerate the data.
---

## Path A — Re-plot the paper figures from shipped data

The repo commits the result CSVs the paper was plotted from, so you can regenerate every figure without CacheLib or traces.

```bash
pip install pandas matplotlib numpy seaborn
bash replot_results.sh                         # plots everything
```

`replot_results.sh` (at the repo root) runs all the plotting scripts and writes the PDFs into `exp/plotting/figures/`.

---

## Path B — Run experiments from scratch

**Prerequisites:** a machine (or cluster) running **Ubuntu 22.04**, with `sudo` permission and enough disk for the traces. For a cluster, the machines share a directory (NFS or equivalent); one machine is the **master**, the rest are **workers**.

You can either try running:
- **[Single-machine test run](#single-machine-test-run--fastest)** the fastest way to verify the whole pipeline, we provide a small run that finishes quickly.
- **[Full cluster run](#full-cluster-run--the-papers-setup)** — the paper's 4-node cluster, for regenerating the full results.

### Single-machine test run — fastest

This script builds cachelib, generate configs, download the trace, run the experiment, and summarize.
```bash
# 1. Point the harness at THIS machine (writes hosts/*, exp/configs.json, makes /users/<you>).
#    Traces are stored under $HOME/adaptive-mh-traces (the demo trace is ~7 GB).
bash set_up_env/setup_local.sh

# 2. Build the forked CacheLib (v1 = 4 MB slabs, for Meta/CDN; v2 = 1 MB slabs, for Twitter). ~30–60 min.
bash set_up_env/build_cachelib.sh                 # add --variant both to also build v2

# 3. Run the miss-ratio experiment. Start with --smoke (a few minutes).
bash reproduce_miss_ratio.sh --smoke              # LRU, one cache size, numOps capped
```

`reproduce_miss_ratio.sh` generates configs, downloads the trace, runs `cachebench` on every generated config, summarizes, and prints a miss-ratio table. Options:

| Flag | Meaning |
|---|---|
| `--dataset demo\|meta\|cdn\|twitter` | which sample to run (default `demo` = `meta_202210_kv`; `twitter` needs the `v2` build) |
| `--smoke` | tiny subset (LRU only, one WSR) + capped `numOps` so it finishes in minutes |
| `--numops N` / `--wsr "0.01 0.1"` | change the op count / working-set ratio for the smoke run |
| `--jobs J` | run J cachebench jobs concurrently |
| `--replot` | copy the result into `exp/result/` and run `replot_results.sh` (Path A) |

Drop `--smoke` to run the full trace. Smoke numbers use a small `numOps` slice, so they prove the pipeline rather than reproducing the exact paper values.

### Full cluster run — the paper's setup

The paper uses a **4-node cluster (1 master + 3 workers)**; we used CloudLab. The scheduler `exp/master/master.py` bin-packs jobs across hosts by CPU/memory, downloads/removes traces on demand, and resumes from where it left off if a node fails.

#### Set up the environment

- Clone this repo to your **local** machine.
- Configure the machine list. Inside `hosts/`, there are two files:
  - `hosts.txt` — the host list, one `user@host` per line (**the first host is the master**).
  - `username.txt` — your Linux username.
- Then run, from your local machine:
  ```bash
  cd set_up_env && /bin/bash host_init.sh
  ```
  This distributes SSH keys and builds CacheLib (`cachelib_v1` and `cachelib_v2`) on every host.

#### Launch Experiments

1. **SSH into the master node.**

2. **Set up the repository on the master node:**
   - `cd` into your NFS shared directory.
   - Clone this repo: `git clone <repo-url>`, then `cd` into it.

3. **Configure the machine list again on the master node.** Edit the files in `hosts/`:
   - `hosts.txt` — the host list, `user@host` format (first host = master).
   - `username.txt` — your Linux username.

4. **Generate the experiment configs.** Each generator writes a `work_dir_*` directory of per-experiment configs:
   ```bash
   cd exp/prepare_exp_configs
   python3 gen_demo_config.py     # single trace, meta_202210_kv (quick demo)
   python3 gen_meta_config.py     # Meta KV traces      (Fig 6)
   python3 gen_cdn_config.py      # Wikimedia CDN traces (Fig 7)
   python3 gen_twitter_config.py  # 54 Twitter KV traces (Fig 8)
   ```

5. **Configure experiment settings.** Edit `exp/configs.json`:
   - `work_dirs`: list of the generated `work_dir_*` directories to run (complete paths).
   - `need_download_traces`: `true` if you don't have the trace files locally.
   - `local_trace_file_dir`: where to store traces (must be NFS-shared and have enough space).
   - `python_path`: the Python interpreter to use on the hosts.

6. **Launch the master process:**
   ```bash
   cd exp/master
   nohup python3 master.py &
   ```

7. **Monitor progress.** `master.py` creates a timestamp-named directory (e.g. `20250810_135652`) containing:
   - `master.log` — detailed scheduling and job-execution logs (real-time progress, running jobs, per-host resource use).
   - `scheduler_state.json` — current state of all experiments.
   - `result_processed.csv` — final summary report (written once all experiments finish; `master.py` runs `summarize_result.py` automatically).

8. **Visualize the result** — either plot everything with Path A (`bash replot_results.sh`), or a single trace directly:
   ```bash
   python3 exp/plotting/plot_demo_figure.py exp/master/<timestamp>/result_processed.csv meta_202210_kv
   ```
   Replace `<timestamp>` with your run's directory. This produces `meta_kv_202210.pdf` and `meta_kv_202210_rebalanced_slabs.pdf`.

---

## Other experiments

### CPU overhead (Fig 11)

`overhead/` is a single-node experiment that counts how many CPU cycles the slab rebalancer burns relative to request serving.  See [overhead/README.md](overhead/README.md) for the manual perf/turbo/core-pinning details.

```bash
bash set_up_env/build_cachelib.sh --variant tx    # build the benchmark-tx branch (needed only here)
bash reproduce_cpu_cycles.sh --smoke              # one trace, LRU, prints ours-vs-shipped ratios
```

### Optimal allocation & synthetic traces (Fig 4–5)

`tools/trace_analysis/` computes per-class miss-ratio curves and the optimal slab allocation; `tools/create_synthetic_trace/` generates the synthetic Zipfian traces. See [docs/Tools.md](docs/Tools.md).
