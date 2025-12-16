import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import pandas as pd

datasets = ['PROF', 'MAP', 'PRD', 'TT', 'SYN1', 'SYN2', 'SYN3']
algorithms = ['T=1', 'T=2', 'T=4', 'T=8', 'T=16']

csv_file = "./artifact/result/scalability_over_threads.csv"
pdf_filename = "./artifact/figure/scalability_over_threads.pdf"

df = pd.read_csv(csv_file)
execution_times = df.iloc[:, 1:].values.tolist()

hatches = ['///', '\\\\\\', '|||', '---', 'X'] # corresponds to T

speedup = [[0]*len(datasets) for _ in range(len(algorithms))]

for i in range(len(algorithms)):
    for j in range(len(datasets)):
        speedup[i][j] = execution_times[0][j]/execution_times[i][j]

x = np.arange(len(datasets))

max_height = 6 # the max height of bar
width = 0.16
with PdfPages(pdf_filename) as pdf:
    fig, ax = plt.subplots(figsize=(10, 4))

    for i, alg in enumerate(algorithms):
        bars = ax.bar(x + i * width, speedup[i], width, label=alg, alpha=.5)
        
        for j, bar in enumerate(bars):
            bar.set_hatch(hatches[i])
            height = bar.get_height()
            if height > max_height:
                bar.set_height(max_height)
                ax.annotate(f'{height:.2g}',
                            xy=(bar.get_x() + bar.get_width() / 2, min(max_height, height)),
                            xytext=(0, 0),  
                            textcoords="offset points",
                            ha='center', va='bottom', fontsize=13)

    ax.set_xlabel('Datasets', fontsize=18, labelpad=9)
    ax.set_ylabel('Speedup', fontsize=18, labelpad=9)

    ax.set_xticks(x + width * 2) 
    ax.set_xticklabels(datasets, fontsize=18)

    ax.tick_params(axis='y', labelsize=18)

    # set yaxis label
    ax.set_ylim(0, max_height+1)
    yticks = np.arange(0, max_height+1, 1)
    ax.set_yticks(yticks)

    ytick_labels = [f'{tick}' for tick in yticks]
    ytick_labels[-1] = r'$\geq$'+str(max_height)
    ax.set_yticklabels(ytick_labels)

    ax.yaxis.grid(True, linestyle='--', alpha=0.6)

    ax.legend(fontsize=16, ncol=4)

    plt.tight_layout()

    pdf.savefig(fig, bbox_inches='tight', pad_inches=0)
    plt.close()