import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
import joblib
import os
from datetime import datetime, timedelta
import random

class DemandPredictor:
    """AI Model for predicting inventory demand"""
    
    def __init__(self):
        self.model = None
        self.scaler = StandardScaler()
        
    def train(self, historical_data=None):
        """Train demand prediction model"""
        print("Training demand predictor model...")
        
        if historical_data is None:
            historical_data = self._generate_sample_data()
        
        X, y = self._prepare_features(historical_data)
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        # Train model
        self.model = LinearRegression()
        self.model.fit(X_scaled, y)
        
        # Calculate R² score
        score = self.model.score(X_scaled, y)
        print(f"Demand predictor trained with R² score: {score:.3f}")
        
        return score
    
    def _generate_sample_data(self):
        """Generate sample training data"""
        np.random.seed(42)
        data = []
        
        for i in range(1000):
            # Features: [day_of_week, month, quantity_on_hand, price, days_since_last_sale]
            day_of_week = np.random.randint(0, 7)
            month = np.random.randint(1, 13)
            quantity_on_hand = np.random.randint(0, 500)
            price = np.random.uniform(5, 500)
            days_since_last_sale = np.random.randint(0, 30)
            
            # Target: daily demand (influenced by features)
            base_demand = 10
            weekend_boost = 1.5 if day_of_week >= 5 else 1.0
            holiday_boost = 1.3 if month in [11, 12] else 1.0
            price_effect = max(0.5, 1 - (price / 1000))
            
            demand = base_demand * weekend_boost * holiday_boost * price_effect
            demand += np.random.normal(0, 2)  # Add noise
            
            data.append({
                'features': [day_of_week, month, quantity_on_hand, price, days_since_last_sale],
                'demand': max(0, demand)
            })
        
        return data
    
    def _prepare_features(self, data):
        """Prepare features for training"""
        X = np.array([d['features'] for d in data])
        y = np.array([d['demand'] for d in data])
        return X, y
    
    def predict(self, item_data):
        """Predict demand for an item"""
        if self.model is None:
            self.train()
        
        # Extract features
        current_date = datetime.now()
        features = np.array([[
            current_date.weekday(),
            current_date.month,
            item_data.get('current_stock', 0),
            item_data.get('price', 0),
            item_data.get('days_since_last_sale', 0)
        ]])
        
        # Scale and predict
        features_scaled = self.scaler.transform(features)
        daily_demand = max(0, self.model.predict(features_scaled)[0])
        
        # Calculate predictions for different periods
        weekly_demand = daily_demand * 7
        monthly_demand = daily_demand * 30
        
        # Add seasonal adjustments
        seasonal_factor = self._get_seasonal_factor()
        weekly_demand *= seasonal_factor
        monthly_demand *= seasonal_factor
        
        # Calculate safety stock and reorder point
        lead_time = 7  # days
        safety_stock = daily_demand * lead_time * 1.5
        reorder_point = daily_demand * lead_time + safety_stock
        
        return {
            'daily_demand': round(daily_demand, 2),
            'weekly_demand': round(weekly_demand, 2),
            'monthly_demand': round(monthly_demand, 2),
            'safety_stock': round(safety_stock, 2),
            'reorder_point': round(reorder_point, 2),
            'optimal_stock': round(monthly_demand * 1.2, 2),
            'confidence_interval': {
                'low': round(daily_demand * 0.8, 2),
                'high': round(daily_demand * 1.2, 2)
            }
        }
    
    def _get_seasonal_factor(self):
        """Get seasonal adjustment factor"""
        current_month = datetime.now().month
        
        # Seasonal patterns
        seasonal_factors = {
            1: 0.8,   # January (post-holiday)
            2: 0.9,   # February
            3: 1.0,   # March
            4: 1.1,   # April
            5: 1.1,   # May
            6: 1.2,   # June
            7: 1.2,   # July
            8: 1.1,   # August
            9: 1.0,   # September
            10: 1.0,  # October
            11: 1.3,  # November (holiday season)
            12: 1.5,  # December (holiday season)
        }
        
        return seasonal_factors.get(current_month, 1.0)
    
    def predict_bulk(self, items):
        """Predict demand for multiple items"""
        predictions = []
        for item in items:
            pred = self.predict(item)
            pred['item_id'] = item.get('id')
            pred['item_name'] = item.get('item_name')
            predictions.append(pred)
        return predictions
    
    def get_restock_recommendations(self, items):
        """Get restock recommendations"""
        predictions = self.predict_bulk(items)
        recommendations = []
        
        for pred in predictions:
            current_stock = pred.get('current_stock', 0)
            reorder_point = pred['reorder_point']
            
            if current_stock <= reorder_point:
                urgency = 'high' if current_stock < reorder_point * 0.5 else 'medium'
                recommendations.append({
                    'item_name': pred['item_name'],
                    'current_stock': current_stock,
                    'reorder_point': reorder_point,
                    'recommended_order': round(reorder_point * 1.5 - current_stock),
                    'urgency': urgency,
                    'expected_depletion': f"{round(current_stock / pred['daily_demand'])} days" if pred['daily_demand'] > 0 else "N/A"
                })
        
        return sorted(recommendations, key=lambda x: x['urgency'] == 'high', reverse=True)
    
    def save_model(self, path='models/predictor_model.joblib'):
        """Save trained model"""
        if self.model:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            model_data = {
                'model': self.model,
                'scaler': self.scaler
            }
            joblib.dump(model_data, path)
            print(f"Predictor model saved to {path}")
    
    def load_model(self, path='models/predictor_model.joblib'):
        """Load trained model"""
        if os.path.exists(path):
            model_data = joblib.load(path)
            self.model = model_data['model']
            self.scaler = model_data['scaler']
            print(f"Predictor model loaded from {path}")
            return True
        return False

if __name__ == '__main__':
    # Test the predictor
    predictor = DemandPredictor()
    predictor.train()
    
    # Test prediction
    test_item = {
        'current_stock': 50,
        'price': 29.99,
        'days_since_last_sale': 3
    }
    
    prediction = predictor.predict(test_item)
    print("\nDemand Prediction:")
    print(f"Daily Demand: {prediction['daily_demand']} units")
    print(f"Weekly Demand: {prediction['weekly_demand']} units")
    print(f"Monthly Demand: {prediction['monthly_demand']} units")
    print(f"Reorder Point: {prediction['reorder_point']} units")
    print(f"Optimal Stock: {prediction['optimal_stock']} units")