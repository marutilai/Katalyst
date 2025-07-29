# Model Evaluation Guide

## 1. Metric Selection
```python
# Regression: r2, neg_mean_squared_error, neg_mean_absolute_error
# Classification: accuracy, precision, recall, f1, roc_auc
# Imbalanced: f1_weighted, balanced_accuracy, average_precision
```

## 2. Regression Metrics
```python
# R²: variance explained (higher=better)
# RMSE: sqrt(MSE), penalizes large errors
# MAE: mean absolute error
print(f"R²: {r2_score(y_true, y_pred):.3f}")
print(f"RMSE: {np.sqrt(mean_squared_error(y_true, y_pred)):.3f}")
```

## 3. Classification Metrics
```python
print(classification_report(y_true, y_pred))

# Confusion matrix heatmap
sns.heatmap(confusion_matrix(y_true, y_pred), annot=True, fmt='d')

# ROC-AUC for probability predictions
auc = roc_auc_score(y_true, y_proba[:, 1])  # binary
```

## 4. Cross-Validation Evaluation
```python
# Multiple metrics
cv_results = cross_validate(model, X, y, cv=5, scoring=['r2', 'neg_rmse'])
for metric, scores in cv_results.items():
    if 'test_' in metric:
        print(f"{metric}: {scores.mean():.3f} ± {scores.std():.3f}")
```

## 5. Holdout Validation
```python
cv_score = cross_val_score(model, X_train, y_train, cv=5).mean()
holdout_score = model.score(X_test, y_test)
print(f"Overfit indicator: {cv_score - holdout_score:.3f}")
```

## 6. Error Distribution
```python
# Regression: plot residuals
residuals = y_true - y_pred
plt.scatter(y_pred, residuals, alpha=0.5)
plt.axhline(0, color='red', linestyle='--')

# Classification: analyze misclassified
misclassified_idx = y_test != y_pred
print(f"Error rate: {misclassified_idx.mean():.1%}")
```

## 7. Threshold Tuning
```python
# Find threshold for target metric
precision, recall, thresholds = precision_recall_curve(y_true, y_proba[:, 1])
idx = np.argmax(recall >= 0.80)  # 80% recall target
optimal_threshold = thresholds[idx]
y_pred_custom = (y_proba[:, 1] >= optimal_threshold)
```

## 8. Model Comparison
```python
results = {}
for name, model in models.items():
    cv_scores = cross_val_score(model, X, y, cv=5, scoring='f1')
    results[name] = f"{cv_scores.mean():.3f} ± {cv_scores.std():.3f}"
pd.Series(results).sort_values(ascending=False)
```

## 9. Explainability
```python
# Feature importance or SHAP
# Tree: model.feature_importances_
# Linear: abs(model.coef_)
# SHAP: shap.TreeExplainer(model).shap_values(X)
```

## 10. Business Impact
```python
# Cost-benefit matrix
costs = {'TP': 100, 'FP': -20, 'FN': -50, 'TN': 0}
cm = confusion_matrix(y_true, y_pred)
value = (cm[1,1] * costs['TP'] + cm[0,1] * costs['FP'] + 
         cm[1,0] * costs['FN'] + cm[0,0] * costs['TN'])
print(f"Business value: ${value:,}")
```

## Quick Reference

| Task | Key Metrics | Red Flags |
|------|-------------|-----------|
| Regression | R², RMSE, MAE | R² < 0 (worse than mean) |
| Binary Classification | Precision, Recall, F1, AUC | F1 << Accuracy (imbalance) |
| Multiclass | Weighted F1, Confusion Matrix | Poor performance on minority classes |
| Imbalanced | Balanced Accuracy, PR-AUC | ROC-AUC misleading |
| Business Alignment | Custom KPIs | Metric improvement ≠ business value |

## Evaluation Checklist
- [ ] Metrics match business objectives
- [ ] Cross-validation performed
- [ ] Holdout set validates performance
- [ ] Error patterns analyzed
- [ ] Threshold optimized (if applicable)
- [ ] Models compared fairly
- [ ] Feature importance reviewed
- [ ] Business impact quantified