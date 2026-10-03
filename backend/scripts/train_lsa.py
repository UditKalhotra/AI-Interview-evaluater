"""
Offline LSA Pipeline Training Script.

Reads backend/data/Data.csv (Mohler ASAG Dataset), fits TF-IDF Vectorizer + TruncatedSVD
on the real dataset corpus of Answers, Student Texts, and Questions, and saves the fitted
pipeline to backend/data/lsa_pipeline.joblib for production scoring.

Usage:
    python -m scripts.train_lsa
    or
    python scripts/train_lsa.py
"""

import os
import re
import csv
import sys
import numpy as np
from pathlib import Path
from scipy.stats import pearsonr, spearmanr
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
from sklearn.metrics import mean_absolute_error
import joblib

backend_dir = Path(__file__).resolve().parent.parent
data_csv_path = backend_dir / "data" / "Data.csv"
saved_model_path = backend_dir / "data" / "lsa_pipeline.joblib"


def clean_text(text: str) -> str:
    """Clean HTML tags and normalize whitespace."""
    if not text:
        return ""
    text_clean = re.sub(r"<[^>]+>", " ", text)
    text_clean = re.sub(r"\s+", " ", text_clean).strip()
    return text_clean


def train_and_save_lsa_pipeline():
    print(f"=======================================================")
    print(f"  TRAINING REAL LSA PIPELINE FROM MOHLER DATASET      ")
    print(f"=======================================================")
    print(f"Dataset path: {data_csv_path}")

    if not data_csv_path.exists():
        print(f"ERROR: Mohler dataset not found at {data_csv_path}")
        sys.exit(1)

    rows = []
    with data_csv_path.open(mode="r", encoding="utf-8", errors="ignore") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)

    print(f"Loaded {len(rows)} rows from Data.csv")

    reference_answers = [clean_text(r.get("Answers", "")) for r in rows]
    student_texts = [clean_text(r.get("Texts", "")) for r in rows]
    questions = [clean_text(r.get("Questions", "")) for r in rows]

    human_scores = []
    valid_indices = []
    for idx, r in enumerate(rows):
        try:
            val = float(r.get("Score", 0.0))
            human_scores.append(val)
            valid_indices.append(idx)
        except ValueError:
            continue

    reference_answers = [reference_answers[i] for i in valid_indices]
    student_texts = [student_texts[i] for i in valid_indices]
    questions = [questions[i] for i in valid_indices]
    human_scores = np.array(human_scores)

    # 1. Build combined corpus
    corpus = list(set([t for t in (reference_answers + student_texts + questions) if t]))
    print(f"Unique text corpus size: {len(corpus)} documents")

    # 2. Fit TF-IDF Vectorizer
    print("Fitting TF-IDF Vectorizer (ngram_range=(1,2))...")
    vectorizer = TfidfVectorizer(
        stop_words="english",
        ngram_range=(1, 2),
        min_df=2,
        sublinear_tf=True,
    )
    tfidf_matrix = vectorizer.fit_transform(corpus)
    print(f"TF-IDF matrix shape: {tfidf_matrix.shape}")

    # 3. Fit TruncatedSVD
    n_components = min(50, tfidf_matrix.shape[1] - 1)
    print(f"Fitting TruncatedSVD (n_components={n_components})...")
    svd = TruncatedSVD(n_components=n_components, random_state=42)
    svd.fit(tfidf_matrix)

    # 4. Evaluate on dataset
    ans_tfidf = vectorizer.transform(reference_answers)
    text_tfidf = vectorizer.transform(student_texts)

    ans_svd = svd.transform(ans_tfidf)
    text_svd = svd.transform(text_tfidf)

    ans_norms = np.linalg.norm(ans_svd, axis=1, keepdims=True)
    text_norms = np.linalg.norm(text_svd, axis=1, keepdims=True)
    ans_norms[ans_norms == 0] = 1e-10
    text_norms[text_norms == 0] = 1e-10

    sims = np.sum((ans_svd / ans_norms) * (text_svd / text_norms), axis=1)
    sims = np.clip(sims, 0.0, 1.0)

    p_corr, _ = pearsonr(sims * 5.0, human_scores)
    s_corr, _ = spearmanr(sims * 5.0, human_scores)
    mae = mean_absolute_error(human_scores, sims * 5.0)

    print(f"Pearson r: {p_corr:.4f} | Spearman rho: {s_corr:.4f} | MAE (0-5 scale): {mae:.4f}")

    # 5. Save fitted pipeline
    model_payload = {
        "vectorizer": vectorizer,
        "svd": svd,
        "n_components": n_components,
    }
    saved_model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model_payload, saved_model_path)
    print(f"SUCCESS: Saved fitted LSA pipeline to {saved_model_path}")
    print(f"=======================================================\n")


if __name__ == "__main__":
    train_and_save_lsa_pipeline()
