"""
Core NLP + stats analysis engine for the College Event Feedback Analyzer.
Fully local/offline - no external API calls.
"""
import base64
import io
import re
from collections import Counter

import numpy as np
import pandas as pd
from nltk.sentiment import SentimentIntensityAnalyzer
from nltk.corpus import stopwords
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import LatentDirichletAllocation, TruncatedSVD
from wordcloud import WordCloud
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

STOPWORDS = set(stopwords.words("english"))
_sia = SentimentIntensityAnalyzer()


def detect_column_types(df: pd.DataFrame):
    """Classify each column as 'rating' (numeric survey scale, e.g. 1-5 or 1-10),
    'text' (free-form remarks, comments, and detailed feedback), or 'categorical'.
    Pure identifier/serial columns (Response ID, Label) are ignored so they don't skew stats."""
    rating_cols, text_cols, categorical_cols = [], [], []
    for col in df.columns:
        series = df[col].dropna()
        if series.empty:
            continue
        col_clean = str(col).strip()
        col_lower = col_clean.lower()

        # Check for identifier / serial sequence names
        is_id_name = bool(re.search(r"(^|[\s_\-])(id|identifier|sr_?no|sno|serial|index|token|uuid)($|[\s_\-])", col_lower))
        if col_lower in ("id", "response id", "response_id", "respondent id", "response label", "label", "sno", "sr no", "sr.no", "sr_no", "index", "token", "uuid") or col_lower.endswith("_id") or col_lower.endswith(" id"):
            is_id_name = True

        numeric = pd.to_numeric(series, errors="coerce")
        is_numeric = numeric.notna().mean() > 0.8

        if is_numeric:
            num_min, num_max = numeric.min(), numeric.max()
            nunique = numeric.nunique()
            has_rating_kw = any(w in col_lower for w in ("rate", "rating", "score", "star", "satisfaction", "scale", "point", "eval"))
            is_rating_scale = (
                (not is_id_name) and (
                    (num_min >= 0 and num_max <= 10 and nunique <= 15) or
                    (has_rating_kw and num_min >= 0 and num_max <= 100 and nunique <= 25)
                )
            )
            if is_rating_scale:
                rating_cols.append(col)
                continue
            elif is_id_name or (nunique == len(series) and nunique > 50):
                # Identifier/index sequence - skip from charts/analysis
                continue
            else:
                # Numeric demographic or categorical (e.g. Year 1-4, Semester, Age bracket)
                categorical_cols.append(col)
                continue

        # If string column is an ID/UUID sequence (e.g. 'Response 00001')
        if is_id_name or (series.nunique() == len(series) and len(series) > 50):
            avg_chars = series.astype(str).str.len().mean()
            if avg_chars < 50:
                continue

        avg_words = series.astype(str).str.split().str.len().mean()
        avg_chars = series.astype(str).str.len().mean()
        nunique = series.nunique()
        nunique_ratio = nunique / max(len(series), 1)
        has_text_hint = any(w in col_lower for w in ("feedback", "comment", "remark", "opinion", "suggestion", "improve", "like", "thought", "detail", "review", "experience", "note", "reason"))
        is_activity_list = any(k in col_lower for k in ("activity", "activities", "session", "track", "event attended", "attended", "tag")) and not has_text_hint

        is_text = False
        if is_activity_list:
            is_text = False
        elif avg_words >= 8 or avg_chars >= 50:
            is_text = True
        elif has_text_hint and (avg_words >= 3 or avg_chars >= 20):
            is_text = True
        elif avg_words >= 4 and (nunique_ratio > 0.2 or nunique >= 20):
            is_text = True

        if is_text:
            text_cols.append(col)
        else:
            categorical_cols.append(col)

    return rating_cols, text_cols, categorical_cols


def analyze_ratings(df: pd.DataFrame, rating_cols):
    out = {}
    for col in rating_cols:
        numeric = pd.to_numeric(df[col], errors="coerce").dropna()
        if numeric.empty:
            continue
        out[col] = {
            "average": round(float(numeric.mean()), 2),
            "min": float(numeric.min()),
            "max": float(numeric.max()),
            "count": int(numeric.count()),
            "distribution": {str(k): int(v) for k, v in numeric.value_counts().sort_index().items()},
        }
    return out


def analyze_categorical(df: pd.DataFrame, categorical_cols):
    out = {}
    for col in categorical_cols:
        counts = df[col].dropna().astype(str).value_counts().head(10)
        out[col] = {str(k): int(v) for k, v in counts.items()}
    return out


def clean_text_series(series: pd.Series):
    texts = series.dropna().astype(str)
    texts = texts[texts.str.strip().str.len() > 0]
    return texts.tolist()


def analyze_sentiment(texts):
    if not texts:
        return {"positive": 0, "neutral": 0, "negative": 0, "average_compound": 0.0, "per_response": []}
    scored = []
    pos = neu = neg = 0
    total_compound = 0.0
    for t in texts:
        s = _sia.polarity_scores(t)
        total_compound += s["compound"]
        if s["compound"] >= 0.05:
            pos += 1
            label = "positive"
        elif s["compound"] <= -0.05:
            neg += 1
            label = "negative"
        else:
            neu += 1
            label = "neutral"
        scored.append({"text": t, "compound": round(s["compound"], 3), "label": label})
    return {
        "positive": pos,
        "neutral": neu,
        "negative": neg,
        "average_compound": round(total_compound / len(texts), 3),
        "per_response": scored,
    }


def extract_keywords(texts, top_n=25):
    if len(texts) < 2:
        joined = " ".join(texts).lower()
        words = re.findall(r"[a-z']{3,}", joined)
        words = [w for w in words if w not in STOPWORDS]
        return Counter(words).most_common(top_n)
    vectorizer = TfidfVectorizer(stop_words="english", max_features=200, ngram_range=(1, 2))
    try:
        matrix = vectorizer.fit_transform(texts)
    except ValueError:
        return []
    scores = matrix.sum(axis=0).A1
    terms = vectorizer.get_feature_names_out()
    ranked = sorted(zip(terms, scores), key=lambda x: -x[1])[:top_n]
    return [(term, round(float(score), 2)) for term, score in ranked]


def extract_topics(texts, n_topics=4, n_words=6):
    if len(texts) < n_topics + 1:
        return []
    vectorizer = TfidfVectorizer(stop_words="english", max_features=300, min_df=1)
    try:
        matrix = vectorizer.fit_transform(texts)
    except ValueError:
        return []
    n_topics = min(n_topics, matrix.shape[0] - 1, matrix.shape[1] - 1)
    if n_topics < 1:
        return []
    model = TruncatedSVD(n_components=n_topics, random_state=42)
    model.fit(matrix)
    terms = vectorizer.get_feature_names_out()
    topics = []
    for i, comp in enumerate(model.components_):
        top_idx = comp.argsort()[-n_words:][::-1]
        words = [terms[j] for j in top_idx]
        topics.append({"topic": i + 1, "keywords": words})
    return topics


def generate_wordcloud_base64(texts):
    if not texts:
        return None
    joined = " ".join(texts)
    wc = WordCloud(width=900, height=450, background_color="white",
                    stopwords=STOPWORDS, collocations=False).generate(joined)
    buf = io.BytesIO()
    wc.to_image().save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def generate_extractive_summary(texts, sentiment_scores, n_sentences=5):
    """Fully local 'AI summary': picks the most representative/impactful
    sentences using TF-IDF centrality + sentiment intensity, no LLM call.
    Uses sparse vector dot-product for O(N) performance on large datasets."""
    if not texts:
        return "No free-text feedback was provided."
    if len(texts) <= n_sentences:
        picked = list(dict.fromkeys(t.strip() for t in texts if t.strip()))
    else:
        vectorizer = TfidfVectorizer(stop_words="english", max_features=1000)
        try:
            matrix = vectorizer.fit_transform(texts)
            # Mathematical identity: (M * M.T).sum(axis=1) == M.dot(M.sum(axis=0).T)
            # Avoids allocating dense N x N matrix (e.g. 12000x12000 = 1.15 GB)
            col_sums = matrix.sum(axis=0)
            prod = matrix.dot(col_sums.T)
            centrality = np.asarray(prod).ravel()
        except Exception:
            centrality = [0] * len(texts)
        intensity = [abs(s.get("compound", 0.0)) for s in sentiment_scores.get("per_response", [])] or [0] * len(texts)
        if len(intensity) < len(texts):
            intensity.extend([0] * (len(texts) - len(intensity)))
        combined = [c + 2 * i for c, i in zip(centrality, intensity)]
        ranked_idx = sorted(range(len(texts)), key=lambda i: -combined[i])
        picked = []
        seen = set()
        for i in ranked_idx:
            t = texts[i].strip()
            if t and t not in seen:
                seen.add(t)
                picked.append(t)
            if len(picked) >= n_sentences:
                break

    pos, neu, neg = sentiment_scores.get("positive", 0), sentiment_scores.get("neutral", 0), sentiment_scores.get("negative", 0)
    total = max(pos + neu + neg, 1)
    lead = (f"Overall sentiment leans {'positive' if pos >= neg else 'negative' if neg > pos else 'mixed'} "
            f"({pos}/{total} positive, {neg}/{total} negative responses). "
            f"Representative feedback includes:")
    bullets = "\n".join(f"- \"{t[:220]}\"" for t in picked)
    return f"{lead}\n{bullets}"


def run_full_analysis(df: pd.DataFrame):
    rating_cols, text_cols, categorical_cols = detect_column_types(df)
    ratings = analyze_ratings(df, rating_cols)
    categorical = analyze_categorical(df, categorical_cols)

    all_text = []
    for col in text_cols:
        all_text.extend(clean_text_series(df[col]))

    sentiment = analyze_sentiment(all_text)
    keywords = extract_keywords(all_text)
    topics = extract_topics(all_text)
    wordcloud_b64 = generate_wordcloud_base64(all_text)
    ai_summary = generate_extractive_summary(all_text, sentiment)

    return {
        "total_responses": int(len(df)),
        "columns_detected": {"rating": rating_cols, "text": text_cols, "categorical": categorical_cols},
        "ratings": ratings,
        "categorical": categorical,
        "sentiment": sentiment,
        "keywords": [{"term": t, "score": s} for t, s in keywords],
        "topics": topics,
        "wordcloud_image": wordcloud_b64,
        "ai_summary": ai_summary,
    }
