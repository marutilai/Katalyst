# Feature Engineering Guide

When engineering features, follow these critical patterns:

## Initial Analysis
1. Use `pandas.describe()` and check data distributions
2. Identify: numerical vs categorical, missing patterns, skewness
3. Check target correlation with existing features

## Core Techniques by Data Type

### Numerical Features
```python
# Skewed data (check with df['col'].skew() > 0.75)
df['log_col'] = np.log1p(df['col'])  # log transform
df['sqrt_col'] = np.sqrt(df['col'])  # square root for moderate skew

# Create bins for non-linear relationships
df['col_bins'] = pd.qcut(df['col'], q=5, labels=['very_low','low','med','high','very_high'])

# Simple interactions (if domain knowledge suggests)
df['feature_product'] = df['feature1'] * df['feature2']
df['feature_ratio'] = df['numerator'] / (df['denominator'] + 1)  # avoid division by zero
```

### Categorical Features
```python
# Low cardinality (<20 unique): One-hot encode
pd.get_dummies(df['category'], prefix='cat')

# High cardinality: Target encoding with CV
from sklearn.model_selection import KFold
for fold, (train_idx, val_idx) in enumerate(KFold(5).split(df)):
    mean_target = df.iloc[train_idx].groupby('category')['target'].mean()
    df.loc[val_idx, 'category_encoded'] = df.iloc[val_idx]['category'].map(mean_target)

# Ordinal: Map to numbers
df['size_num'] = df['size'].map({'small': 1, 'medium': 2, 'large': 3, 'extra_large': 4})
```

### Missing Values
```python
# Create indicator if missingness is informative
df['has_feature_x'] = df['feature_x'].notna().astype(int)

# Then impute appropriately
df['feature_x'].fillna(df['feature_x'].median(), inplace=True)  # numerical
df['category_y'].fillna('missing', inplace=True)  # categorical
```

### DateTime Features
```python
# Extract components
df['year'] = pd.to_datetime(df['timestamp']).dt.year
df['month'] = pd.to_datetime(df['timestamp']).dt.month
df['day_of_week'] = pd.to_datetime(df['timestamp']).dt.dayofweek
df['hour'] = pd.to_datetime(df['timestamp']).dt.hour

# Time differences
df['days_since_event'] = (pd.Timestamp.now() - df['event_date']).dt.days
df['time_between_events'] = df['timestamp'].diff().dt.total_seconds() / 3600  # hours
```

## Quick Decision Guide

| Situation | Technique | Example |
|-----------|-----------|---------|
| Skewed numeric (skew > 0.75) | Log transform | `np.log1p(df['amount'])` |
| Non-monotonic relationship | Binning | `pd.qcut(df['numeric_col'], 5)` |
| Two features interact | Multiply/divide | `df['rate'] = df['distance'] / df['time']` |
| Many categories (>20) | Target encode | Use KFold to avoid leakage |
| Missing is meaningful | Add indicator | `df['has_data'] = df['col'].notna()` |
| Need feature importance | Don't over-engineer | Start simple, iterate |

## Validation Checklist
- ✓ No data leakage (especially in target encoding)
- ✓ Features make domain sense
- ✓ Validated on holdout set
- ✓ Computation is reproducible
- ✓ Document feature definitions

## Common Pitfalls
- Creating too many features without validation
- Target encoding without cross-validation
- Using future information (data leakage)
- Over-engineering before establishing baseline