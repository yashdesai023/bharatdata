import pandas as pd
import sys

def inspect_excel(path):
    print(f"Inspecting: {path}")
    df = pd.read_excel(path, header=None, nrows=10)
    for i, row in df.iterrows():
        print(f"Row {i}: {row.tolist()}")

if __name__ == "__main__":
    inspect_excel(sys.argv[1])
