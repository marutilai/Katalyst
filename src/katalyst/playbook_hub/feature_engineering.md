# Feature Engineering Guide

## 1. Advanced Numerical Transformations
```python
# Skewness correction (check with df['col'].skew() > 0.75)
df['log_col'] = np.log1p(df['col'])  # log transform
df['sqrt_col'] = np.sqrt(np.abs(df['col']))  # square root
# Advanced: Box-Cox or Yeo-Johnson for flexibility
from sklearn.preprocessing import PowerTransformer
pt = PowerTransformer(method='yeo-johnson')
df['col_yj'] = pt.fit_transform(df[['col']])

# Binning strategies
df['col_bins'] = pd.qcut(df['col'], q=5, labels=['VL','L','M','H','VH'])
# Target-based binning (finds optimal splits)
from sklearn.tree import DecisionTreeRegressor
dt = DecisionTreeRegressor(max_depth=3)
dt.fit(df[['feature']], df['target'])
df['feature_tree_bin'] = dt.predict(df[['feature']])

# Interaction detection (mutual information)
from sklearn.feature_selection import mutual_info_regression
# Create interactions for features with high MI scores
top_features = ['feat1', 'feat2', 'feat3']  # based on MI analysis
for i, f1 in enumerate(top_features[:-1]):
    for f2 in top_features[i+1:]:
        df[f'{f1}_x_{f2}'] = df[f1] * df[f2]
        df[f'{f1}_div_{f2}'] = df[f1] / (df[f2] + 1e-8)
```

## 2. Group-Based Aggregations
```python
# Multi-level aggregations
agg_funcs = ['mean', 'std', 'min', 'max', 'count']
group_stats = df.groupby('user_id')['amount'].agg(agg_funcs)
group_stats.columns = [f'user_amount_{f}' for f in agg_funcs]
df = df.merge(group_stats, on='user_id', how='left')

# Time-windowed features
df['rolling_mean_7d'] = (df.groupby('user_id')['value']
                          .transform(lambda x: x.rolling('7D').mean()))
df['expanding_sum'] = (df.groupby('user_id')['value']
                       .transform(lambda x: x.expanding().sum()))

# Lag features for time series
for lag in [1, 7, 30]:
    df[f'value_lag_{lag}'] = df.groupby('user_id')['value'].shift(lag)
```

## 3. Categorical & Text Features
```python
# Encoding strategies by cardinality
for col in categorical_cols:
    n_unique = df[col].nunique()
    if n_unique < 10:
        # One-hot for low cardinality
        df = pd.get_dummies(df, columns=[col], prefix=col)
    elif n_unique < 100:
        # Target encoding with smoothing
        smooth = 10
        mean = df['target'].mean()
        agg = df.groupby(col)['target'].agg(['count', 'mean'])
        smooth_mean = (agg['count'] * agg['mean'] + smooth * mean) / (agg['count'] + smooth)
        df[f'{col}_target_enc'] = df[col].map(smooth_mean)
    else:
        # Feature hashing for high cardinality
        from sklearn.feature_extraction import FeatureHasher
        hasher = FeatureHasher(n_features=32, input_type='string')
        hashed = hasher.transform(df[[col]].astype(str).values)
        df[f'{col}_hash'] = hashed.toarray().sum(axis=1)

# Text features
df['text_len'] = df['text'].str.len()
df['word_count'] = df['text'].str.split().str.len()
df['capital_ratio'] = df['text'].str.count('[A-Z]') / (df['text_len'] + 1)
# TF-IDF for important terms
from sklearn.feature_extraction.text import TfidfVectorizer
tfidf = TfidfVectorizer(max_features=20, ngram_range=(1,2))
text_features = tfidf.fit_transform(df['text']).toarray()
```

## 4. DateTime & Cyclical Features
```python
# Cyclical encoding for periodic features
df['hour_sin'] = np.sin(2 * np.pi * df['hour'] / 24)
df['hour_cos'] = np.cos(2 * np.pi * df['hour'] / 24)
df['month_sin'] = np.sin(2 * np.pi * df['month'] / 12)
df['month_cos'] = np.cos(2 * np.pi * df['month'] / 12)

# Time-based patterns
df['is_weekend'] = df['dayofweek'].isin([5, 6]).astype(int)
df['is_month_end'] = df['day'].isin([28, 29, 30, 31]).astype(int)
df['days_since_last_event'] = (df.groupby('user_id')['date']
                                .diff().dt.days.fillna(0))

# Missing value patterns
for col in df.columns:
    if df[col].isnull().sum() > 0:
        df[f'{col}_was_missing'] = df[col].isnull().astype(int)
        # Impute based on type
        if df[col].dtype in ['float64', 'int64']:
            df[col].fillna(df[col].median(), inplace=True)
        else:
            df[col].fillna('missing', inplace=True)
```

## 5. Feature Selection & Validation
```python
# Variance threshold
from sklearn.feature_selection import VarianceThreshold
vt = VarianceThreshold(threshold=0.01)
low_var_features = df.columns[~vt.fit(df).get_support()]

# Mutual information scores
from sklearn.feature_selection import mutual_info_classif
mi_scores = mutual_info_classif(df[features], df['target'])
top_features = pd.Series(mi_scores, index=features).nlargest(50)

# Check for leakage
for feat in features:
    if df[feat].corr(df['target']) > 0.95:
        print(f"WARNING: {feat} may have leakage!")

# Recursive feature elimination
from sklearn.feature_selection import RFE
from sklearn.ensemble import RandomForestClassifier
rfe = RFE(RandomForestClassifier(n_estimators=50), n_features_to_select=30)
selected = rfe.fit(df[features], df['target']).support_
```

## Quick Reference

| Situation | Technique | Key Point |
| Skewed numeric | PowerTransformer | Handles negative values unlike log |
| High cardinality | Feature hashing | Preserves information, fixed size |
| Time patterns | Cyclical encoding | sin/cos preserves continuity |
| Group features | Aggregations + CV | Prevents leakage with proper splits |
| Text data | TF-IDF + stats | Combine semantic and structural |
| Feature explosion | MI + RFE | Select informative features only |

## Production Checklist
- [ ] Save all transformers (scalers, encoders) for inference
- [ ] Check train/test distribution shift with KS test
- [ ] Version control feature definitions
- [ ] Monitor feature drift in production
- [ ] Document feature dependencies and compute order

## Advanced Tips
1. **Embeddings**: For high-cardinality categoricals, use entity embeddings from neural nets
2. **Auto-FE**: Try featuretools for automated feature generation
3. **Domain Features**: Always prioritize domain knowledge over statistical patterns
4. **Feature Stores**: Consider using Feast or similar for production ML