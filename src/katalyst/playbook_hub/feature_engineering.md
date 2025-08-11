# Feature Engineering Guide

## 1. Numerical Transformations
```python
# Skewness correction (if skew > 0.75)
from sklearn.preprocessing import PowerTransformer
pt = PowerTransformer(method='yeo-johnson')  # handles negatives
df['col_transformed'] = pt.fit_transform(df[['col']])

# Binning (for non-linear relationships)
df['col_bins'] = pd.qcut(df['col'], q=5, labels=['VL','L','M','H','VH'])

# Create interactions based on mutual information scores
from sklearn.feature_selection import mutual_info_regression
mi_scores = mutual_info_regression(df[numeric_features], df['target'])
top_features = numeric_features[mi_scores.argsort()[-5:]]  # top 5

for i, f1 in enumerate(top_features[:-1]):
    for f2 in top_features[i+1:]:
        df[f'{f1}_x_{f2}'] = df[f1] * df[f2]
```

## 2. Aggregations & Time Features
```python
# Group aggregations
agg_funcs = ['mean', 'std', 'min', 'max']
group_stats = df.groupby('user_id')['amount'].agg(agg_funcs)
group_stats.columns = [f'user_amount_{f}' for f in agg_funcs]
df = df.merge(group_stats, on='user_id', how='left')

# Time-based features (crucial for temporal data)
df['rolling_mean_7d'] = df.groupby('user_id')['value'].transform(
    lambda x: x.rolling('7D').mean()
)

# Lag features for time series
for lag in [1, 7, 30]:
    df[f'value_lag_{lag}'] = df.groupby('user_id')['value'].shift(lag)
```

## 3. Categorical Encoding
```python
# Choose encoding by cardinality
n_unique = df[col].nunique()

if n_unique < 10:
    # One-hot encoding
    df = pd.get_dummies(df, columns=[col], prefix=col)
elif n_unique < 100:
    # Target encoding with smoothing
    mean = df['target'].mean()
    agg = df.groupby(col)['target'].agg(['count', 'mean'])
    smooth_mean = (agg['count'] * agg['mean'] + 10 * mean) / (agg['count'] + 10)
    df[f'{col}_target_enc'] = df[col].map(smooth_mean)
else:
    # Very high cardinality: feature hashing
    from sklearn.feature_extraction import FeatureHasher
    hasher = FeatureHasher(n_features=32, input_type='string')
    hashed = hasher.transform(df[[col]].astype(str).values)
    df[f'{col}_hash'] = hashed.toarray().sum(axis=1)
```

## 4. Missing Values & DateTime
```python
# Missing value imputation (based on percentage from exploration)
missing_pct = df.isnull().sum() / len(df) * 100

for col in df.columns:
    if missing_pct[col] > 0:
        df[f'{col}_was_missing'] = df[col].isnull().astype(int)
        
        if missing_pct[col] > 30:
            print(f"Dropping {col}: {missing_pct[col]:.1f}% missing")
            df.drop(col, axis=1, inplace=True)
        elif df[col].dtype in ['float64', 'int64']:
            df[col].fillna(df[col].median(), inplace=True)
        else:
            df[col].fillna(df[col].mode()[0], inplace=True)

# Cyclical encoding for time
df['hour_sin'] = np.sin(2 * np.pi * df['hour'] / 24)
df['hour_cos'] = np.cos(2 * np.pi * df['hour'] / 24)

```

## 5. Text Features (if applicable)
```python
# Basic text statistics
df['text_len'] = df['text'].str.len()
df['word_count'] = df['text'].str.split().str.len()

# TF-IDF for important terms
from sklearn.feature_extraction.text import TfidfVectorizer
tfidf = TfidfVectorizer(max_features=20, ngram_range=(1,2))
text_features = tfidf.fit_transform(df['text']).toarray()
```

## 6. Feature Selection
```python
# Remove low variance features
from sklearn.feature_selection import VarianceThreshold
vt = VarianceThreshold(threshold=0.01)
selected_features = df.columns[vt.fit(df).get_support()]

# Mutual information for feature importance
from sklearn.feature_selection import mutual_info_classif
mi_scores = mutual_info_classif(df[features], df['target'])
top_features = pd.Series(mi_scores, index=features).nlargest(30)

# Check for leakage (correlation > 0.95)
high_corr = df.corr()['target'].abs() > 0.95
if high_corr.any():
    print(f"WARNING: Possible leakage in {high_corr[high_corr].index.tolist()}")
```

## Quick Reference

| Situation | Technique | Key Point |
| Missing values (<10%) | Median/mode impute | Simple and effective for low missingness |
| Missing values (10-30%) | KNN/iterative impute | Uses feature relationships |
| Missing values (>30%) | Drop or indicator | Consider dropping or missingness as feature |
| Missing categorical | Mode or 'missing' category | Preserve information about missingness |
| Missing time-based | Forward/backward fill | Respects temporal patterns |
| Skewed numeric | PowerTransformer | Handles negative values unlike log |
| High cardinality | Feature hashing | Preserves information, fixed size |
| Time patterns | Cyclical encoding | sin/cos preserves continuity |
| Group features | Aggregations + CV | Prevents leakage with proper splits |
| Text data | TF-IDF + stats | Combine semantic and structural |
| Feature explosion | MI + RFE | Select informative features only |

## Key Reminders
- Save all transformers (scalers, encoders) for inference
- Check train/test distribution consistency
- Document feature dependencies
- Prioritize domain knowledge over complex transformations