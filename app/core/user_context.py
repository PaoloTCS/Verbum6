# app core user_context.py

from typing import Dict, List, Optional
import json
import os

class UserContext:
    def __init__(self):
        self.preferences = {
            "domains": {},        # Domain weights based on user interaction
            "recent_clicks": [],  # Track recent navigation paths
            "expertise_levels": {
                "math": 0.0,
                "physics": 0.0,
                "programming": 0.0,
                "business": 0.0,
                "medicine": 0.0
            }
        }
        self.load_context()
    
    def update_domain_interest(self, domain: str, weight: float = 0.1):
        """Update user's interest in a domain based on interaction."""
        current = self.preferences["domains"].get(domain, 0.0)
        self.preferences["domains"][domain] = min(1.0, current + weight)
        self.save_context()
    
    def add_click(self, path: str):
        """Record user navigation."""
        self.preferences["recent_clicks"].append(path)
        self.preferences["recent_clicks"] = self.preferences["recent_clicks"][-5:]  # Keep last 5
        self.save_context()
    
    def predict_next_click(self, current_path: str) -> Optional[str]:
        """Predict user's next likely destination based on history and interests."""
        try:
            # Get current domain from path
            current_domain = current_path.split('/')[0] if '/' in current_path else current_path
            
            # Get recent paths in same domain
            domain_clicks = [
                click for click in self.preferences["recent_clicks"]
                if click.startswith(current_domain)
            ]
            
            if domain_clicks:
                # Find common next steps from this path
                next_steps = []
                for i, click in enumerate(domain_clicks[:-1]):
                    if click == current_path:
                        next_steps.append(domain_clicks[i + 1])
                
                if next_steps:
                    # Return most common next step
                    from collections import Counter
                    return Counter(next_steps).most_common(1)[0][0]
            
            # If no history, suggest based on domain interests
            domain_interests = sorted(
                self.preferences["domains"].items(),
                key=lambda x: x[1],
                reverse=True
            )
            
            if domain_interests:
                return domain_interests[0][0]
            
            return None
            
        except Exception as e:
            logger.error(f"Error predicting next click: {e}")
            return None
    
    def load_context(self):
        """Load user context from file."""
        context_path = os.path.expanduser("~/.verbum6/user_context.json")
        try:
            if os.path.exists(context_path):
                with open(context_path, 'r') as f:
                    self.preferences = json.load(f)
        except Exception as e:
            print(f"Error loading user context: {e}")
    
    def save_context(self):
        """Save user context to file."""
        context_path = os.path.expanduser("~/.verbum6/user_context.json")
        os.makedirs(os.path.dirname(context_path), exist_ok=True)
        with open(context_path, 'w') as f:
            json.dump(self.preferences, f)