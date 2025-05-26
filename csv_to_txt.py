import pandas as pd
import os

df = pd.read_csv("random_texts.csv", usecols=['text'])

output_dir = "data/txt/"
for idx, row in df.iterrows():
    text = row['text'] or ""
    filename = os.path.join(output_dir, f"initial_{idx:03d}.txt")
    with open(filename, "w", encoding="utf-8") as f:
        f.write(text)

print(f"Wrote {len(df)} files to {output_dir}")