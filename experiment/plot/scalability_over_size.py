import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import pandas as pd

X_values = [50, 100, 200, 400, 800, 1600]

csv_file = "./artifact/result/scalability_over_size.csv"
pdf_filename = "./artifact/figure/scalability_over_size.pdf"

df = pd.read_csv(csv_file)
Y_SPP = df.iloc[:, 1].values.tolist()

with PdfPages(pdf_filename) as pdf:
    plt.figure(figsize=(8, 3))

    plt.plot(X_values, Y_SPP, marker='v', label='SpecProto')

    plt.xscale('log')

    plt.xlabel('Size (MB)', fontsize=14)
    plt.ylabel('Time (s)', fontsize=14)

    plt.xticks(fontsize=14) 
    plt.yticks(fontsize=14)

    plt.legend()

    plt.xticks(X_values, X_values)

    plt.grid(True)

    plt.tight_layout()

    pdf.savefig()
    plt.close()

