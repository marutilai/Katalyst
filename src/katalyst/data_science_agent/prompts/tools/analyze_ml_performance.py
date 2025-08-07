"""Prompt for the analyze_ml_performance tool."""

ANALYZE_ML_PERFORMANCE_PROMPT = """
Tool Name: analyze_ml_performance

Description: Extracts and analyzes machine learning model performance metrics from evaluation files. Can analyze single models or compare multiple models to find the best performer.

Parameters:
- metrics_file (optional): Path to specific metrics file. If not provided, searches for recent files with 'metric', 'score', 'result', 'performance', or 'evaluation' in the name.
- compare_all (optional): If True, analyzes and compares all found metrics files (up to 10 most recent). Default is False.

Returns: 
- Single file: Detailed metrics report with observations and warnings
- Multiple files: Comparison table with best model identification

Usage Examples:
```python
# Analyze most recent model
result = analyze_ml_performance()

# Analyze specific metrics file
result = analyze_ml_performance(metrics_file="models/xgboost_metrics.json")

# Compare all models in project
result = analyze_ml_performance(compare_all=True)
```

The tool automatically:
- Finds and parses various metric file formats (JSON, CSV, text)
- Extracts common ML metrics (accuracy, precision, recall, F1, AUC, RMSE, MAE, R²)
- Identifies model type from available metrics
- Highlights unusual patterns (e.g., accuracy > 99%, negative R²)
- Calculates metric relationships to reveal insights

Based on this analysis, you can determine:
- Whether the model is overfitting (large train-test gap)
- If there's class imbalance (precision/recall disparity)
- Whether outliers affect predictions (high RMSE/MAE ratio)
- How well the model performs compared to baselines
"""