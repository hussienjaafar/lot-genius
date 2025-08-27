"""
Machine Learning-enhanced product matching for external comparables.
Uses multiple signals and fuzzy matching to improve comp quality.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any, Dict, List, Tuple


@dataclass
class MatchFeatures:
    """Features extracted for ML-style product matching."""

    title_similarity: float = 0.0
    brand_match: float = 0.0
    model_match: float = 0.0
    category_relevance: float = 0.0
    price_reasonableness: float = 0.0
    keyword_density: float = 0.0
    specification_match: float = 0.0
    condition_alignment: float = 0.0


class ProductMatcher:
    """Advanced product matching using ML techniques."""

    def __init__(self):
        # Category mapping for better matching
        self.category_keywords = {
            "electronics": [
                "phone",
                "tablet",
                "laptop",
                "computer",
                "tv",
                "monitor",
                "camera",
                "headphones",
                "earbuds",
                "speaker",
                "gaming",
                "console",
                "router",
            ],
            "clothing": [
                "shirt",
                "pants",
                "dress",
                "shoes",
                "sneakers",
                "jacket",
                "coat",
                "jeans",
                "sweater",
                "boots",
                "sandals",
                "hat",
                "belt",
                "watch",
            ],
            "home": [
                "vacuum",
                "blender",
                "microwave",
                "coffee",
                "pot",
                "pan",
                "chair",
                "table",
                "lamp",
                "mattress",
                "pillow",
                "tools",
                "drill",
                "saw",
            ],
        }

        # Brand name variations for better matching
        self.brand_aliases = {
            "apple": ["apple", "iphone", "ipad", "macbook", "airpods"],
            "samsung": ["samsung", "galaxy"],
            "sony": ["sony", "playstation", "ps4", "ps5"],
            "nike": ["nike", "air jordan", "jordan"],
            "adidas": ["adidas", "three stripes"],
        }

    def normalize_text(self, text: str) -> str:
        """Normalize text for better comparison."""
        if not text:
            return ""

        # Convert to lowercase and remove special characters
        text = re.sub(r"[^\w\s]", " ", text.lower())
        # Remove extra whitespace
        text = " ".join(text.split())
        return text

    def extract_specifications(self, text: str) -> Dict[str, str]:
        """Extract specifications from product text."""
        specs = {}
        text_lower = text.lower()

        # Size patterns
        size_patterns = [
            r'(\d+(?:\.\d+)?)\s*(?:inch|in|")',  # Screen sizes
            r"size\s*(\d+)",  # Clothing sizes
            r"(\d+)\s*(?:gb|tb)",  # Storage
            r"(\d+)\s*(?:oz|lb|kg)",  # Weight
        ]

        for pattern in size_patterns:
            matches = re.findall(pattern, text_lower)
            if matches:
                specs["size"] = matches[0]
                break

        # Color extraction
        colors = [
            "black",
            "white",
            "red",
            "blue",
            "green",
            "silver",
            "gold",
            "gray",
            "pink",
        ]
        for color in colors:
            if color in text_lower:
                specs["color"] = color
                break

        # Model year
        year_match = re.search(r"20\d{2}", text)
        if year_match:
            specs["year"] = year_match.group()

        return specs

    def calculate_title_similarity(self, title1: str, title2: str) -> float:
        """Calculate semantic similarity between titles."""
        norm1 = self.normalize_text(title1)
        norm2 = self.normalize_text(title2)

        if not norm1 or not norm2:
            return 0.0

        # Use SequenceMatcher for fuzzy matching
        similarity = SequenceMatcher(None, norm1, norm2).ratio()

        # Boost for exact word matches
        words1 = set(norm1.split())
        words2 = set(norm2.split())
        word_overlap = len(words1 & words2) / max(len(words1), len(words2), 1)

        # Combine sequence similarity with word overlap
        return (similarity * 0.6) + (word_overlap * 0.4)

    def calculate_brand_match(self, target_brand: str, listing_text: str) -> float:
        """Calculate brand matching score with alias support."""
        if not target_brand:
            return 0.0

        target_brand_norm = self.normalize_text(target_brand)
        listing_norm = self.normalize_text(listing_text)

        # Direct brand match
        if target_brand_norm in listing_norm:
            return 1.0

        # Check brand aliases
        for brand, aliases in self.brand_aliases.items():
            if target_brand_norm in aliases or any(
                alias in target_brand_norm for alias in aliases
            ):
                if any(alias in listing_norm for alias in aliases):
                    return 0.9

        # Fuzzy brand matching
        for word in listing_norm.split():
            similarity = SequenceMatcher(None, target_brand_norm, word).ratio()
            if similarity > 0.8:
                return similarity

        return 0.0

    def calculate_category_relevance(
        self, target_category: str, listing_text: str
    ) -> float:
        """Calculate category relevance score."""
        if not target_category or target_category not in self.category_keywords:
            return 0.0

        listing_norm = self.normalize_text(listing_text)
        category_keywords = self.category_keywords[target_category]

        matches = sum(1 for keyword in category_keywords if keyword in listing_norm)
        return min(matches / 3.0, 1.0)  # Normalize to 0-1 scale

    def calculate_price_reasonableness(
        self, price: float, expected_range: Tuple[float, float]
    ) -> float:
        """Calculate if price is in reasonable range."""
        if price <= 0:
            return 0.0

        min_price, max_price = expected_range
        if min_price <= price <= max_price:
            return 1.0
        elif price < min_price:
            return max(0.0, price / min_price)
        else:  # price > max_price
            return max(0.0, max_price / price)

    def extract_features(
        self, listing: Dict[str, Any], target: Dict[str, Any]
    ) -> MatchFeatures:
        """Extract all matching features for ML scoring."""

        listing_title = listing.get("title", "")
        listing_text = f"{listing_title} {listing.get('description', '')}"

        target_title = target.get("title", "")
        target_brand = target.get("brand", "")
        target_model = target.get("model", "")
        target_category = target.get("category", "")

        features = MatchFeatures()

        # Title similarity
        features.title_similarity = self.calculate_title_similarity(
            target_title, listing_title
        )

        # Brand matching
        features.brand_match = self.calculate_brand_match(target_brand, listing_text)

        # Model matching
        if target_model:
            model_norm = self.normalize_text(target_model)
            listing_norm = self.normalize_text(listing_text)
            features.model_match = 1.0 if model_norm in listing_norm else 0.0

        # Category relevance
        features.category_relevance = self.calculate_category_relevance(
            target_category, listing_text
        )

        # Price reasonableness (estimate range from target or use defaults)
        price = float(listing.get("price", 0))
        expected_range = target.get("price_range", (10, 10000))  # Default range
        features.price_reasonableness = self.calculate_price_reasonableness(
            price, expected_range
        )

        # Keyword density (important terms per text length)
        important_words = [target_title, target_brand, target_model]
        important_words = [w for w in important_words if w]
        if important_words:
            listing_words = self.normalize_text(listing_text).split()
            keyword_count = sum(
                1
                for word in listing_words
                if any(kw.lower() in word for kw in important_words)
            )
            features.keyword_density = min(
                keyword_count / max(len(listing_words), 1), 1.0
            )

        # Specification matching
        target_specs = self.extract_specifications(target_title)
        listing_specs = self.extract_specifications(listing_text)
        if target_specs and listing_specs:
            spec_matches = sum(
                1 for k, v in target_specs.items() if listing_specs.get(k) == v
            )
            features.specification_match = spec_matches / max(len(target_specs), 1)

        # Condition alignment
        target_condition = target.get("condition", "").lower()
        listing_condition = listing.get("condition", "").lower()
        if target_condition and listing_condition:
            condition_similarity = SequenceMatcher(
                None, target_condition, listing_condition
            ).ratio()
            features.condition_alignment = condition_similarity

        return features

    def calculate_match_score(self, features: MatchFeatures) -> float:
        """
        Calculate final match score using weighted features.
        Weights optimized for liquidation business use case.
        """
        weights = {
            "title_similarity": 0.25,  # Important for overall match
            "brand_match": 0.20,  # Critical for brand products
            "model_match": 0.15,  # High specificity
            "category_relevance": 0.10,  # Basic filtering
            "price_reasonableness": 0.10,  # Avoid outliers
            "keyword_density": 0.08,  # Text quality signal
            "specification_match": 0.07,  # Technical accuracy
            "condition_alignment": 0.05,  # Condition matching
        }

        score = (
            features.title_similarity * weights["title_similarity"]
            + features.brand_match * weights["brand_match"]
            + features.model_match * weights["model_match"]
            + features.category_relevance * weights["category_relevance"]
            + features.price_reasonableness * weights["price_reasonableness"]
            + features.keyword_density * weights["keyword_density"]
            + features.specification_match * weights["specification_match"]
            + features.condition_alignment * weights["condition_alignment"]
        )

        return min(score, 1.0)

    def match_listings(
        self,
        listings: List[Dict[str, Any]],
        target: Dict[str, Any],
        min_score: float = 0.3,
    ) -> List[Tuple[Dict[str, Any], float]]:
        """Match listings against target item with ML scoring."""

        results = []

        for listing in listings:
            features = self.extract_features(listing, target)
            score = self.calculate_match_score(features)

            if score >= min_score:
                results.append((listing, score))

        # Sort by score descending
        results.sort(key=lambda x: x[1], reverse=True)
        return results


# Global matcher instance
_matcher = ProductMatcher()


def enhanced_product_matching(
    listings: List[Dict[str, Any]],
    target_item: Dict[str, Any],
    min_confidence: float = 0.4,
) -> List[Tuple[Dict[str, Any], float]]:
    """
    Public interface for ML-enhanced product matching.
    """
    return _matcher.match_listings(listings, target_item, min_confidence)


def calculate_listing_similarity(
    listing: Dict[str, Any], target: Dict[str, Any]
) -> float:
    """
    Calculate similarity score between a listing and target item.
    """
    features = _matcher.extract_features(listing, target)
    return _matcher.calculate_match_score(features)
