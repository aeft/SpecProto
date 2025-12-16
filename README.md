# SpecProto

SpecProto is a parallelizing compiler that generates parallel decoders for a given Protobuf schema.

## Reproduce

Our experiments ran on a server node with two Intel Xeon E5-2683 v4 processors and 512GB RAM. Unless otherwise specified, all parallel executions will use a single socket with 16 threads. This server runs on Rocky 8 and is installed with G++ 9.2.1. All programs are compiled with O3 optimization. The timing results reported are the average of five repetitive runs.

Please ensure that the machine has 16 physical CPU cores and at least 16 GB of memory.

### (optional) HPC 
If you are using HPC, you can use the following command to get a shell with 32 cores and 16GB memory. (Exclusive mode is recommended to avoid resource contention.)
```bash
srun --mem=16gb --cpus-per-task=32 -p intel --nodes=1 --ntasks=1 --time=2:00:00 --exclusive --pty bash -l
module load gcc@9.2.1
```

### 1. Install Protobuf

This project installs protobuf locally into the repository.

Before running the installation script, make sure the following tools are available:
- `git`
- `cmake` (tested with `cmake 3.26.4`)
- A C++ compiler (tested with `g++ 9.2.1`)

```bash
git --version && cmake --version && g++ --version
```

On Debian/Ubuntu systems, the required tools can be installed with:
```bash
sudo apt update
sudo apt install -y git cmake build-essential
```

Then install protobuf locally:
```bash
./script/install_protobuf.sh
```

### 2. Install Python Dependencies
Tested with Python 3.9:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

### 3. Download Datasets
Setup the project:
```bash
make setup
```

Download datasets from [Google Drive](https://drive.google.com/drive/folders/1twyHH5PbnYRaCO9pHzE_2k1BzfzUyU_G) and place them in `./dataset`.

### 4. Run Experiments

We have encapsulated the detailed commands for running the experiments in `Makefile`, which calls Python scripts to execute the experiments and generate the results. Below, for each experiment, we provide a corresponding `make` command to run the experiment and produce the results.

#### Before running experiments, generate and build the code:
```bash
make gen_parallel_pbs
make build_all
```

Note `impl=bl` is the baseline implementation. `impl=tpp` is the non-speculative implementation. `impl=spp` is the speculative implementation.

#### Overall Decoding Time (Table 2, Figure 11)

```bash
make overall_execution_time
make overall_execution_time_fig
```

The results will be saved in `./artifact/result/overall_execution_time.csv` and `./artifact/figure/overall_execution_time.pdf`.

#### Memory Overhead (Table 2)

```bash
make memory_overhead
```

The results will be saved in `./artifact/result/memory_overhead.csv`.

#### SpecProto (spec) Time Breakdown (Figure 12)

```bash
make time_breakdown_spec
make time_breakdown_spec_fig
```

The results will be saved in `./artifact/result/time_breakdown_spec.csv` and `./artifact/figure/time_breakdown_spec.pdf`.

#### Speculation Cost Breakdown (Table 3)

First, we need to generate and build the code with statistics enabled:
```bash
make gen_parallel_pbs
make build_all BUILD="build/stat" DEFINE="-DCOUNT_REDO_BYTES -DCOUNT_VISITED_BYTES"
```

Then, run the experiment:
```bash
make cost_breakdown_spec
```

The results will be saved in `./artifact/result/cost_breakdown_spec.csv`. Note the statistics may not be exactly the same as the ones in the paper due to update of the code generation.

#### Benefits of Type Prioritization (Figure 13)

First, we need to generate and build the code with disabled type prioritization:
```bash
make gen_parallel_pbs GEN_OPTIONS="--disable_type_prioritization"
make build_all BUILD="build/disable_type_prioritization"
```

Then, run the experiment:
```bash
make benefits_of_type_prioritization
make benefits_of_type_prioritization_fig
```

The results will be saved in `./artifact/result/benefits_of_type_prioritization.csv` and `./artifact/figure/benefits_of_type_prioritization.pdf`.

#### Scalability over Threads (Figure 14)

```bash
make scalability_over_threads
make scalability_over_threads_fig
```

The results will be saved in `./artifact/result/scalability_over_threads.csv` and `./artifact/figure/scalability_over_threads.pdf`.

#### Scalability over Message Size (Figure 15)

```bash
make scalability_over_size
make scalability_over_size_fig
```

The results will be saved in `./artifact/result/scalability_over_size.csv` and `./artifact/figure/scalability_over_size.pdf`.

## Run a single test

```bash
make gen_parallel_pb PREFIX=pprof_profile
make build PREFIX=pprof_profile
make run TEST_MODE=C DATASET=pprof_profile IMPL=spp THREADS=16
```

Note `TEST_MODE=C` is the check mode (i.e., compare the results with the standard parser to test the correctness). `TEST_MODE=B` is the benchmark mode.

To run your own schema and dataset, you should first put the schema and dataset in `./schema` and `./dataset` respectively. Then, run the following command to generate and build the code:
```bash
make gen_parallel_pb PREFIX=your_schema
make build PREFIX=your_schema
```

Then, run the following command to run the test:
```bash
make run TEST_MODE=C DATASET=your_dataset IMPL=spp THREADS=16
```

Note currently we support a simplified Protobuf schema. The package should be `PB` and the first message should be the main message. Please refer to `./schema/pprof_profile.proto` for an example.