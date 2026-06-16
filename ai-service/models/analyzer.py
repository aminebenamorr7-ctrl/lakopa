import numpy as np
from scipy import stats
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import joblib
import os
from datetime import datetime, timedelta

class InventoryAnalyzer:
    """AI Model for analyzing inventory patterns and detecting anomalies"""
    
    def __init__(self):
        self.anomaly_detector = None
        self.scaler = StandardScaler()
        self.thresholds = self._get_default_thresholds()
    
    def _get_default_thresholds(self):
        """Get default thresholds for anomaly detection"""
        return {
            'price': {
                'min': 0.01,
                'max': 100000,
                'unusual_high': 10000
            },
            'quantity': {
                'min': 0,
                'max': 1000000,
                'unusual_high': 10000,
                'unusual_change_percent': 50
            },
            'category_count': {
                'unusual_low': 2
            }
        }
    
    def train_anomaly_detector(self, data=None):
        """Train anomaly detection model"""
        print("Training anomaly detector...")
        
        if data is None:
            data = self._generate_sample_data()
        
        # Prepare features
        X = self._prepare_features(data)
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        # Train Isolation Forest
        self.anomaly_detector = IsolationForest(
            contamination=0.1,
            random_state=42,
            n_estimators=100
        )
        self.anomaly_detector.fit(X_scaled)
        
        print("Anomaly detector trained successfully")
    
    def _generate_sample_data(self):
        """Generate sample data for training"""
        np.random.seed(42)
        data = []
        
        for i in range(500):
            item = {
                'id': i + 1,
                'item_name': f'Item {i+1}',
                'quantity': np.random.normal(100, 30),
                'price': np.random.normal(50, 20),
                'category': np.random.choice(['Electronics', 'Clothing', 'Food']),
                'created_at': datetime.now() - timedelta(days=np.random.randint(1, 365))
            }
            data.append(item)
        
        # Add some anomalies
        anomalies = [
            {'id': 501, 'item_name': 'Anomaly High Price', 'quantity': 100, 'price': 50000},
            {'id': 502, 'item_name': 'Anomaly High Stock', 'quantity': 50000, 'price': 50},
            {'id': 503, 'item_name': 'Anomaly Negative Stock', 'quantity': -10, 'price': 50},
            {'id': 504, 'item_name': 'Anomaly Old Item', 'quantity': 100, 'price': 50, 'created_at': datetime.now() - timedelta(days=500)},
        ]
        
        data.extend(anomalies)
        return data
    
    def _prepare_features(self, data):
        """Prepare features for anomaly detection"""
        features = []
        for item in data:
            # Extract numerical features
            quantity = item.get('quantity', 0)
            price = item.get('price', 0)
            
            # Calculate days since creation
            if 'created_at' in item:
                days_since_creation = (datetime.now() - item['created_at']).days
            else:
                days_since_creation = 0
            
            features.append([
                quantity,
                price,
                days_since_creation,
                np.log1p(quantity),  # Log transform for skewed data
                np.log1p(price)
            ])
        
        return np.array(features)
    
    def detect_anomalies(self, items):
        """Detect anomalies in inventory items"""
        anomalies = []
        
        for item in items:
            item_anomalies = []
            
            # Rule-based checks
            item_anomalies.extend(self._rule_based_checks(item))
            
            # Statistical checks
            item_anomalies.extend(self._statistical_checks(item, items))
            
            if item_anomalies:
                anomalies.append({
                    'item_id': item.get('id'),
                    'item_name': item.get('item_name', 'Unknown'),
                    'anomalies': item_anomalies,
                    'severity': self._calculate_severity(item_anomalies)
                })
        
        # ML-based anomaly detection
        if self.anomaly_detector and len(items) > 0:
            X = self._prepare_features(items)
            if X.shape[0] > 0:
                X_scaled = self.scaler.transform(X)
                predictions = self.anomaly_detector.predict(X_scaled)
                
                for i, pred in enumerate(predictions):
                    if pred == -1:  # Anomaly detected
                        if not any(a['item_id'] == items[i].get('id') for a in anomalies):
                            anomalies.append({
                                'item_id': items[i].get('id'),
                                'item_name': items[i].get('item_name', 'Unknown'),
                                'anomalies': [{'type': 'ml_detected', 'message': 'ML model detected unusual pattern'}],
                                'severity': 'medium'
                            })
        
        return anomalies
    
    def _rule_based_checks(self, item):
        """Perform rule-based anomaly checks"""
        anomalies = []
        
        quantity = item.get('quantity', 0)
        price = item.get('price', 0)
        
        # Check for negative values
        if quantity < self.thresholds['quantity']['min']:
            anomalies.append({
                'type': 'negative_quantity',
                'message': f'Negative quantity: {quantity}',
                'value': quantity
            })
        
        if price < self.thresholds['price']['min']:
            anomalies.append({
                'type': 'negative_price',
                'message': f'Invalid price: ${price}',
                'value': price
            })
        
        # Check for unusually high values
        if quantity > self.thresholds['quantity']['unusual_high']:
            anomalies.append({
                'type': 'high_quantity',
                'message': f'Unusually high quantity: {quantity}',
                'value': quantity
            })
        
        if price > self.thresholds['price']['unusual_high']:
            anomalies.append({
                'type': 'high_price',
                'message': f'Unusually high price: ${price}',
                'value': price
            })
        
        # Check for old items with zero stock
        if quantity == 0 and 'created_at' in item:
            days_since = (datetime.now() - item['created_at']).days
            if days_since > 90:
                anomalies.append({
                    'type': 'stale_item',
                    'message': f'Out of stock for {days_since} days',
                    'value': days_since
                })
        
        return anomalies
    
    def _statistical_checks(self, item, all_items):
        """Perform statistical anomaly checks"""
        anomalies = []
        
        # Only perform if we have enough data
        if len(all_items) < 5:
            return anomalies
        
        # Calculate statistics for same category
        category = item.get('category')
        if category:
            same_category = [i for i in all_items if i.get('category') == category]
            if len(same_category) > 2:
                prices = [i.get('price', 0) for i in same_category if i.get('price', 0) > 0]
                quantities = [i.get('quantity', 0) for i in same_category]
                
                if prices:
                    mean_price = np.mean(prices)
                    std_price = np.std(prices)
                    item_price = item.get('price', 0)
                    
                    if std_price > 0 and abs(item_price - mean_price) > 3 * std_price:
                        anomalies.append({
                            'type': 'price_outlier',
                            'message': f'Price ${item_price} is unusual for {category} (avg: ${mean_price:.2f})',
                            'value': item_price
                        })
                
                if quantities:
                    mean_qty = np.mean(quantities)
                    std_qty = np.std(quantities)
                    item_qty = item.get('quantity', 0)
                    
                    if std_qty > 0 and abs(item_qty - mean_qty) > 3 * std_qty:
                        anomalies.append({
                            'type': 'quantity_outlier',
                            'message': f'Quantity {item_qty} is unusual for {category} (avg: {mean_qty:.0f})',
                            'value': item_qty
                        })
        
        return anomalies
    
    def _calculate_severity(self, anomalies):
        """Calculate severity based on number and type of anomalies"""
        if not anomalies:
            return 'none'
        
        critical_types = ['negative_quantity', 'negative_price']
        critical_count = sum(1 for a in anomalies if a['type'] in critical_types)
        
        if critical_count > 0:
            return 'critical'
        elif len(anomalies) >= 3:
            return 'high'
        elif len(anomalies) >= 2:
            return 'medium'
        else:
            return 'low'
    
    def analyze_inventory_health(self, items):
        """Analyze overall inventory health"""
        total_items = len(items)
        if total_items == 0:
            return {'status': 'empty', 'score': 0}
        
        # Calculate metrics
        out_of_stock = sum(1 for i in items if i.get('quantity', 0) == 0)
        low_stock = sum(1 for i in items if 0 < i.get('quantity', 0) < 10)
        no_category = sum(1 for i in items if not i.get('category'))
        no_price = sum(1 for i in items if not i.get('price', 0))
        
        # Calculate health score (0-100)
        score = 100
        score -= (out_of_stock / total_items) * 30
        score -= (low_stock / total_items) * 20
        score -= (no_category / total_items) * 15
        score -= (no_price / total_items) * 15
        
        score = max(0, min(100, score))
        
        # Determine status
        if score >= 80:
            status = 'excellent'
        elif score >= 60:
            status = 'good'
        elif score >= 40:
            status = 'fair'
        else:
            status = 'poor'
        
        return {
            'status': status,
            'score': round(score, 1),
            'metrics': {
                'total_items': total_items,
                'out_of_stock': out_of_stock,
                'low_stock': low_stock,
                'missing_category': no_category,
                'missing_price': no_price
            },
            'recommendations': self._get_health_recommendations(score, out_of_stock, low_stock, no_category, no_price)
        }
    
    def _get_health_recommendations(self, score, out_of_stock, low_stock, no_category, no_price):
        """Get recommendations based on inventory health"""
        recommendations = []
        
        if out_of_stock > 0:
            recommendations.append({
                'priority': 'high',
                'action': 'Reorder out-of-stock items immediately',
                'impact': f'{out_of_stock} items currently unavailable'
            })
        
        if low_stock > 0:
            recommendations.append({
                'priority': 'medium',
                'action': 'Plan restock for low-stock items',
                'impact': f'{low_stock} items running low'
            })
        
        if no_category > 0:
            recommendations.append({
                'priority': 'low',
                'action': 'Categorize uncategorized items',
                'impact': f'{no_category} items need categorization'
            })
        
        if score < 60:
            recommendations.append({
                'priority': 'high',
                'action': 'Conduct full inventory audit',
                'impact': 'Overall inventory health is poor'
            })
        
        return recommendations
    
    def save_model(self, path='models/analyzer_model.joblib'):
        """Save trained model"""
        if self.anomaly_detector:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            model_data = {
                'anomaly_detector': self.anomaly_detector,
                'scaler': self.scaler
            }
            joblib.dump(model_data, path)
            print(f"Analyzer model saved to {path}")
    
    def load_model(self, path='models/analyzer_model.joblib'):
        """Load trained model"""
        if os.path.exists(path):
            model_data = joblib.load(path)
            self.anomaly_detector = model_data['anomaly_detector']
            self.scaler = model_data['scaler']
            print(f"Analyzer model loaded from {path}")
            return True
        return False

if __name__ == '__main__':
    # Test the analyzer
    analyzer = InventoryAnalyzer()
    analyzer.train_anomaly_detector()
    
    # Test with sample items
    test_items = [
        {'id': 1, 'item_name': 'Normal Item', 'quantity': 100, 'price': 50, 'category': 'Electronics'},
        {'id': 2, 'item_name': 'High Price', 'quantity': 50, 'price': 50000, 'category': 'Electronics'},
        {'id': 3, 'item_name': 'Negative Stock', 'quantity': -5, 'price': 30, 'category': 'Clothing'},
        {'id': 4, 'item_name': 'No Category', 'quantity': 75, 'price': 40},
    ]
    
    anomalies = analyzer.detect_anomalies(test_items)
    print(f"\nFound {len(anomalies)} anomalies:")
    for anomaly in anomalies:
        print(f"- {anomaly['item_name']}: {len(anomaly['anomalies'])} issues (severity: {anomaly['severity']})")
    
    # Test inventory health
    health = analyzer.analyze_inventory_health(test_items)
    print(f"\nInventory Health Score: {health['score']}/100 ({health['status']})")