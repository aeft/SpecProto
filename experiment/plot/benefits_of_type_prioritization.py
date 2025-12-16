import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import pandas as pd

datasets = ['PROF', 'MAP', 'PRD', 'TT', 'SYN1', 'SYN2', 'SYN3']
algorithms = ['Baseline', 'SpecProto without Type Prioritization', 'SpecProto']

csv_file = "./artifact/result/benefits_of_type_prioritization.csv"
pdf_filename = "./artifact/figure/benefits_of_type_prioritization.pdf"

df = pd.read_csv(csv_file)

execution_times = df.iloc[:, 1:].values.tolist()

x = np.arange(len(datasets)) * 0.8

max_height = 3 # the max height of bar
width = 0.16

hatches = ['///', '\\\\\\', '---'] 

with PdfPages(pdf_filename) as pdf:
    fig, ax = plt.subplots(figsize=(10, 4))

    for i, alg in enumerate(algorithms):
        bars = ax.bar(x + (i - 1) * width, execution_times[i], width, label=alg, alpha=.5)

        for j, bar in enumerate(bars):
            bar.set_hatch(hatches[i])
            height = bar.get_height()
            if height > max_height:
                bar.set_height(max_height)
                offset_x = 0

                offset_x = 0
                if i == 0:
                    offset_x -= 6
                if i == 1:
                    offset_x += 6
                ax.annotate(f'{height:.1f}',
                            xy=(bar.get_x() + bar.get_width() / 2, min(max_height, height)),
                            xytext=(offset_x, 1),  
                            textcoords="offset points",
                            ha='center', va='bottom', fontsize=13)

    ax.set_xlabel('Datasets', fontsize=18, labelpad=9)
    ax.set_ylabel('Time (s)', fontsize=18, labelpad=9)

    ax.set_xticks(x) 
    ax.set_xticklabels(datasets, fontsize=18)

    ax.tick_params(axis='y', labelsize=18)

    # set yaxis label
    ax.set_ylim(0, max_height)
    yticks = np.arange(0, max_height+1, 1)

    ax.set_yticks(yticks)
    ytick_labels = [f'{tick}' for tick in yticks]
    ytick_labels[-1] = r'$\geq$'+str(max_height)
    ax.set_yticklabels(ytick_labels)

    ax.yaxis.grid(True, linestyle='--', alpha=0.6)

    ax.set_ylim(0, max_height+0.6)

    ax.legend(fontsize=17)

    plt.tight_layout()

    pdf.savefig(fig, bbox_inches='tight', pad_inches=0)
    plt.close()
