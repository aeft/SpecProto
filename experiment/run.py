import argparse
import subprocess
import os
import copy
from pathlib import Path
import sys
import csv
import re

BIN = "./artifact/{build}/{schema}/{schema}.test"

DATASET_TO_SCHEMA = {
    "pprof_profile": "pprof_profile",
    "google_map": "google_map",
    "walmart_product": "walmart_product",
    "twitter_stream": "twitter_stream",
    "synth_wiki1": "synth_wiki",
    "synth_wiki2": "synth_wiki",
    "synth_tree": "synth_tree",

    "twitter_stream_50MB": "twitter_stream",
    "twitter_stream_100MB": "twitter_stream",
    "twitter_stream_200MB": "twitter_stream",
    "twitter_stream_400MB": "twitter_stream",
    "twitter_stream_800MB": "twitter_stream",
    "twitter_stream_1600MB": "twitter_stream",
}

DATASET_MAP = {
    "pprof_profile": "PROF",
    "google_map": "MAP",
    "walmart_product": "PRD",
    "twitter_stream": "TT",
    "synth_wiki1": "SYN1",
    "synth_wiki2": "SYN2",
    "synth_tree": "SYN3",
}

def run(test_mode, dataset, impl, threads, runs, build="build", cmds=None):
    env = copy.deepcopy(os.environ)

    env["OMP_NUM_THREADS"] = str(threads)
    env["OMP_PLACES"] = "cores"
    env["OMP_PROC_BIND"] = "close"
    env["LD_PRELOAD"] = "./third_party/mimalloc/libmimalloc.so"

    if dataset in DATASET_TO_SCHEMA:
        schema = DATASET_TO_SCHEMA[dataset]
    else:
        schema = dataset
    
    bin = BIN.format(build=build, schema=schema)

    cmd = [
        bin,
        f"--file_path=./dataset/{dataset}.pb",
        f"--test_mode={test_mode}",
        f"--impl={impl}",
        f"--runs={runs}",
    ]

    if cmds:
        cmd = cmds + cmd

    print(f"[RUN] bin={bin} schema={schema} dataset={dataset} test_mode={test_mode} impl={impl} threads={threads} runs={runs}")
    res = subprocess.run(
        cmd,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    print(res.stdout, end="")
    print(res.stderr, end="", file=sys.stderr)
    return res.stdout, res.stderr

def run_overall_execution_time():
    os.makedirs("./artifact/log/overall_execution_time", exist_ok=True)

    extract_pattern = re.compile(r"execution_time:\s*([0-9.]+)")

    results = {}
    for impl in ["bl", "tpp", "spp"]:
        for dataset in DATASET_MAP.keys():
            res_stdout, _ = run(
                test_mode="B",
                dataset=dataset,
                impl=impl,
                threads=16,
                runs=5,
            )
            with open(f"./artifact/log/overall_execution_time/{impl}_{dataset}.txt", "w") as f:
                f.write(res_stdout)
            m = extract_pattern.search(res_stdout)
            if not m:
                raise RuntimeError("execution_time not found in stdout")

            results.setdefault(impl, {})[dataset] = round(float(m.group(1)), 3)

    with open("./artifact/result/overall_execution_time.csv", "w") as f:
        writer = csv.writer(f)
        writer.writerow([""] + [DATASET_MAP[dataset] for dataset in DATASET_MAP.keys()])
        for impl in results.keys():
            writer.writerow([impl] + [results[impl][dataset] for dataset in DATASET_MAP.keys()])

def run_memory_overhead():
    os.makedirs("./artifact/log/memory_overhead", exist_ok=True)

    # Regex to extract memory from /usr/bin/time -v output
    memory_pattern = re.compile(r"Maximum resident set size \(kbytes\):\s*(\d+)")

    results = {}
    for impl in ["bl", "tpp", "spp"]:
        for dataset in DATASET_MAP.keys():
            res_stdout, res_stderr = run(
                test_mode="B",
                dataset=dataset,
                impl=impl,
                threads=16,
                runs=0, # run 1 time for memory overhead
                cmds=["/usr/bin/time", "-v"],
            )

            log_content = f"STDOUT:\n{res_stdout}\n\nSTDERR:\n{res_stderr}"
            with open(f"./artifact/log/memory_overhead/{impl}_{dataset}.txt", "w") as f:
                f.write(log_content)

            m = memory_pattern.search(res_stderr)
            if not m:
                raise RuntimeError("memory_overhead not found in stderr")

            memory_kb = int(m.group(1))
            memory_gb = round(memory_kb * 1024 / 1e9, 2)
            results.setdefault(impl, {})[dataset] = memory_gb

    # Write results to CSV
    with open("./artifact/result/memory_overhead.csv", "w") as f:
        writer = csv.writer(f)
        writer.writerow([""] + [DATASET_MAP[dataset] for dataset in DATASET_MAP.keys()])
        for impl in results.keys():
            writer.writerow([impl] + [results[impl][dataset] for dataset in DATASET_MAP.keys()])

def run_memory_overhead_over_threads():
    os.makedirs("./artifact/log/memory_overhead_over_threads", exist_ok=True)

    memory_pattern = re.compile(r"Maximum resident set size \(kbytes\):\s*(\d+)")

    results = {}
    for impl in ["tpp", "spp"]:
        for threads in [1, 2, 4, 8, 16]:
            for dataset in DATASET_MAP.keys():
                res_stdout, res_stderr = run(
                    test_mode="B",
                    dataset=dataset,
                    impl=impl,
                    threads=threads,
                    runs=0, # run 1 time for memory overhead
                    cmds=["/usr/bin/time", "-v"],
                )

                log_content = f"STDOUT:\n{res_stdout}\n\nSTDERR:\n{res_stderr}"
                with open(f"./artifact/log/memory_overhead_over_threads/{impl}_{threads}_{dataset}.txt", "w") as f:
                    f.write(log_content)

                m = memory_pattern.search(res_stderr)
                if not m:
                    raise RuntimeError("memory_overhead not found in stderr")

                memory_kb = int(m.group(1))
                memory_gb = round(memory_kb * 1024 / 1e9, 2)
                results.setdefault(f"{impl}_{threads}", {})[dataset] = memory_gb

    with open("./artifact/result/memory_overhead_over_threads.csv", "w") as f:
        writer = csv.writer(f)
        writer.writerow([""] + [DATASET_MAP[dataset] for dataset in DATASET_MAP.keys()])
        for key in results.keys():
            writer.writerow([key] + [results[key][dataset] for dataset in DATASET_MAP.keys()])

def run_time_breakdown_spec():
    os.makedirs("./artifact/log/time_breakdown_spec", exist_ok=True)

    extract_pattern = re.compile(r"speculatively_parsing_time:\s*([0-9.]+)")
    extract_pattern2 = re.compile(r"execution_time:\s*([0-9.]+)")
    results = {}
    impl = "spp"
    runs = 5
    for dataset in DATASET_MAP.keys():
        res_stdout, _ = run(
            test_mode="B",
            dataset=dataset,
            impl=impl,
            threads=16,
            runs=runs,
        )
        with open(f"./artifact/log/time_breakdown_spec/{impl}_{dataset}.txt", "w") as f:
            f.write(res_stdout)
        m = extract_pattern.findall(res_stdout)
        if not m:
            raise RuntimeError("speculatively_parsing_time not found in stdout")
        m2 = extract_pattern2.search(res_stdout)
        if not m2:
            raise RuntimeError("execution_time not found in stdout")

        assert len(m) == runs+1, f"speculatively_parsing_time should exist {runs+1} times, got {len(m)}"
        
        m = m[1:]
        spec_time = float(sum([float(x) for x in m]) / runs)

        results[dataset] = {
            "spec_time": round(spec_time, 3),
            "merge_time": round(float(m2.group(1))-spec_time, 4),
        }

    with open("./artifact/result/time_breakdown_spec.csv", "w") as f:
        writer = csv.writer(f)
        writer.writerow([""] + [DATASET_MAP[dataset] for dataset in DATASET_MAP.keys()])
        writer.writerow(["spec_time"] + [results[dataset]["spec_time"] for dataset in DATASET_MAP.keys()])
        writer.writerow(["merge_time"] + [results[dataset]["merge_time"] for dataset in DATASET_MAP.keys()])

def run_benefits_of_type_prioritization():
    os.makedirs("./artifact/log/benefits_of_type_prioritization", exist_ok=True)

    extract_pattern = re.compile(r"execution_time:\s*([0-9.]+)")

    results = {}
    for impl in ["bl", "spp_disable_type_prioritization", "spp"]:
        for dataset in DATASET_MAP.keys():
            build = "build"
            run_impl = impl
            if impl == "spp_disable_type_prioritization":
                build = "build/disable_type_prioritization"
                run_impl = "spp"
            res_stdout, _ = run(
                test_mode="B",
                dataset=dataset,
                impl=run_impl,
                threads=16,
                runs=5,
                build=build,
            )
            with open(f"./artifact/log/benefits_of_type_prioritization/{impl}_{dataset}.txt", "w") as f:
                f.write(res_stdout)
            m = extract_pattern.search(res_stdout)
            if not m:
                raise RuntimeError("execution_time not found in stdout")

            results.setdefault(impl, {})[dataset] = round(float(m.group(1)), 3)
    
    with open("./artifact/result/benefits_of_type_prioritization.csv", "w") as f:
        writer = csv.writer(f)
        writer.writerow([""] + [DATASET_MAP[dataset] for dataset in DATASET_MAP.keys()])
        for impl in results.keys():
            writer.writerow([impl] + [results[impl][dataset] for dataset in DATASET_MAP.keys()])

def run_scalability_over_threads():
    os.makedirs("./artifact/log/scalability_over_threads", exist_ok=True)

    extract_pattern = re.compile(r"execution_time:\s*([0-9.]+)")

    results = {}
    impl = "spp"
    for threads in [1, 2, 4, 8, 16]:
        for dataset in DATASET_MAP.keys():
            res_stdout, _ = run(
                test_mode="B",
                dataset=dataset,
                impl=impl,
                threads=threads,
                runs=5,
            )
            with open(f"./artifact/log/scalability_over_threads/{impl}_{dataset}_{threads}.txt", "w") as f:
                f.write(res_stdout)
            m = extract_pattern.search(res_stdout)
            if not m:
                raise RuntimeError("execution_time not found in stdout")

            results.setdefault(threads, {})[dataset] = round(float(m.group(1)), 3)

    with open("./artifact/result/scalability_over_threads.csv", "w") as f:
        writer = csv.writer(f)
        writer.writerow([""] + [DATASET_MAP[dataset] for dataset in DATASET_MAP.keys()])
        for threads in results.keys():
            writer.writerow([threads] + [results[threads][dataset] for dataset in DATASET_MAP.keys()])

def run_scalability_over_size():
    os.makedirs("./artifact/log/scalability_over_size", exist_ok=True)

    extract_pattern = re.compile(r"execution_time:\s*([0-9.]+)")

    impl = "spp"
    dataset = "twitter_stream"
    results = {}
    for size in [50, 100, 200, 400, 800, 1600]:
        res_stdout, _ = run(
            test_mode="B",
            dataset=dataset + f"_{size}MB",
            impl=impl,
            threads=16,
            runs=5,
        )
        with open(f"./artifact/log/scalability_over_size/{impl}_twitter_stream_{size}MB.txt", "w") as f:
            f.write(res_stdout)
        m = extract_pattern.search(res_stdout)
        if not m:
            raise RuntimeError("execution_time not found in stdout")

        results[size] = round(float(m.group(1)), 3)

    with open("./artifact/result/scalability_over_size.csv", "w") as f:
        writer = csv.writer(f)
        writer.writerow(["size", "time"])
        for size in results.keys():
            writer.writerow([size] + [results[size]])

def run_cost_breakdown_spec():
    os.makedirs("./artifact/log/cost_breakdown_spec", exist_ok=True)

    extract_pattern = re.compile(r"visited_byte_cnt_total:\s*([0-9.]+)")
    extract_pattern2 = re.compile(r"stat_redo_bytes:\s*([0-9.]+)")

    results = {}
    impl = "spp"
    for dataset in DATASET_MAP.keys():
        res_stdout, _ = run(
            test_mode="B",
            dataset=dataset,
            impl=impl,
            threads=16,
            runs=0,
            build="build/stat",
        )
        with open(f"./artifact/log/cost_breakdown_spec/{dataset}.txt", "w") as f:
            f.write(res_stdout)
        m = extract_pattern.search(res_stdout)
        if not m:
            raise RuntimeError("visited_byte_cnt_total not found in stdout")
        m2 = extract_pattern2.search(res_stdout)
        if not m2:
            raise RuntimeError("stat_redo_bytes not found in stdout")

        results[dataset] = {
            "visited_byte_cnt_total": int(m.group(1)),
            "stat_redo_bytes": int(m2.group(1)),
        }

    with open("./artifact/result/cost_breakdown_spec.csv", "w") as f:
        writer = csv.writer(f)
        writer.writerow([""] + [DATASET_MAP[dataset] for dataset in DATASET_MAP.keys()])
        writer.writerow(["Processed"] + [results[dataset]["visited_byte_cnt_total"] for dataset in DATASET_MAP.keys()])
        writer.writerow(["Redo"] + [results[dataset]["stat_redo_bytes"] for dataset in DATASET_MAP.keys()])

def run_experiment(experiment):
    if experiment == "overall_execution_time":
        run_overall_execution_time()
    elif experiment == "memory_overhead":
        run_memory_overhead()
    elif experiment == "time_breakdown_spec":
        run_time_breakdown_spec()
    elif experiment == "benefits_of_type_prioritization":
        run_benefits_of_type_prioritization()
    elif experiment == "scalability_over_threads":
        run_scalability_over_threads()
    elif experiment == "scalability_over_size":
        run_scalability_over_size()
    elif experiment == "cost_breakdown_spec":
        run_cost_breakdown_spec()
    elif experiment == "memory_overhead_over_threads":
        run_memory_overhead_over_threads()
    else:
        raise ValueError(f"Unknown experiment: {experiment}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--experiment", choices=[
        "overall_execution_time",
        "memory_overhead",
        "time_breakdown_spec",
        "benefits_of_type_prioritization",
        "scalability_over_threads",
        "scalability_over_size",
        "cost_breakdown_spec",
        "memory_overhead_over_threads",
    ])
    ap.add_argument("--test_mode", choices=["C", "B"])
    ap.add_argument("--dataset")
    ap.add_argument("--impl", choices=["gg", "bl", "tpp", "spp"])
    ap.add_argument("--runs", type=int, default=5)
    ap.add_argument("--threads", type=int, default=16)
    args = ap.parse_args()

    if args.experiment:
        run_experiment(args.experiment)
        return

    run(
        test_mode=args.test_mode,
        dataset=args.dataset,
        impl=args.impl,
        threads=args.threads,
        runs=args.runs,
    )

if __name__ == "__main__":
    main()
