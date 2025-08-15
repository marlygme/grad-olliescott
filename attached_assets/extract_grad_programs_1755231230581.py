
import os
import pandas as pd
from datetime import datetime
from extractors import (
    FIRM_ALIASES, detect_program_type, detect_city, detect_intake_year,
    detect_salary, detect_length_months, detect_rotations, find_dates_near_keywords,
    extract_evidence_span, score_confidence, parse_timestamp_to_utcish, parse_date_to_iso
)

DEFAULT_INPUTS = [
    "/mnt/data/law_raw.csv",
    "/mnt/data/law_whirlpool_2018_2025.csv",
    "/mnt/data/raw_all.csv",
]

def main(in_paths=None, out_csv="out/grad_program_signals.csv", out_parquet="out/grad_program_signals.parquet"):
    in_paths = in_paths or DEFAULT_INPUTS
    frames = []
    for p in in_paths:
        if os.path.exists(p):
            try:
                df = pd.read_csv(p)
                df["source_file"] = os.path.basename(p)
                frames.append(df)
            except Exception as e:
                print(f"Failed reading {p}: {e}")
    if not frames:
        raise SystemExit("No CSVs found.")

    df = pd.concat(frames, ignore_index=True).drop_duplicates()
    for col in ["thread_title","thread_url","content","author","timestamp"]:
        if col not in df.columns:
            df[col] = None

    df["title_lc"] = df["thread_title"].fillna("").astype(str).str.lower()
    df["content_lc"] = df["content"].fillna("").astype(str).str.lower()
    df["combined_lc"] = (df["title_lc"] + " " + df["content_lc"]).str.replace(r"\\s+", " ", regex=True)

    records = []

    import re

    for _, row in df.iterrows():
        text_full = f"{row.get('thread_title','')}\\n{row.get('content','')}"
        t = row.get("combined_lc","")
        if not t.strip():
            continue

        # fallback year from timestamp if present
        fallback_year = None
        ts_raw = str(row.get("timestamp","") or "")
        m = re.search(r"\\b(20\\d{2})\\b", ts_raw)
        if m:
            try:
                fallback_year = int(m.group(1))
            except Exception:
                fallback_year = None

        matched = []
        for canonical, aliases in FIRM_ALIASES.items():
            alias_hit = None
            exact_alias = False
            for a in aliases:
                if re.search(rf"\\b{re.escape(a)}\\b", t, flags=re.IGNORECASE):
                    alias_hit = a
                    exact_alias = True
                    break
            if not alias_hit:
                if re.search(rf"\\b{re.escape(canonical.lower())}\\b", t):
                    alias_hit = canonical
                    exact_alias = True
            if alias_hit:
                matched.append((canonical, alias_hit, exact_alias))

        if not matched:
            continue

        program_type = detect_program_type(t)
        city = detect_city(t if t.strip() else row.get("title_lc",""))
        intake_year = detect_intake_year(text_full, fallback_year)
        open_date = find_dates_near_keywords(text_full, r"open(s|ing)?")
        close_date = find_dates_near_keywords(text_full, r"close(s|ing)?")
        salary = detect_salary(text_full)
        length_months = detect_length_months(text_full)
        rotations = detect_rotations(text_full)

        multi = len(matched) > 1

        for canonical, alias_hit, exact_alias in matched:
            evidence = extract_evidence_span(text_full, alias_hit)
            conf = score_confidence(
                is_exact_alias=exact_alias,
                program_explicit=(program_type != "ambiguous"),
                city_found=(city != "Other/Unknown"),
                intake_found=(intake_year is not None),
                month_only_dates=((open_date or "").endswith("-01") or (close_date or "").endswith("-28")),
                multi_firms=multi
            )
            records.append({
                "firm_name": canonical,
                "firm_alias": alias_hit,
                "program_type": program_type,
                "city": city,
                "intake_year": int(intake_year) if intake_year is not None else None,
                "application_open_date": open_date,
                "application_close_date": close_date,
                "program_length_months": length_months,
                "rotations_count": rotations,
                "salary_annual_aud": salary,
                "evidence_span": evidence,
                "thread_title": row.get("thread_title"),
                "thread_url": row.get("thread_url"),
                "post_number": row.get("post_number"),
                "post_timestamp": parse_timestamp_to_utcish(ts_raw),
                "source_file": row.get("source_file"),
                "confidence": round(conf, 3),
                "created_at": datetime.utcnow().isoformat()
            })

    out_df = pd.DataFrame.from_records(records, columns=[
        "firm_name","firm_alias","program_type","city","intake_year",
        "application_open_date","application_close_date","program_length_months","rotations_count",
        "salary_annual_aud","evidence_span","thread_title","thread_url","post_number","post_timestamp",
        "source_file","confidence","created_at"
    ])

    os.makedirs(os.path.dirname(out_csv), exist_ok=True)
    out_df.to_csv(out_csv, index=False)
    try:
        out_df.to_parquet(out_parquet, index=False)
    except Exception as e:
        print(f"Parquet write failed: {e}")

    # quick summary
    summary = (out_df.groupby(["firm_name","program_type"])["evidence_span"]
               .count().reset_index(name="count").sort_values(["firm_name","count"], ascending=[True,False]))
    print(summary.head(30).to_string(index=False))

if __name__ == "__main__":
    main()
