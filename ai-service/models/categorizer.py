import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder
import joblib
import os
import json

class InventoryCategorizer:
    """AI Model for categorizing inventory items"""
    
    def __init__(self):
        self.model = None
        self.label_encoder = None
        self.vectorizer = None
        self.categories = [
            'Electronics', 'Clothing', 'Food & Beverages', 
            'Office Supplies', 'Home & Garden', 'Sports & Outdoors',
            'Books & Media', 'Automotive', 'Health & Beauty',
            'Toys & Games', 'Tools & Hardware', 'Pet Supplies',
            'Jewelry & Accessories', 'Furniture', 'Other'
        ]
        
        # Training data for initial model
        self.training_data = self._get_training_data()
        
    def _get_training_data(self):
        """Get training data for the model"""
        return [
            # Electronics
            ("iPhone charger cable", "Electronics"),
            ("USB C hub adapter", "Electronics"),
            ("Wireless Bluetooth headphones", "Electronics"),
            ("Laptop stand aluminum", "Electronics"),
            ("HDMI cable 6ft", "Electronics"),
            ("Smart watch band", "Electronics"),
            ("Phone case protective", "Electronics"),
            ("Computer mouse wireless", "Electronics"),
            ("Keyboard mechanical", "Electronics"),
            ("Monitor 24 inch", "Electronics"),
            ("Tablet screen protector", "Electronics"),
            ("Power bank portable", "Electronics"),
            ("Webcam HD", "Electronics"),
            ("Speaker bluetooth", "Electronics"),
            ("Memory card 64gb", "Electronics"),
            
            # Clothing
            ("Cotton t-shirt men", "Clothing"),
            ("Denim jeans women", "Clothing"),
            ("Winter jacket waterproof", "Clothing"),
            ("Running shoes athletic", "Clothing"),
            ("Dress shirt formal", "Clothing"),
            ("Socks pack cotton", "Clothing"),
            ("Sweater wool knit", "Clothing"),
            ("Shorts cargo", "Clothing"),
            ("Hat baseball cap", "Clothing"),
            ("Scarf winter warm", "Clothing"),
            ("Gloves leather", "Clothing"),
            ("Belt casual", "Clothing"),
            ("Swimsuit beach", "Clothing"),
            ("Pajamas cotton", "Clothing"),
            ("Uniform work", "Clothing"),
            
            # Food & Beverages
            ("Coffee beans organic", "Food & Beverages"),
            ("Green tea organic", "Food & Beverages"),
            ("Protein bar chocolate", "Food & Beverages"),
            ("Water bottle reusable", "Food & Beverages"),
            ("Snack mix trail", "Food & Beverages"),
            ("Honey raw organic", "Food & Beverages"),
            ("Olive oil extra virgin", "Food & Beverages"),
            ("Chocolate dark", "Food & Beverages"),
            ("Energy drink natural", "Food & Beverages"),
            ("Pasta organic", "Food & Beverages"),
            ("Rice basmati", "Food & Beverages"),
            ("Cereal breakfast", "Food & Beverages"),
            ("Juice orange fresh", "Food & Beverages"),
            ("Nuts mixed roasted", "Food & Beverages"),
            ("Spices organic set", "Food & Beverages"),
            
            # Office Supplies
            ("Printer paper A4", "Office Supplies"),
            ("Ballpoint pen blue", "Office Supplies"),
            ("Stapler office heavy duty", "Office Supplies"),
            ("Notebook spiral bound", "Office Supplies"),
            ("Sticky notes yellow", "Office Supplies"),
            ("File folder manila", "Office Supplies"),
            ("Whiteboard markers", "Office Supplies"),
            ("Desk organizer", "Office Supplies"),
            ("Tape dispenser", "Office Supplies"),
            ("Binder clips medium", "Office Supplies"),
            ("Envelope mailing", "Office Supplies"),
            ("Calendar wall", "Office Supplies"),
            ("Paper clips jumbo", "Office Supplies"),
            ("Rubber bands assorted", "Office Supplies"),
            ("Label maker", "Office Supplies"),
            
            # Home & Garden
            ("LED light bulb", "Home & Garden"),
            ("Plant pot ceramic", "Home & Garden"),
            ("Garden hose 50ft", "Home & Garden"),
            ("Cleaning spray multi", "Home & Garden"),
            ("Towel set bathroom", "Home & Garden"),
            ("Curtains blackout", "Home & Garden"),
            ("Pillow memory foam", "Home & Garden"),
            ("Rug area 5x7", "Home & Garden"),
            ("Candle scented", "Home & Garden"),
            ("Picture frame wood", "Home & Garden"),
            ("Vase decorative", "Home & Garden"),
            ("Doormat outdoor", "Home & Garden"),
            ("Storage bin plastic", "Home & Garden"),
            ("Clock wall modern", "Home & Garden"),
            ("Mirror wall mounted", "Home & Garden"),
            
            # Sports & Outdoors
            ("Yoga mat exercise", "Sports & Outdoors"),
            ("Dumbbell set adjustable", "Sports & Outdoors"),
            ("Tent camping 4 person", "Sports & Outdoors"),
            ("Bicycle helmet adult", "Sports & Outdoors"),
            ("Fishing rod combo", "Sports & Outdoors"),
            ("Basketball outdoor", "Sports & Outdoors"),
            ("Soccer ball size 5", "Sports & Outdoors"),
            ("Tennis racket pro", "Sports & Outdoors"),
            ("Swimming goggles", "Sports & Outdoors"),
            ("Hiking backpack 40L", "Sports & Outdoors"),
            ("Jump rope speed", "Sports & Outdoors"),
            ("Resistance bands set", "Sports & Outdoors"),
            ("Cooler portable", "Sports & Outdoors"),
            ("Sleeping bag mummy", "Sports & Outdoors"),
            ("Compass hiking", "Sports & Outdoors"),
            
            # Books & Media
            ("Cookbook recipes", "Books & Media"),
            ("Notebook journal", "Books & Media"),
            ("Calendar 2024 wall", "Books & Media"),
            ("Art supplies set", "Books & Media"),
            ("Coloring book adult", "Books & Media"),
            ("DVD movie collection", "Books & Media"),
            ("Board game family", "Books & Media"),
            ("Puzzle 1000 piece", "Books & Media"),
            ("Magazine subscription", "Books & Media"),
            ("Sketch pad drawing", "Books & Media"),
            ("Paint set acrylic", "Books & Media"),
            ("Calligraphy pen set", "Books & Media"),
            ("Sticker book kids", "Books & Media"),
            ("Atlas world map", "Books & Media"),
            ("Dictionary english", "Books & Media"),
            
            # Automotive
            ("Car phone mount", "Automotive"),
            ("Air freshener car", "Automotive"),
            ("Windshield wipers", "Automotive"),
            ("Car charger USB", "Automotive"),
            ("Floor mats rubber", "Automotive"),
            ("Engine oil synthetic", "Automotive"),
            ("Car wax polish", "Automotive"),
            ("Tire inflator portable", "Automotive"),
            ("Jumper cables heavy duty", "Automotive"),
            ("Car seat cover", "Automotive"),
            ("Steering wheel cover", "Automotive"),
            ("Car wash soap", "Automotive"),
            ("Dash cam HD", "Automotive"),
            ("Car vacuum portable", "Automotive"),
            ("License plate frame", "Automotive"),
            
            # Health & Beauty
            ("Shampoo natural organic", "Health & Beauty"),
            ("Face moisturizer SPF", "Health & Beauty"),
            ("Toothbrush electric", "Health & Beauty"),
            ("Sunscreen SPF 50", "Health & Beauty"),
            ("Hand sanitizer gel", "Health & Beauty"),
            ("Lip balm natural", "Health & Beauty"),
            ("Nail polish set", "Health & Beauty"),
            ("Deodorant natural", "Health & Beauty"),
            ("Body lotion shea", "Health & Beauty"),
            ("First aid kit", "Health & Beauty"),
            ("Vitamins multivitamin", "Health & Beauty"),
            ("Hair dryer professional", "Health & Beauty"),
            ("Makeup brush set", "Health & Beauty"),
            ("Essential oils set", "Health & Beauty"),
            ("Razor blades pack", "Health & Beauty"),
            
            # Toys & Games
            ("Building blocks set", "Toys & Games"),
            ("Stuffed animal plush", "Toys & Games"),
            ("Remote control car", "Toys & Games"),
            ("Action figure superhero", "Toys & Games"),
            ("Doll house furniture", "Toys & Games"),
            ("Science kit experiment", "Toys & Games"),
            ("Card game deck", "Toys & Games"),
            ("Kite flying outdoor", "Toys & Games"),
            ("Play dough set", "Toys & Games"),
            ("Robot toy interactive", "Toys & Games"),
            ("Water gun summer", "Toys & Games"),
            ("Marble run set", "Toys & Games"),
            ("Jigsaw puzzle kids", "Toys & Games"),
            ("Musical toy instrument", "Toys & Games"),
            ("Balloons party pack", "Toys & Games"),
        ]
    
    def train(self):
        """Train the categorization model"""
        print("Training categorizer model...")
        
        # Prepare training data
        texts = [item[0] for item in self.training_data]
        labels = [item[1] for item in self.training_data]
        
        # Encode labels
        self.label_encoder = LabelEncoder()
        y = self.label_encoder.fit_transform(labels)
        
        # Create pipeline
        self.model = Pipeline([
            ('vectorizer', TfidfVectorizer(
                max_features=5000,
                ngram_range=(1, 2),
                stop_words='english'
            )),
            ('classifier', MultinomialNB(alpha=0.1))
        ])
        
        # Train model
        self.model.fit(texts, y)
        
        # Calculate accuracy
        accuracy = self.model.score(texts, y)
        print(f"Model trained with accuracy: {accuracy:.2%}")
        
        return accuracy
    
    def predict(self, item_name, description=""):
        """Predict category for an item"""
        if self.model is None:
            self.train()
        
        # Combine name and description
        text = f"{item_name} {description}"
        
        # Get prediction probabilities
        probabilities = self.model.predict_proba([text])[0]
        
        # Get top predictions
        top_indices = np.argsort(probabilities)[::-1][:5]
        
        predictions = []
        for idx in top_indices:
            category = self.label_encoder.inverse_transform([idx])[0]
            confidence = probabilities[idx]
            predictions.append({
                'category': category,
                'confidence': round(float(confidence), 4)
            })
        
        return {
            'category': predictions[0]['category'],
            'confidence': predictions[0]['confidence'],
            'all_predictions': predictions
        }
    
    def save_model(self, path='models/categorizer_model.joblib'):
        """Save trained model"""
        if self.model:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            model_data = {
                'model': self.model,
                'label_encoder': self.label_encoder
            }
            joblib.dump(model_data, path)
            print(f"Model saved to {path}")
    
    def load_model(self, path='models/categorizer_model.joblib'):
        """Load trained model"""
        if os.path.exists(path):
            model_data = joblib.load(path)
            self.model = model_data['model']
            self.label_encoder = model_data['label_encoder']
            print(f"Model loaded from {path}")
            return True
        return False

if __name__ == '__main__':
    # Test the categorizer
    categorizer = InventoryCategorizer()
    categorizer.train()
    
    # Test predictions
    test_items = [
        ("USB cable charger", "fast charging cable for phones"),
        ("Winter coat", "warm waterproof jacket for skiing"),
        ("Coffee maker", "automatic drip coffee machine"),
        ("Yoga mat", "non-slip exercise mat for workout"),
    ]
    
    print("\nTest Predictions:")
    for name, desc in test_items:
        result = categorizer.predict(name, desc)
        print(f"Item: {name}")
        print(f"Category: {result['category']} (confidence: {result['confidence']:.2%})")
        print()