"""
Module 7 — Phase A: Offline LSA Scoring Validation Script.

Reads /backend/data/Data.csv (Mohler ASAG dataset), fits TF-IDF Vectorizer + TruncatedSVD
on the combined corpus of Answers + Texts, computes cosine similarity between candidate
texts and reference answers in SVD latent space, evaluates correlation (Pearson, Spearman)
and Mean Absolute Error against human scores, and saves the fitted models to disk.
"""

import os
import re
import csv
import sys
import numpy as np
from scipy.stats import pearsonr, spearmanr
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
from sklearn.metrics import mean_absolute_error
import joblib

# Paths setup
script_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(script_dir)
data_csv_path = os.path.join(backend_dir, "data", "Data.csv")
saved_model_path = os.path.join(backend_dir, "data", "lsa_pipeline.joblib")


def clean_text(text: str) -> str:
    """Clean HTML tags and normalize whitespace in input text."""
    if not text:
        return ""
    # Strip HTML tags like <br>, <br/>, <p>
    text_clean = re.sub(r"<[^>]+>", " ", text)
    # Replace multiple spaces with single space
    text_clean = re.sub(r"\s+", " ", text_clean).strip()
    return text_clean


def main():
    print(f"Loading Mohler dataset from: {data_csv_path}")

    if not os.path.exists(data_csv_path):
        print(f"ERROR: Dataset file not found at {data_csv_path}")
        sys.exit(1)

    rows = []
    with open(data_csv_path, mode="r", encoding="utf-8", errors="ignore") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)

    print(f"Total rows loaded: {len(rows)}")

    # Extract cleaned text fields and scores
    reference_answers = [clean_text(r.get("Answers", "")) for r in rows]
    student_texts = [clean_text(r.get("Texts", "")) for r in rows]
    questions = [clean_text(r.get("Questions", "")) for r in rows]
    
    human_scores = []
    valid_indices = []

    for idx, r in enumerate(rows):
        try:
            score_val = float(r.get("Score", 0.0))
            human_scores.append(score_val)
            valid_indices.append(idx)
        except ValueError:
            continue

    reference_answers = [reference_answers[i] for i in valid_indices]
    student_texts = [student_texts[i] for i in valid_indices]
    questions = [questions[i] for i in valid_indices]
    human_scores = np.array(human_scores)

    # 1. Build combined corpus for fitting LSA
    corpus = list(set(reference_answers + student_texts + questions))
    print(f"Unique text corpus size for LSA fitting: {len(corpus)}")

    # 2. Fit TF-IDF Vectorizer & TruncatedSVD
    print("Fitting TF-IDF Vectorizer (ngram_range=(1,2))...")
    vectorizer = TfidfVectorizer(
        stop_words="english",
        ngram_range=(1, 2),
        min_df=2,
        sublinear_tf=True,
    )
    tfidf_matrix = vectorizer.fit_transform(corpus)

    n_components = min(50, tfidf_matrix.shape[1] - 1)
    print(f"Fitting TruncatedSVD (n_components={n_components})...")
    svd = TruncatedSVD(n_components=n_components, random_state=42)
    svd.fit(tfidf_matrix)

    # 3. Transform Answers and Texts into SVD latent space
    ans_tfidf = vectorizer.transform(reference_answers)
    text_tfidf = vectorizer.transform(student_texts)

    ans_svd = svd.transform(ans_tfidf)
    text_svd = svd.transform(text_tfidf)

    # Normalize vectors for cosine similarity computation
    ans_norms = np.linalg.norm(ans_svd, axis=1, keepdims=True)
    text_norms = np.linalg.norm(text_svd, axis=1, keepdims=True)

    # Avoid division by zero
    ans_norms[ans_norms == 0] = 1e-10
    text_norms[text_norms == 0] = 1e-10

    ans_svd_norm = ans_svd / ans_norms
    text_svd_norm = text_svd / text_norms

    # Row-wise dot product = cosine similarity in SVD space
    lsa_cosine_sims = np.sum(ans_svd_norm * text_svd_norm, axis=1)
    # Clip similarity to [0.0, 1.0]
    lsa_cosine_sims = np.clip(lsa_cosine_sims, 0.0, 1.0)

    # Scale LSA similarity to 0-5 scale (matching Mohler human score scale)
    lsa_scaled_scores_5 = lsa_cosine_sims * 5.0
    lsa_scaled_scores_100 = lsa_cosine_sims * 100.0

    # 4. Evaluation Metrics
    pearson_corr, pearson_p = pearsonr(lsa_scaled_scores_5, human_scores)
    spearman_corr, spearman_p = spearmanr(lsa_scaled_scores_5, human_scores)
    mae_5 = mean_absolute_error(human_scores, lsa_scaled_scores_5)
    mae_100 = mean_absolute_error(human_scores * 20.0, lsa_scaled_scores_100)

    # 5. Print Summary Report
    print("\n=======================================================")
    print("      LSA SCORING OFFLINE VALIDATION SUMMARY REPORT    ")
    print("=======================================================")
    print(f"Dataset Rows Analyzed     : {len(human_scores)}")
    print(f"TF-IDF Vocabulary Size    : {len(vectorizer.vocabulary_)}")
    print(f"SVD Components Count      : {n_components}")
    print(f"Pearson Correlation (r)   : {pearson_corr:.4f} (p-value: {pearson_p:.4e})")
    print(f"Spearman Correlation (rho): {spearman_corr:.4f} (p-value: {spearman_p:.4e})")
    print(f"Mean Absolute Error (0-5) : {mae_5:.4f}")
    print(f"Mean Absolute Error (0-100): {mae_100:.2f}")

    # Calculate worst-mismatched samples
    errors = np.abs(lsa_scaled_scores_5 - human_scores)
    worst_indices = np.argsort(errors)[::-1][:5]

    print("\n-------------------------------------------------------")
    print("      TOP 5 WORST-MISMATCHED EXAMPLES FOR MANUAL INSPECTION")
    print("-------------------------------------------------------")
    for i, idx in enumerate(worst_indices, 1):
        print(f"\nExample #{i} (Row index {idx}):")
        print(f"  Question        : {questions[idx]}")
        print(f"  Reference Answer: {reference_answers[idx]}")
        print(f"  Student Text    : {student_texts[idx]}")
        print(f"  Human Score     : {human_scores[idx]}")
        print(f"  LSA Sim Score   : {lsa_scaled_scores_5[idx]:.2f} (0-5 scale) / {lsa_scaled_scores_100[idx]:.1f} (0-100 scale)")
        print(f"  Absolute Error  : {errors[idx]:.2f}")

    # 6. Save fitted models to disk
    model_payload = {
        "vectorizer": vectorizer,
        "svd": svd,
        "n_components": n_components,
    }
    os.makedirs(os.path.dirname(saved_model_path), exist_ok=True)
    joblib.dump(model_payload, saved_model_path)
    print(f"\nSaved fitted LSA pipeline to: {saved_model_path}")
    print("=======================================================\n")


if __name__ == "__main__":
    main()
