import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import pandas as pd

datasets = ['PROF', 'MAP', 'PRD', 'TT', 'SYN1', 'SYN2', 'SYN3']

csv_file = "./artifact/result/time_breakdown_spec.csv"
pdf_filename = "./artifact/figure/time_breakdown_spec.pdf"

df = pd.read_csv(csv_file)
times1 = df.iloc[0, 1:].values.tolist()
times2 = df.iloc[1, 1:].values.tolist()

# Calculate total times and percentages
total_times = [t1 + t2 for t1, t2 in zip(times1, times2)]
percent1 = [(t1 / total * 100) for t1, total in zip(times1, total_times)]  # Speculative Parsing percentages
percent2 = [(t2 / total * 100) for t2, total in zip(times2, total_times)]  # Merge percentages

with PdfPages(pdf_filename) as pdf:
    plt.figure(figsize=(8, 3))

    bar1 = plt.bar(datasets, percent1, label='Speculative Decoding')
    bar2 = plt.bar(datasets, percent2, bottom=percent1, label='Merge')

    for i in range(len(datasets)):
        if percent1[i] >= 6:  # Show percentage if >= 6%
            plt.text(i, percent1[i]/2, f'{percent1[i]:.0f}%', 
                    ha='center', va='center', color='white', fontsize=14)
        if percent2[i] >= 6:  # Show percentage if >= 6%
            plt.text(i, percent1[i] + percent2[i]/2, f'{percent2[i]:.0f}%', 
                    ha='center', va='center', color='white', fontsize=14)

    plt.xlabel('Datasets', fontsize=14, labelpad=9)
    plt.ylabel('Percentage (%)', fontsize=14, labelpad=9)

    plt.xticks(fontsize=14) 
    plt.yticks(fontsize=14)

    plt.legend(fontsize=14)

    plt.grid(True, axis='y', linestyle='--', alpha=0.6)

    plt.tight_layout()

    pdf.savefig(bbox_inches='tight', pad_inches=0)
    plt.close()
