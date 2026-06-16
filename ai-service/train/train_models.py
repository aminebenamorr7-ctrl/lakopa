#!/usr/bin/env python3
"""
Train all AI models for the inventory system
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.categorizer import InventoryCategorizer
from models.predictor import DemandPredictor
from models.analyzer import InventoryAnalyzer
import joblib
from datetime import datetime

def train_all_models():
    """Train and save all models"""
    print("=" * 60)
    print("🤖 Training Inventory AI Models")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    results = {}
    
    # 1. Train Categorizer
    print("1/3 Training Categorizer Model...")
    print("-" * 40)
    try:
        categorizer = InventoryCategorizer()
        accuracy = categorizer.train()
        categorizer.save_model('models/categorizer_model.joblib')
        results['categorizer'] = {'status': 'success', 'accuracy': accuracy}
        print(f"✅ Categorizer trained successfully (Accuracy: {accuracy:.2%})")
    except Exception as e:
        results['categorizer'] = {'status': 'failed', 'error': str(e)}
        print(f"❌ Categorizer training failed: {e}")
    print()
    
    # 2. Train Demand Predictor
    print("2/3 Training Demand Predictor Model...")
    print("-" * 40)
    try:
        predictor = DemandPredictor()
        score = predictor.train()
        predictor.save_model('models/predictor_model.joblib')
        results['predictor'] = {'status': 'success', 'r2_score': score}
        print(f"✅ Predictor trained successfully (R² Score: {score:.3f})")
    except Exception as e:
        results['predictor'] = {'status': 'failed', 'error': str(e)}
        print(f"❌ Predictor training failed: {e}")
    print()
    
    # 3. Train Anomaly Analyzer
    print("3/3 Training Anomaly Analyzer Model...")
    print("-" * 40)
    try:
        analyzer = InventoryAnalyzer()
        analyzer.train_anomaly_detector()
        analyzer.save_model('models/analyzer_model.joblib')
        results['analyzer'] = {'status': 'success'}
        print(f"✅ Analyzer trained successfully")
    except Exception as e:
        results['analyzer'] = {'status': 'failed', 'error': str(e)}
        print(f"❌ Analyzer training failed: {e}")
    print()
    
    # Save training results
    results['trained_at'] = datetime.now().isoformat()
    results['version'] = '1.0.0'
    
    os.makedirs('models', exist_ok=True)
    with open('models/training_results.json', 'w') as f:
        import json
        json.dump(results, f, indent=2)
    
    # Summary
    print("=" * 60)
    print("📊 Training Summary")
    print("=" * 60)
    for model_name, result in results.items():
        if model_name in ['trained_at', 'version']:
            continue
        status = result['status']
        icon = '✅' if status == 'success' else '❌'
        print(f"{icon} {model_name.title()}: {status}")
        
        if status == 'success':
            if 'accuracy' in result:
                print(f"   Accuracy: {result['accuracy']:.2%}")
            if 'r2_score' in result:
                print(f"   R² Score: {result['r2_score']:.3f}")
    
    print()
    print(f"Models saved in: {os.path.abspath('models/')}")
    print("=" * 60)
    
    return results

def test_models():
    """Quick test of all trained models"""
    print("\n" + "=" * 60)
    print("🧪 Testing Trained Models")
    print("=" * 60)
    
    # Test Categorizer
    print("\n1. Testing Categorizer:")
    categorizer = InventoryCategorizer()
    if categorizer.load_model('models/categorizer_model.joblib'):
        test_items = [
            ("Wireless mouse", "ergonomic computer mouse"),
            ("Winter jacket", "waterproof ski jacket"),
            ("Protein bars", "chocolate protein bars 12 pack"),
        ]
        for name, desc in test_items:
            result = categorizer.predict(name, desc)
            print(f"   {name} → {result['category']} ({result['confidence']:.0%})")
    
    # Test Predictor
    print("\n2. Testing Predictor:")
    predictor = DemandPredictor()
    if predictor.load_model('models/predictor_model.joblib'):
        test_item = {'current_stock': 50, 'price': 29.99, 'days_since_last_sale': 3}
        prediction = predictor.predict(test_item)
        print(f"   Daily demand: {prediction['daily_demand']} units")
        print(f"   Reorder point: {prediction['reorder_point']} units")
    
    # Test Analyzer
    print("\n3. Testing Analyzer:")
    analyzer = InventoryAnalyzer()
    if analyzer.load_model('models/analyzer_model.joblib'):
        test_items = [
            {'id': 1, 'item_name': 'Test Item', 'quantity': 100, 'price': 50, 'category': 'Test'},
        ]
        health = analyzer.analyze_inventory_health(test_items)
        print(f"   Health Score: {health['score']}/100 ({health['status']})")

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Train Inventory AI Models')
    parser.add_argument('--test', action='store_true', help='Test models after training')
    args = parser.parse_args()
    
    # Train models
    results = train_all_models()
    
    # Test if requested
    if args.test:
        test_models()
    
    # Check for failures
    failures = [k for k, v in results.items() if isinstance(v, dict) and v.get('status') == 'failed']
    if failures:
        print(f"\n⚠️  Warning: {len(failures)} model(s) failed to train")
        sys.exit(1)
    else:
        print("\n🎉 All models trained successfully!")
        sys.exit(0)