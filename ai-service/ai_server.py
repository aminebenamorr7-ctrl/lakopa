from flask import Flask, request, jsonify
from flask_cors import CORS
import numpy as np
from datetime import datetime, timedelta
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Try to import ML models, fallback to simple version if they fail
try:
    from models.categorizer import InventoryCategorizer
    from models.predictor import DemandPredictor
    from models.analyzer import InventoryAnalyzer
    ML_MODELS_AVAILABLE = True
except Exception as e:
    print(f"⚠️ ML models not available: {e}")
    print("Using rule-based AI instead")
    ML_MODELS_AVAILABLE = False

app = Flask(__name__)
CORS(app)

class SimpleAIService:
    """Simple rule-based AI service that always works"""
    
    def __init__(self):
        self.categories = [
            'Electronics', 'Clothing', 'Food & Beverages', 
            'Office Supplies', 'Home & Garden', 'Sports & Outdoors',
            'Books & Media', 'Automotive', 'Health & Beauty',
            'Toys & Games', 'Tools & Hardware', 'Other'
        ]
        print("✅ Simple AI Service initialized")
    
    def categorize_item(self, item_name, description=""):
        text = f"{item_name} {description}".lower()
        
        category_keywords = {
            'Electronics': ['phone', 'laptop', 'computer', 'tablet', 'charger', 'cable', 'usb', 'hdmi', 'adapter', 'battery', 'screen', 'keyboard', 'mouse', 'speaker', 'headphone', 'camera', 'watch', 'smart', 'memory', 'webcam', 'monitor', 'power bank'],
            'Clothing': ['shirt', 'pants', 'dress', 'shoe', 'jacket', 'cloth', 'jeans', 'sock', 'hat', 'glove', 'scarf', 'belt', 'sweater', 'shorts', 'swim', 'pajama', 'uniform', 'coat', 'boot'],
            'Food & Beverages': ['food', 'drink', 'snack', 'coffee', 'tea', 'organic', 'protein', 'water', 'juice', 'chocolate', 'candy', 'spice', 'oil', 'rice', 'pasta', 'cereal', 'nut', 'honey', 'energy drink'],
            'Office Supplies': ['paper', 'pen', 'pencil', 'stapler', 'desk', 'office', 'notebook', 'folder', 'binder', 'clip', 'sticky', 'tape', 'envelope', 'calendar', 'label', 'rubber band', 'whiteboard'],
            'Home & Garden': ['furniture', 'garden', 'lamp', 'decor', 'kitchen', 'home', 'plant', 'towel', 'curtain', 'rug', 'pillow', 'candle', 'vase', 'mirror', 'clock', 'storage', 'cleaning', 'broom', 'mop'],
            'Sports & Outdoors': ['ball', 'racket', 'exercise', 'fitness', 'sport', 'gym', 'bike', 'yoga', 'camping', 'hiking', 'tent', 'helmet', 'fishing', 'basketball', 'soccer', 'swimming', 'running'],
            'Books & Media': ['book', 'magazine', 'novel', 'textbook', 'guide', 'manual', 'puzzle', 'game', 'journal', 'calendar', 'dvd', 'board game', 'coloring', 'sketch', 'paint'],
            'Automotive': ['car', 'auto', 'vehicle', 'tire', 'engine', 'motor', 'oil', 'wax', 'charger car', 'mount', 'wiper', 'brake', 'steering', 'seat cover'],
            'Health & Beauty': ['cream', 'lotion', 'makeup', 'vitamin', 'health', 'beauty', 'shampoo', 'soap', 'sunscreen', 'deodorant', 'brush', 'nail', 'lip', 'hair', 'perfume', 'essential oil'],
            'Toys & Games': ['toy', 'game', 'puzzle', 'doll', 'lego', 'play', 'blocks', 'card', 'robot', 'action figure', 'kite', 'balloon', 'marble', 'stuffed animal']
        }
        
        scores = {}
        for category, keywords in category_keywords.items():
            score = sum(1 for keyword in keywords if keyword in text)
            scores[category] = score
        
        max_score = max(scores.values())
        if max_score > 0:
            best_category = max(scores, key=scores.get)
            confidence = min(max_score / 3, 1.0)
        else:
            best_category = 'Other'
            confidence = 0.3
        
        return {
            'category': best_category,
            'confidence': round(confidence, 2),
            'all_predictions': [
                {'category': k, 'confidence': round(v/max(1, max_score*3), 2)} 
                for k, v in sorted(scores.items(), key=lambda x: x[1], reverse=True)[:3]
            ]
        }
    
    def predict_demand(self, item_id, item_name, current_stock, sales_history=None, price=0):
        if sales_history and len(sales_history) > 0:
            avg_daily_sales = np.mean(sales_history)
        else:
            # Generate realistic mock data based on stock level
            if current_stock > 100:
                avg_daily_sales = np.random.uniform(3, 8)
            elif current_stock > 10:
                avg_daily_sales = np.random.uniform(1, 5)
            else:
                avg_daily_sales = np.random.uniform(0.5, 3)
        
        predicted_demand_7d = avg_daily_sales * 7
        predicted_demand_30d = avg_daily_sales * 30
        reorder_point = predicted_demand_7d * 1.5
        optimal_stock = predicted_demand_30d * 1.2
        
        if current_stock <= reorder_point:
            stock_status = 'low'
            recommendation = f"URGENT: Reorder immediately! Order at least {max(1, round(reorder_point - current_stock))} units."
        elif current_stock < optimal_stock:
            stock_status = 'optimal'
            recommendation = f"Plan to reorder soon. Recommended: {max(1, round(optimal_stock - current_stock))} units."
        else:
            stock_status = 'excess'
            recommendation = "Stock level is adequate. No action needed."
        
        return {
            'item_id': item_id,
            'item_name': item_name,
            'current_stock': current_stock,
            'avg_daily_sales': round(avg_daily_sales, 2),
            'predicted_demand_7d': round(predicted_demand_7d),
            'predicted_demand_30d': round(predicted_demand_30d),
            'reorder_point': round(reorder_point),
            'optimal_stock': round(optimal_stock),
            'stock_status': stock_status,
            'recommendation': recommendation
        }
    
    def detect_anomalies(self, items):
        anomalies = []
        for item in items:
            issues = []
            qty = item.get('quantity', 0)
            price = item.get('price', 0)
            
            if qty < 0:
                issues.append("Negative stock quantity detected")
            if price < 0:
                issues.append("Negative price detected")
            if price > 10000:
                issues.append(f"Unusually high price: ${price:,.2f}")
            if qty > 10000:
                issues.append(f"Unusually high stock: {qty} units")
            if qty == 0:
                issues.append("Item is out of stock")
            
            if issues:
                severity = 'critical' if any(i.startswith('Negative') for i in issues) else \
                          'high' if len(issues) > 1 else 'medium'
                anomalies.append({
                    'item_id': item.get('id'),
                    'item_name': item.get('item_name', 'Unknown'),
                    'issues': issues,
                    'severity': severity
                })
        
        return anomalies
    
    def analyze_inventory_health(self, items):
        total = len(items)
        if total == 0:
            return {
                'status': 'empty',
                'score': 0,
                'metrics': {'total_items': 0, 'out_of_stock': 0, 'low_stock': 0, 'missing_category': 0, 'missing_price': 0},
                'recommendations': [{'priority': 'high', 'action': 'Add items to your inventory', 'impact': 'No items in system'}]
            }
        
        out_of_stock = sum(1 for i in items if i.get('quantity', 0) == 0)
        low_stock = sum(1 for i in items if 0 < i.get('quantity', 0) < 10)
        no_category = sum(1 for i in items if not i.get('category'))
        no_price = sum(1 for i in items if not i.get('price'))
        
        score = 100
        score -= (out_of_stock / total) * 30
        score -= (low_stock / total) * 20
        score -= (no_category / total) * 15
        score -= (no_price / total) * 15
        score = max(0, min(100, round(score, 1)))
        
        if score >= 80:
            status = 'excellent'
        elif score >= 60:
            status = 'good'
        elif score >= 40:
            status = 'fair'
        else:
            status = 'poor'
        
        recommendations = []
        if out_of_stock > 0:
            recommendations.append({
                'priority': 'high',
                'action': f'Reorder {out_of_stock} out-of-stock items',
                'impact': f'{out_of_stock} items currently unavailable'
            })
        if low_stock > 0:
            recommendations.append({
                'priority': 'medium',
                'action': f'Restock {low_stock} low-stock items',
                'impact': f'{low_stock} items running low (less than 10)'
            })
        if no_category > 0:
            recommendations.append({
                'priority': 'low',
                'action': f'Categorize {no_category} uncategorized items',
                'impact': 'Better organization and filtering'
            })
        if no_price > 0:
            recommendations.append({
                'priority': 'low',
                'action': f'Set prices for {no_price} items',
                'impact': 'Enable value tracking'
            })
        
        return {
            'status': status,
            'score': score,
            'metrics': {
                'total_items': total,
                'out_of_stock': out_of_stock,
                'low_stock': low_stock,
                'missing_category': no_category,
                'missing_price': no_price
            },
            'recommendations': recommendations
        }

# Use simple AI service
ai_service = SimpleAIService()

# ===== API Routes =====

@app.route('/api/ai/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'healthy',
        'service': 'Inventory AI Service v2.0',
        'type': 'Rule-Based AI',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/ai/categorize', methods=['POST'])
def categorize():
    try:
        data = request.json
        if not data or 'item_name' not in data:
            return jsonify({'success': False, 'message': 'Item name required'}), 400
        
        result = ai_service.categorize_item(
            data.get('item_name', ''),
            data.get('description', '')
        )
        return jsonify({'success': True, 'data': result})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/ai/predict-demand', methods=['POST'])
def predict_demand():
    try:
        data = request.json
        result = ai_service.predict_demand(
            data.get('item_id'),
            data.get('item_name', 'Unknown'),
            data.get('current_stock', 0),
            data.get('sales_history', []),
            data.get('price', 0)
        )
        return jsonify({'success': True, 'data': result})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/ai/detect-anomalies', methods=['POST'])
def detect_anomalies():
    try:
        data = request.json
        if not data or 'items' not in data:
            return jsonify({'success': False, 'message': 'Items array required'}), 400
        
        result = ai_service.detect_anomalies(data.get('items', []))
        return jsonify({
            'success': True,
            'data': result,
            'count': len(result)
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/ai/inventory-health', methods=['POST'])
def inventory_health():
    try:
        data = request.json
        if not data or 'items' not in data:
            return jsonify({'success': False, 'message': 'Items array required'}), 400
        
        result = ai_service.analyze_inventory_health(data.get('items', []))
        return jsonify({'success': True, 'data': result})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# Error handlers
@app.errorhandler(404)
def not_found(e):
    return jsonify({'success': False, 'message': 'Endpoint not found'}), 404

if __name__ == '__main__':
    print("=" * 50)
    print("🤖 AI Service Starting...")
    print("=" * 50)
    print("\n📡 Available endpoints:")
    print("   GET  /api/ai/health")
    print("   POST /api/ai/categorize")
    print("   POST /api/ai/predict-demand")
    print("   POST /api/ai/detect-anomalies")
    print("   POST /api/ai/inventory-health")
    print("\n" + "=" * 50)
    print("🚀 Running on http://localhost:5000")
    print("=" * 50 + "\n")
    
    app.run(host='0.0.0.0', port=5000, debug=True)