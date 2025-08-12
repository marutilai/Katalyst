# Model Training Guide

## 1. AutoML Baseline
```python
# Start with AutoML for quick baseline
from autosklearn.classification import AutoSklearnClassifier

auto_clf = AutoSklearnClassifier(
    time_left_for_this_task=3600,  # 1 hour
    per_run_time_limit=300,
    ensemble_size=50,
    metric=autosklearn.metrics.roc_auc
)
auto_clf.fit(X_train, y_train)
print(f"AutoML AUC: {auto_clf.score(X_test, y_test):.3f}")

# Extract insights
for model, weight in auto_clf.get_models_with_weights():
    print(f"{model}: {weight:.3f}")
```

## 2. Quick Model Comparison
```python
from sklearn.model_selection import cross_val_score
import xgboost as xgb
import lightgbm as lgb

models = {
    'LogisticRegression': LogisticRegression(max_iter=1000),
    'RandomForest': RandomForestClassifier(n_estimators=100, n_jobs=-1),
    'XGBoost': xgb.XGBClassifier(n_estimators=100, use_label_encoder=False),
    'LightGBM': lgb.LGBMClassifier(n_estimators=100, verbosity=-1)
}

# Compare models
for name, model in models.items():
    score = cross_val_score(model, X_train, y_train, cv=5, scoring='roc_auc').mean()
    print(f"{name}: {score:.3f}")
```

## 3. Hyperparameter Tuning
```python
import optuna

# Optuna for efficient tuning
def objective(trial):
    params = {
        'n_estimators': trial.suggest_int('n_estimators', 100, 1000),
        'max_depth': trial.suggest_int('max_depth', 3, 15),
        'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.3, log=True),
        'subsample': trial.suggest_float('subsample', 0.6, 1.0),
        'colsample_bytree': trial.suggest_float('colsample_bytree', 0.6, 1.0)
    }
    
    model = xgb.XGBClassifier(**params, use_label_encoder=False, eval_metric='logloss')
    return cross_val_score(model, X_train, y_train, cv=5, scoring='roc_auc').mean()

study = optuna.create_study(direction='maximize')
study.optimize(objective, n_trials=100)
best_params = study.best_params
```

## 4. Training with Early Stopping
```python
X_tr, X_val, y_tr, y_val = train_test_split(X_train, y_train, test_size=0.2, stratify=y_train)

# XGBoost
model = xgb.XGBClassifier(**best_params, use_label_encoder=False)
model.fit(
    X_tr, y_tr,
    eval_set=[(X_val, y_val)],
    early_stopping_rounds=50,
    verbose=False
)

# LightGBM alternative
lgb_train = lgb.Dataset(X_tr, y_tr)
lgb_valid = lgb.Dataset(X_val, y_val, reference=lgb_train)

model = lgb.train(
    {'objective': 'binary', 'metric': 'auc', 'learning_rate': 0.05},
    lgb_train,
    valid_sets=[lgb_valid],
    callbacks=[lgb.early_stopping(50)]
)
```

## 5. Evaluation & Interpretation
```python
# Core metrics
y_pred_proba = model.predict_proba(X_test)[:, 1]
print(f"ROC-AUC: {roc_auc_score(y_test, y_pred_proba):.3f}")
print(classification_report(y_test, model.predict(X_test)))

# Feature importance
import shap
explainer = shap.TreeExplainer(model)
shap_values = explainer.shap_values(X_test)
shap.summary_plot(shap_values, X_test)

# Quick ROC plot
fpr, tpr, _ = roc_curve(y_test, y_pred_proba)
plt.plot(fpr, tpr, label=f'AUC={roc_auc_score(y_test, y_pred_proba):.3f}')
plt.plot([0,1], [0,1], 'k--')
plt.xlabel('FPR'); plt.ylabel('TPR'); plt.legend()
```


## 6. Cross-Validation Strategies
```python
# Stratified for imbalanced
skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
score = cross_val_score(model, X_train, y_train, cv=skf, scoring='roc_auc').mean()

# Time series
tscv = TimeSeriesSplit(n_splits=5)
for train_idx, val_idx in tscv.split(X_train):
    # Train on train_idx, validate on val_idx
    pass

# Custom split (e.g., by user)
unique_users = X['user_id'].unique()
train_users = np.random.choice(unique_users, size=int(0.8*len(unique_users)), replace=False)
train_mask = X['user_id'].isin(train_users)
```

## 7. Model Persistence
```python
import joblib

# Save with metadata
model_info = {
    'model': model,
    'features': list(X_train.columns),
    'params': best_params,
    'test_auc': roc_auc_score(y_test, y_pred_proba),
    'trained_at': datetime.now().isoformat()
}

joblib.dump(model_info, 'model_v1.pkl')

# Load and validate
loaded = joblib.load('model_v1.pkl')
assert loaded['features'] == list(X_test.columns), "Feature mismatch!"
```

## Quick Reference

| Step | Method | Key Point |
|------|--------|-----------|
| Baseline | AutoSklearn | 1-hour time box for benchmark |
| Compare | Cross-validation | Test 4-5 algorithm families |
| Tune | Optuna | 100 trials usually sufficient |
| Evaluate | SHAP + metrics | Interpret before deploying |
| Save | joblib + metadata | Track features & performance |

## Checklist
- [ ] AutoML baseline → Pick top 2 models → Tune with Optuna
- [ ] Use stratified CV for imbalanced, time series split for temporal
- [ ] Early stopping prevents overfitting in boosting models
- [ ] SHAP for feature importance, not just model.feature_importances_
- [ ] Save feature list with model to catch drift in production