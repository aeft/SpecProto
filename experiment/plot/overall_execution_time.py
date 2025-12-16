import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import pandas as pd

datasets = ['PROF', 'MAP', 'PRD', 'TT', 'SYN1', 'SYN2', 'SYN3']
algorithms = ['Baseline', 'SpecProto (non-spec)', 'SpecProto (spec)']

csv_file = "./artifact/result/overall_execution_time.csv"
pdf_filename = "./artifact/figure/overall_execution_time.pdf"

df = pd.read_csv(csv_file)

execution_times = df.iloc[:, 1:].values.tolist()

speedup = [[0]*len(datasets) for _ in range(len(algorithms))]

for i in range(len(algorithms)):
    for j in range(len(datasets)):
        speedup[i][j] = execution_times[0][j]/execution_times[i][j]

# compute geomean for each algorithm
for i in range(len(algorithms)):
    geomean = 1
    for j in range(len(datasets)):
        if speedup[i][j] > 0:
            geomean *= speedup[i][j]
    geomean = geomean ** (1/len(datasets))
    speedup[i].append(geomean)
datasets.append('Geo')

hatches = ['///', '\\\\\\', '|||', '---', '+++'] # corresponds to algorithms
x = np.arange(len(datasets)) * 0.8

max_height = 8.3 # the max height of bar
width = 0.16

with PdfPages(pdf_filename) as pdf:
    fig, ax = plt.subplots(figsize=(11, 4))

    for i, alg in enumerate(algorithms):
        bars = ax.bar(x + (i - 1) * width, speedup[i], width, label=alg, alpha=.5)

        for j, bar in enumerate(bars):
            bar.set_hatch(hatches[i])
            height = bar.get_height()
            if height > max_height:
                bar.set_height(max_height)

    ax.set_xlabel('Datasets', fontsize=18, labelpad=9)
    ax.set_ylabel('Speedup', fontsize=18, labelpad=9)

    ax.set_xticks(x) 
    ax.set_xticklabels(datasets, fontsize=18)

    ax.tick_params(axis='y', labelsize=18)

    # set yaxis label
    ax.set_ylim(0, max_height)
    yticks = np.arange(0, max_height+1, 1)
    ax.set_yticks(yticks)

    ax.yaxis.grid(True, linestyle='--', alpha=0.6)

    ax.set_ylim(0, max_height)

    ax.legend(loc='upper left', ncol=3, fontsize=18)

    plt.tight_layout()

    pdf.savefig(fig, bbox_inches='tight', pad_inches=0)
    plt.close()