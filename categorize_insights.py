
# categorize_insights.py
import csv, sys
from categorizer import classify_text, label

def run(in_path, out_path):
    with open(in_path, newline="", encoding="utf-8") as f, open(out_path, "w", newline="", encoding="utf-8") as g:
        r = csv.DictReader(f)
        w = csv.DictWriter(g, fieldnames=r.fieldnames + ["primary_cat","cat_labels"])
        w.writeheader()
        for row in r:
            p, cats, _ = classify_text(row.get("content",""), threshold=1.0, top_k=3)
            row["primary_cat"] = p or ""
            row["cat_labels"] = ", ".join([label(c) for c in cats])
            w.writerow(row)

if __name__ == "__main__":
    in_path = sys.argv[1]; out_path = sys.argv[2]
    run(in_path, out_path)
    print("Wrote", out_path)
