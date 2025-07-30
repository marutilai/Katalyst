# Data Exploration Guide

## 1. Initial Data Loading & Preview
```python
df = pd.read_csv('data.csv')
print(f"Shape: {df.shape}")
print(df.head())
print(df.sample(5))  # Random sample
```

## 2. Data Structure & Types
```python
df.info()  # Overview
print(df.dtypes.value_counts())  # Type distribution
```

## 3. Missing Value Analysis
```python
missing_pct = (df.isnull().sum() / len(df)) * 100
print(missing_pct[missing_pct > 0].sort_values(ascending=False))

# Visual pattern
sns.heatmap(df.isnull(), cbar=True, yticklabels=False)
```
**Decision**: Drop if >50% missing

## 4. Descriptive Statistics
```python
df.describe()  # Numeric
df.describe(include='all')  # All columns
```

## 5. Distribution Analysis
```python
# Check skewness for numeric columns
for col in df.select_dtypes(include='number'):
    skew = df[col].skew()
    if abs(skew) > 0.75:
        print(f"{col}: skew={skew:.2f} - consider transform")
    
# Quick histograms
df.hist(figsize=(12, 8), bins=30)
```

## 6. Categorical Analysis
```python
for col in df.select_dtypes('object'):
    print(f"\n{col}: {df[col].nunique()} unique")
    if df[col].nunique() < 20:
        print(df[col].value_counts().head())
```

## 7. Target Variable Analysis
```python
# Regression
if df['target'].dtype in ['int64', 'float64']:
    print(f"Target skew: {df['target'].skew():.2f}")
    df['target'].hist(bins=50)
    
# Classification  
else:
    print(df['target'].value_counts(normalize=True))
    imbalance = df['target'].value_counts().max() / df['target'].value_counts().min()
    print(f"Imbalance ratio: {imbalance:.2f}")
```

## 8. Correlation Analysis
```python
corr = df.corr()
# Heatmap
sns.heatmap(corr, mask=np.triu(np.ones_like(corr), k=1), 
            annot=True, fmt='.2f', cmap='coolwarm')

# High correlations
high_corr = (corr.abs() > 0.8).sum() - 1  # Subtract diagonal
print(f"Features with |corr| > 0.8: {high_corr[high_corr > 0]}")
```

## 9. Feature-Target Relationships
```python
# Numeric features
if 'target' in df.columns:
    target_corr = df.corr()['target'].sort_values(ascending=False)
    print(target_corr.head(10))
    
    # Plot top 3
    for feat in target_corr.abs().nlargest(4).index[1:]:
        df.plot.scatter(x=feat, y='target', alpha=0.5)
```

## 10. Outlier Detection
```python
# IQR method
for col in df.select_dtypes('number'):
    Q1, Q3 = df[col].quantile([0.25, 0.75])
    IQR = Q3 - Q1
    outliers = ((df[col] < Q1 - 1.5*IQR) | (df[col] > Q3 + 1.5*IQR)).sum()
    if outliers > 0:
        print(f"{col}: {outliers} outliers ({outliers/len(df)*100:.1f}%)")
```

## Quick Reference

| Technique | Key Code | What to Look For |
|-----------|----------|------------------|
| Data Preview | `df.head()`, `df.sample()` | Anomalies, wrong types |
| Shape & Info | `df.shape`, `df.info()` | Size, memory usage |
| Missing Values | `df.isnull().sum()` | Patterns, >50% missing |
| Statistics | `df.describe()` | Outliers, skewness |
| Value Counts | `df['col'].value_counts()` | Imbalance, cardinality |
| Distributions | Histograms, boxplots | Skewness >0.75, outliers |
| Correlations | `df.corr()`, heatmap | >0.8 correlation pairs |
| Target Analysis | Distribution plots | Transformation needs |
| Feature-Target | Scatter plots, grouped means | Strong relationships |
| Outliers | IQR method | >5% outliers warning |

## Exploration Checklist
1. ✓ Loaded data and checked shape
2. ✓ Verified data types are correct
3. ✓ Analyzed missing value patterns
4. ✓ Reviewed descriptive statistics
5. ✓ Visualized distributions
6. ✓ Examined target variable
7. ✓ Calculated correlations
8. ✓ Explored feature-target relationships
9. ✓ Identified outliers
10. ✓ Documented key findings

## Key Decisions from Exploration
- Which features to keep/drop?
- What transformations are needed?
- How to handle missing values?
- Which encoding for categoricals?
- What evaluation metric to use?
- Any data quality issues to fix?