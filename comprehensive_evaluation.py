"""
Comprehensive Model Performance Evaluation and Visualization
Creates essential plots with English labels and detailed explanations
"""

import json
import pickle
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

# Configure matplotlib for clean English rendering
plt.style.use('seaborn-v0_8-whitegrid')
sns.set_palette("husl")
plt.rcParams['font.family'] = 'DejaVu Sans'
plt.rcParams['font.size'] = 10
plt.rcParams['axes.unicode_minus'] = False

MODELS_DIR = Path("models")
MODEL_PATH = MODELS_DIR / "best_mcp_lstm_model.h5"
METADATA_PATH = MODELS_DIR / "mcp_model_metadata.pkl"
HISTORY_PATH = MODELS_DIR / "training_history.json"


def load_artifacts():
    """Load saved model metadata and training history."""
    with open(METADATA_PATH, 'rb') as f:
        metadata = pickle.load(f)
    
    with open(HISTORY_PATH, 'r', encoding='utf-8') as f:
        history = json.load(f)
    
    return metadata, history


def create_comprehensive_plots(history, metadata):
    """
    Generate 6 essential performance analysis plots with detailed explanations.
    
    Plot 1: Training/Validation Loss Curves
        - Shows model learning progress over epochs
        - Lower loss = better fit
        - Val > Train suggests overfitting
        
    Plot 2: Training/Validation MAE Curves  
        - Tracks Mean Absolute Error (average prediction error)
        - MAE in same units as target variable
        - Lower MAE = more accurate predictions
        
    Plot 3: Epoch-wise Improvement Rate
        - Percentage improvement per epoch
        - Positive = model improving
        - Negative = model degrading
        - Helps identify learning plateaus
        
    Plot 4: Generalization Gap Analysis
        - Difference between validation and training loss
        - Positive gap = overfitting (model memorizing training data)
        - Negative gap = underfitting (model too simple)
        - Ideal: small positive gap
        
    Plot 5: Training Stability Analysis
        - Standard deviation of MAE across epochs
        - Lower std = more stable/consistent learning
        - High std = unstable/erratic training
        
    Plot 6: Performance Summary
        - Configuration details and final metrics
        - Best epoch identification
        - Overall improvement percentages
    """
    
    fig = plt.figure(figsize=(20, 10))
    
    epochs = history['epoch']
    best_epoch = int(np.argmin(history['val_loss'])) + 1
    best_loss = float(np.min(history['val_loss']))
    
    # ==================== PLOT 1: Loss Curves ====================
    ax1 = plt.subplot(2, 3, 1)
    ax1.plot(epochs, history['train_loss'], label='Training Loss', 
             linewidth=2.5, alpha=0.8, color='#2E86DE')
    ax1.plot(epochs, history['val_loss'], label='Validation Loss', 
             linewidth=2.5, alpha=0.8, color='#EE5A6F')
    ax1.axvline(x=float(best_epoch), color='red', linestyle='--', alpha=0.5, linewidth=1.5)
    ax1.annotate(f'Best Epoch: {best_epoch}\nLoss: {best_loss:.4f}',
                xy=(float(best_epoch), best_loss),
                xytext=(10, 10), textcoords='offset points',
                bbox=dict(boxstyle='round,pad=0.5', fc='yellow', alpha=0.3),
                fontsize=9, ha='left')
    ax1.set_xlabel('Epoch', fontsize=12, fontweight='bold')
    ax1.set_ylabel('Loss (Huber)', fontsize=12, fontweight='bold')
    ax1.set_title('Training & Validation Loss Curves\n(Lower is Better)', 
                  fontsize=13, fontweight='bold', pad=10)
    ax1.legend(fontsize=10, loc='upper right')
    ax1.grid(True, linestyle='--', alpha=0.6)
    
    # ==================== PLOT 2: MAE Curves ====================
    ax2 = plt.subplot(2, 3, 2)
    ax2.plot(epochs, history['train_mae'], label='Training MAE', 
             linewidth=2.5, alpha=0.8, color='#10AC84')
    ax2.plot(epochs, history['val_mae'], label='Validation MAE', 
             linewidth=2.5, alpha=0.8, color='#F79F1F')
    ax2.set_xlabel('Epoch', fontsize=12, fontweight='bold')
    ax2.set_ylabel('Mean Absolute Error', fontsize=12, fontweight='bold')
    ax2.set_title('MAE Progression Over Training\n(Average Prediction Error)', 
                  fontsize=13, fontweight='bold', pad=10)
    ax2.legend(fontsize=10, loc='upper right')
    ax2.grid(True, linestyle='--', alpha=0.6)
    
    # ==================== PLOT 3: Improvement Rate ====================
    ax3 = plt.subplot(2, 3, 3)
    train_improvements = -np.diff(history['train_loss']) / np.array(history['train_loss'][:-1]) * 100
    val_improvements = -np.diff(history['val_loss']) / np.array(history['val_loss'][:-1]) * 100
    ax3.plot(epochs[1:], train_improvements, label='Train Improvement', 
             linewidth=2, alpha=0.8, color='#5F27CD')
    ax3.plot(epochs[1:], val_improvements, label='Val Improvement', 
             linewidth=2, alpha=0.8, color='#00D2D3')
    ax3.axhline(y=0, color='red', linestyle='--', alpha=0.5, linewidth=2)
    ax3.set_xlabel('Epoch', fontsize=12, fontweight='bold')
    ax3.set_ylabel('Improvement Rate (%)', fontsize=12, fontweight='bold')
    ax3.set_title('Epoch-wise Performance Improvement\n(Positive = Better)', 
                  fontsize=13, fontweight='bold', pad=10)
    ax3.legend(fontsize=10)
    ax3.grid(True, linestyle='--', alpha=0.6)
    
    # ==================== PLOT 4: Generalization Gap ====================
    ax4 = plt.subplot(2, 3, 4)
    loss_gap = np.array(history['val_loss']) - np.array(history['train_loss'])
    ax4.plot(epochs, loss_gap, linewidth=2.5, color='#8E44AD', alpha=0.8)
    ax4.axhline(y=0, color='green', linestyle='--', alpha=0.5, linewidth=2)
    ax4.fill_between(epochs, 0, loss_gap, 
                     where=np.array(loss_gap) > 0, 
                     alpha=0.3, color='red', label='Overfitting Zone')
    ax4.fill_between(epochs, 0, loss_gap, 
                     where=np.array(loss_gap) <= 0, 
                     alpha=0.3, color='blue', label='Underfitting Zone')
    ax4.set_xlabel('Epoch', fontsize=12, fontweight='bold')
    ax4.set_ylabel('Val Loss - Train Loss', fontsize=12, fontweight='bold')
    ax4.set_title('Generalization Gap Analysis\n(Small Gap = Good Generalization)', 
                  fontsize=13, fontweight='bold', pad=10)
    ax4.legend(fontsize=10)
    ax4.grid(True, linestyle='--', alpha=0.6)
    
    # ==================== PLOT 5: Training Stability ====================
    ax5 = plt.subplot(2, 3, 5)
    train_mae_std = np.std(history['train_mae'])
    val_mae_std = np.std(history['val_mae'])
    categories = ['Train MAE\nStability', 'Val MAE\nStability']
    stds = [train_mae_std, val_mae_std]
    colors_bar = ['#2ECC71' if std < 0.1 else '#F39C12' if std < 0.2 else '#E74C3C' for std in stds]
    bars = ax5.bar(categories, stds, color=colors_bar, alpha=0.7, edgecolor='black', linewidth=1.5)
    ax5.set_ylabel('Standard Deviation', fontsize=12, fontweight='bold')
    ax5.set_title('Training Stability Measurement\n(Lower = More Stable)', 
                  fontsize=13, fontweight='bold', pad=10)
    ax5.grid(True, axis='y', linestyle='--', alpha=0.6)
    for bar, std in zip(bars, stds):
        height = bar.get_height()
        ax5.text(bar.get_x() + bar.get_width()/2., height,
                f'{std:.4f}', ha='center', va='bottom', fontsize=10, fontweight='bold')
    
    # ==================== PLOT 6: Performance Summary ====================
    ax6 = plt.subplot(2, 3, 6)
    ax6.axis('off')
    
    train_improve = (history['train_loss'][0] - history['train_loss'][-1]) / history['train_loss'][0] * 100
    val_improve = (history['val_loss'][0] - history['val_loss'][-1]) / history['val_loss'][0] * 100
    
    summary_text = f"""
TRAINING SUMMARY
{'='*50}

Model Configuration:
  - Features: {metadata['n_features']}
  - Sequence Length: {metadata['sequence_length']}
  - Target: {metadata['target_col']}
  - Log Transform: {metadata['use_log_transform']}
  - Scaler: {type(metadata['scaler']).__name__}

Training Progress:
  - Total Epochs: {len(epochs)}
  - Best Epoch: {best_epoch}
  - Early Stopped: {'Yes' if len(epochs) < 150 else 'No'}
  
Final Metrics:
  - Train Loss: {history['train_loss'][-1]:.6f}
  - Val Loss: {history['val_loss'][-1]:.6f}
  - Train MAE: {history['train_mae'][-1]:.4f}
  - Val MAE: {history['val_mae'][-1]:.4f}

Best Performance:
  - Best Val Loss: {best_loss:.6f}
  - Best Train MAE: {min(history['train_mae']):.4f}
  - Best Val MAE: {min(history['val_mae']):.4f}

Overall Improvement:
  - Train: {train_improve:.2f}%
  - Val: {val_improve:.2f}%
"""
    ax6.text(0.05, 0.5, summary_text, fontsize=10, verticalalignment='center',
            family='monospace', 
            bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.3, pad=1))
    
    plt.tight_layout()
    output_path = MODELS_DIR / 'comprehensive_training_analysis.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
    print(f"\n[SUCCESS] Comprehensive analysis saved: {output_path}")
    plt.close()


def print_summary_table(metadata, history):
    """Print formatted summary table in English."""
    print("\n" + "="*80)
    print("LSTM MODEL COMPREHENSIVE EVALUATION REPORT".center(80))
    print("="*80)
    
    print("\n[MODEL CONFIGURATION]")
    print("-" * 80)
    print(f"  {'Feature Count':<30}: {metadata['n_features']}")
    print(f"  {'Sequence Length':<30}: {metadata['sequence_length']}")
    print(f"  {'Target Column':<30}: {metadata['target_col']}")
    print(f"  {'Log Transform Applied':<30}: {metadata['use_log_transform']}")
    print(f"  {'Scaler Type':<30}: {type(metadata['scaler']).__name__}")
    
    print("\n[TRAINING PROCESS]")
    print("-" * 80)
    best_epoch = int(np.argmin(history['val_loss'])) + 1
    print(f"  {'Total Epochs':<30}: {len(history['epoch'])}")
    print(f"  {'Best Epoch':<30}: {best_epoch}")
    print(f"  {'Best Val Loss':<30}: {min(history['val_loss']):.6f}")
    print(f"  {'Final Train Loss':<30}: {history['train_loss'][-1]:.6f}")
    print(f"  {'Final Val Loss':<30}: {history['val_loss'][-1]:.6f}")
    
    train_improve = (history['train_loss'][0] - history['train_loss'][-1]) / history['train_loss'][0] * 100
    val_improve = (history['val_loss'][0] - history['val_loss'][-1]) / history['val_loss'][0] * 100
    print(f"  {'Train Improvement':<30}: {train_improve:.2f}%")
    print(f"  {'Val Improvement':<30}: {val_improve:.2f}%")
    
    print("\n[EVALUATION COMPLETE]")
    print("="*80)


def main():
    print("\n[STARTING] Comprehensive Performance Evaluation...\n")
    
    if not METADATA_PATH.exists() or not HISTORY_PATH.exists():
        print("[ERROR] Model metadata or history files not found.")
        print("        Please run train_from_notebook.py first.")
        return
    
    metadata, history = load_artifacts()
    create_comprehensive_plots(history, metadata)
    print_summary_table(metadata, history)
    
    print("\n[COMPLETE] Evaluation finished successfully!")
    print(f"[OUTPUT] Results saved to: {MODELS_DIR / 'comprehensive_training_analysis.png'}")
    print("\nPlot Descriptions:")
    print("  1. Loss Curves - Model learning progress (lower = better)")
    print("  2. MAE Curves - Average prediction error over time")
    print("  3. Improvement Rate - Percentage gain per epoch")
    print("  4. Generalization Gap - Overfitting/underfitting indicator")
    print("  5. Training Stability - Learning consistency measurement")
    print("  6. Performance Summary - Configuration and final metrics\n")


if __name__ == "__main__":
    main()
