# Data Exploration Guide

## 1. Quick Overview
```python
# Load and inspect
df = pd.read_csv('data.csv')
print(f"Shape: {df.shape}")
df.head()
df.info()
df.describe(include='all')

# Missing values
missing_pct = (df.isnull().sum() / len(df)) * 100
print(missing_pct[missing_pct > 0].sort_values(ascending=False))
sns.heatmap(df.isnull(), cbar=True, yticklabels=False)
```
**Decision**: Drop if >50% missing

## 2. Distribution Analysis
```python
# Check skewness for numeric columns
for col in df.select_dtypes(include='number'):
    skew = df[col].skew()
    if abs(skew) > 0.75:
        print(f"{col}: skew={skew:.2f} - consider transform")

# Visualizations
df.hist(figsize=(12, 8), bins=30)
# Optional: sns.pairplot(), boxplots, violinplots for deeper analysis
```

## 3. Categorical & Target Analysis
```python
# Categorical overview
for col in df.select_dtypes('object'):
    print(f"\n{col}: {df[col].nunique()} unique")
    if df[col].nunique() < 20:
        print(df[col].value_counts().head())

# Target variable
if 'target' in df.columns:
    if df['target'].dtype in ['int64', 'float64']:
        print(f"Target skew: {df['target'].skew():.2f}")
        df['target'].hist(bins=50)
    else:
        print(df['target'].value_counts(normalize=True))
        imbalance = df['target'].value_counts().max() / df['target'].value_counts().min()
        print(f"Imbalance ratio: {imbalance:.2f}")
```

## 4. Correlation & Feature-Target Analysis
```python
# Correlation matrix
corr = df.corr()
sns.heatmap(corr, mask=np.triu(np.ones_like(corr), k=1), 
            annot=True, fmt='.2f', cmap='coolwarm')

# High correlations warning
high_corr = (corr.abs() > 0.8).sum() - 1
print(f"Features with |corr| > 0.8: {high_corr[high_corr > 0]}")

# Feature-target relationships
if 'target' in df.columns:
    target_corr = df.corr()['target'].sort_values(ascending=False)
    print(target_corr.head(10))
    
    # Visualize top correlations
    for feat in target_corr.abs().nlargest(4).index[1:]:
        df.plot.scatter(x=feat, y='target', alpha=0.5)
```

## 5. Outlier Detection
```python
# IQR method
for col in df.select_dtypes('number'):
    Q1, Q3 = df[col].quantile([0.25, 0.75])
    IQR = Q3 - Q1
    outliers = ((df[col] < Q1 - 1.5*IQR) | (df[col] > Q3 + 1.5*IQR)).sum()
    if outliers > 0:
        print(f"{col}: {outliers} outliers ({outliers/len(df)*100:.1f}%)")
```

## 6. Text Data Analysis (if present)
```python
# Identify text columns (avg length > 20 chars)
for col in df.select_dtypes('object').columns:
    if df[col].str.len().mean() > 20:
        print(f"\n{col}: Avg length={df[col].str.len().mean():.0f}, Missing={df[col].isnull().sum()}")
        # Word analysis
        words = ' '.join(df[col].dropna()).split()
        print(f"  Words: {len(words)} total, {len(set(words))} unique")
        from collections import Counter
        print(f"  Top 5: {Counter(words).most_common(5)}")
```

## 7. Datetime Analysis (if present)
```python
# Find/convert datetime columns
date_cols = df.select_dtypes(include=['datetime64']).columns.tolist()
for col in df.select_dtypes('object').columns:
    try:
        df[col] = pd.to_datetime(df[col])
        date_cols.append(col)
    except:
        pass

# Analyze datetime features
for col in date_cols:
    print(f"\n{col}: {df[col].min()} to {df[col].max()} ({(df[col].max() - df[col].min()).days} days)")
    # Extract time components
    df[f'{col}_year'] = df[col].dt.year
    df[f'{col}_month'] = df[col].dt.month
    df[f'{col}_dayofweek'] = df[col].dt.dayofweek
    # Plot target trend if available
    if 'target' in df.columns:
        df.groupby(df[col].dt.to_period('M'))['target'].mean().plot()
```

## 8. Multivariate Relationships
```python
# Categorical interactions with target
cat_cols = [col for col in df.select_dtypes('object').columns if df[col].nunique() < 10]
if 'target' in df.columns and len(cat_cols) > 1:
    # Create pivot tables for top categorical pairs
    for col1, col2 in [(cat_cols[i], cat_cols[j]) 
                       for i in range(min(2, len(cat_cols))) 
                       for j in range(i+1, min(3, len(cat_cols)))]:
        pivot = df.pivot_table(values='target', index=col1, columns=col2, aggfunc='mean')
        print(f"\nTarget mean by {col1} x {col2}:\n{pivot.round(2)}")
```

## Quick Reference

| Section | Key Insight | Action Threshold |
|---------|-------------|------------------|
| Overview | Missing values, shape | >50% missing → drop |
| Distributions | Skewness | >0.75 → transform |
| Categoricals | Cardinality, imbalance | >100 unique → embed |
| Correlations | Feature redundancy | >0.8 → drop one |
| Outliers | Data quality | >5% → investigate |
| Text Data | Length patterns | >20 chars → NLP |
| Datetime | Trends | Seasonality → features |
| Multivariate | Interactions | Strong → feature eng |