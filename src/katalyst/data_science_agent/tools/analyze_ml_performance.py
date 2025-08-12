"""
Tool for extracting and analyzing ML model performance metrics.
"""

import os
import json
import re
from typing import Optional, Dict, Any, List
from katalyst.katalyst_core.utils.tools import katalyst_tool
from katalyst.katalyst_core.utils.logger import get_logger

logger = get_logger("analyze_ml_performance")


@katalyst_tool(
    prompt_module="analyze_ml_performance",
    prompt_var="ANALYZE_ML_PERFORMANCE_PROMPT",
    categories=["replanner"]
)
def analyze_ml_performance(
    metrics_file: Optional[str] = None,
    compare_all: bool = False,
    project_root_cwd: Optional[str] = None
) -> str:
    """
    Extract and analyze ML model performance metrics.
    
    Args:
        metrics_file: Path to specific metrics file. If None, finds most recent.
        compare_all: If True, analyzes all found metrics files for comparison
        project_root_cwd: Project root directory
    
    Returns:
        Structured analysis of model performance metrics
    """
    project_root = project_root_cwd or os.getcwd()
    
    # Find metrics files
    potential_files = _find_metrics_files(project_root)
    
    if not potential_files:
        return "No metrics files found. Please provide a metrics_file path or ensure model evaluation results are saved."
    
    # Determine which files to analyze
    if metrics_file:
        # Specific file requested
        files_to_analyze = [metrics_file]
    elif compare_all:
        # Analyze all found files
        files_to_analyze = potential_files[:10]  # Limit to 10 most recent
    else:
        # Just the most recent
        files_to_analyze = [max(potential_files, key=os.path.getmtime)]
    
    # Analyze each file
    all_results = []
    for file_path in files_to_analyze:
        result = _analyze_single_file(file_path, project_root)
        if result:
            all_results.append(result)
    
    if not all_results:
        return "Failed to analyze any metrics files."
    
    # Generate report
    if len(all_results) == 1:
        # Single file report
        metrics, model_type, file_path = all_results[0]
        return _generate_structured_report(metrics, model_type, file_path)
    else:
        # Comparison report
        return _generate_comparison_report(all_results)


def _parse_text_metrics(content: str) -> Dict[str, Any]:
    """Parse metrics from text content."""
    metrics = {}
    
    # Common patterns
    patterns = {
        'accuracy': r'accuracy[:\s]+([0-9.]+)',
        'precision': r'precision[:\s]+([0-9.]+)',
        'recall': r'recall[:\s]+([0-9.]+)',
        'f1': r'f1[:\s-]+([0-9.]+)',
        'auc': r'(?:auc|roc)[:\s]+([0-9.]+)',
        'rmse': r'rmse[:\s]+([0-9.]+)',
        'mae': r'mae[:\s]+([0-9.]+)',
        'r2': r'r2[:\s]+([0-9.]+)',
        'loss': r'loss[:\s]+([0-9.]+)',
    }
    
    for metric, pattern in patterns.items():
        match = re.search(pattern, content.lower())
        if match:
            metrics[metric] = float(match.group(1))
    
    return metrics


def _infer_model_type(metrics: Dict[str, Any]) -> str:
    """Infer model type from available metrics."""
    classification_metrics = {'accuracy', 'precision', 'recall', 'f1', 'auc'}
    regression_metrics = {'rmse', 'mae', 'r2', 'mse'}
    
    metric_keys = set(metrics.keys())
    
    if metric_keys & classification_metrics:
        return 'classification'
    elif metric_keys & regression_metrics:
        return 'regression'
    else:
        return 'unknown'


def _generate_structured_report(metrics: Dict[str, Any], model_type: str, metrics_file: str) -> str:
    """Generate structured metrics report."""
    report = "# ML Performance Metrics Report\n\n"
    report += f"**Metrics File**: {metrics_file}\n"
    report += f"**Model Type**: {model_type}\n\n"
    
    report += "## Performance Metrics\n"
    for metric, value in sorted(metrics.items()):
        if isinstance(value, float):
            report += f"- **{metric.upper()}**: {value:.4f}\n"
        else:
            report += f"- **{metric.upper()}**: {value}\n"
    
    report += "\n## Key Observations\n"
    
    if model_type == 'classification':
        report += _analyze_classification_patterns(metrics)
    elif model_type == 'regression':
        report += _analyze_regression_patterns(metrics)
    
    # Add comparative analysis if train/test metrics available
    if 'train_accuracy' in metrics and 'test_accuracy' in metrics:
        gap = metrics['train_accuracy'] - metrics['test_accuracy']
        report += "\n### Train-Test Gap\n"
        report += f"- Training: {metrics['train_accuracy']:.4f}\n"
        report += f"- Testing: {metrics['test_accuracy']:.4f}\n"
        report += f"- Gap: {gap:.4f}\n"
    
    return report


def _analyze_classification_patterns(metrics: Dict[str, Any]) -> str:
    """Extract key patterns from classification metrics."""
    observations = ""
    
    accuracy = metrics.get('accuracy', 0)
    precision = metrics.get('precision', 0)
    recall = metrics.get('recall', 0)
    f1 = metrics.get('f1', 0)
    auc = metrics.get('auc', 0)
    
    # Report metric values and relationships
    if accuracy > 0:
        observations += f"- Overall accuracy: {accuracy:.1%}\n"
    
    if precision > 0 and recall > 0:
        observations += f"- Precision-Recall balance: {precision:.3f} vs {recall:.3f} (diff: {abs(precision-recall):.3f})\n"
    
    if f1 > 0:
        observations += f"- F1 Score: {f1:.3f}\n"
    
    if auc > 0:
        observations += f"- AUC-ROC: {auc:.3f}\n"
    
    # Check for extreme values that might indicate issues
    if accuracy > 0.99:
        observations += "- ⚠️ Accuracy > 99% (unusual)\n"
    
    if precision > 0 and recall > 0:
        ratio = precision / recall if recall > 0 else float('inf')
        if ratio > 2 or ratio < 0.5:
            observations += f"- ⚠️ Large precision/recall imbalance (ratio: {ratio:.2f})\n"
    
    return observations


def _analyze_regression_patterns(metrics: Dict[str, Any]) -> str:
    """Extract key patterns from regression metrics."""
    observations = ""
    
    rmse = metrics.get('rmse', None)
    mae = metrics.get('mae', None)
    r2 = metrics.get('r2', None)
    mse = metrics.get('mse', None)
    
    # Report available metrics
    if r2 is not None:
        observations += f"- R² Score: {r2:.4f}\n"
    
    if rmse is not None:
        observations += f"- RMSE: {rmse:.4f}\n"
    
    if mae is not None:
        observations += f"- MAE: {mae:.4f}\n"
    
    if mse is not None:
        observations += f"- MSE: {mse:.4f}\n"
    
    # Calculate relationships between metrics
    if rmse is not None and mae is not None and mae > 0:
        ratio = rmse / mae
        observations += f"- RMSE/MAE ratio: {ratio:.2f}\n"
        if ratio > 1.5:
            observations += "- ⚠️ High RMSE/MAE ratio suggests outlier influence\n"
    
    # Flag extreme values
    if r2 is not None:
        if r2 > 0.99:
            observations += "- ⚠️ R² > 0.99 (unusual)\n"
        elif r2 < 0:
            observations += "- ⚠️ Negative R² (model worse than mean baseline)\n"
    
    return observations




def _find_metrics_files(project_root: str) -> List[str]:
    """Find all potential metrics files in project."""
    potential_files = []
    for root, _, files in os.walk(project_root):
        for file in files:
            if any(pattern in file.lower() for pattern in ['metric', 'score', 'result', 'performance', 'evaluation']):
                if file.endswith(('.json', '.csv', '.txt', '.log')):
                    potential_files.append(os.path.join(root, file))
    
    # Sort by modification time (newest first)
    potential_files.sort(key=os.path.getmtime, reverse=True)
    return potential_files


def _analyze_single_file(file_path: str, project_root: str) -> Optional[tuple]:
    """Analyze a single metrics file."""
    metrics_path = os.path.join(project_root, file_path) if not os.path.isabs(file_path) else file_path
    
    if not os.path.exists(metrics_path):
        return None
    
    try:
        with open(metrics_path, 'r') as f:
            content = f.read()
        
        # Try to parse as JSON first
        try:
            metrics = json.loads(content)
        except json.JSONDecodeError:
            # Parse text content for common metrics
            metrics = _parse_text_metrics(content)
        
        if not metrics:
            return None
            
        # Infer model type from metrics
        model_type = _infer_model_type(metrics)
        
        return (metrics, model_type, os.path.basename(file_path))
        
    except Exception as e:
        logger.error(f"Error analyzing {file_path}: {str(e)}")
        return None


def _generate_comparison_report(results: List[tuple]) -> str:
    """Generate comparison report for multiple models."""
    report = "# ML Model Comparison Report\n\n"
    report += f"**Comparing {len(results)} models**\n\n"
    
    # Create comparison table
    report += "## Performance Summary\n\n"
    report += "| Model File | Type | Key Metrics |\n"
    report += "|------------|------|-------------|\n"
    
    for metrics, model_type, filename in results:
        key_metrics = []
        
        if model_type == 'classification':
            if 'accuracy' in metrics:
                key_metrics.append(f"Acc: {metrics['accuracy']:.3f}")
            if 'f1' in metrics:
                key_metrics.append(f"F1: {metrics['f1']:.3f}")
            if 'auc' in metrics:
                key_metrics.append(f"AUC: {metrics['auc']:.3f}")
        else:
            if 'r2' in metrics:
                key_metrics.append(f"R²: {metrics['r2']:.3f}")
            if 'rmse' in metrics:
                key_metrics.append(f"RMSE: {metrics['rmse']:.3f}")
            if 'mae' in metrics:
                key_metrics.append(f"MAE: {metrics['mae']:.3f}")
        
        report += f"| {filename} | {model_type} | {', '.join(key_metrics)} |\n"
    
    # Find best model
    report += "\n## Best Performing Model\n"
    best_model = _find_best_model(results)
    if best_model:
        metrics, model_type, filename = best_model
        report += f"**{filename}** based on primary metric\n\n"
        
        # Add detailed analysis for best model
        report += "### Detailed Metrics\n"
        for metric, value in sorted(metrics.items()):
            if isinstance(value, float):
                report += f"- **{metric.upper()}**: {value:.4f}\n"
    
    return report


def _find_best_model(results: List[tuple]) -> Optional[tuple]:
    """Find best model based on primary metric."""
    if not results:
        return None
    
    # Group by model type
    classification_models = [(m, t, f) for m, t, f in results if t == 'classification']
    regression_models = [(m, t, f) for m, t, f in results if t == 'regression']
    
    # Find best classification model (by F1 or accuracy)
    if classification_models:
        return max(classification_models, 
                  key=lambda x: x[0].get('f1', x[0].get('accuracy', 0)))
    
    # Find best regression model (by R²)
    if regression_models:
        return max(regression_models, 
                  key=lambda x: x[0].get('r2', -float('inf')))
    
    return results[0]  # Fallback to first


# Optional: Tool function
__all__ = ['analyze_ml_performance']