from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

from backend.lotgenius.datasources.base import SoldComp
from backend.lotgenius.datasources.ebay_scraper import (
    _build_targeted_query,
    _filter_results,
    _title_similarity,
    fetch_sold_comps,
)


class TestQueryBuilding:
    """Test the targeted query building functionality."""

    def test_query_priority_upc_exact(self):
        """UPC gets highest priority and is quoted for exact match."""
        query = _build_targeted_query(
            query="iPhone 13 Pro Max",
            brand="Apple",
            model="iPhone 13 Pro",
            upc="123456789012",
            asin="B08N5WRWNW",
        )
        assert query == '"123456789012" Apple'
        assert "iPhone" not in query  # Should not fall back to title
        assert "B08N5WRWNW" not in query  # Should not use ASIN when UPC present

    def test_query_priority_asin_exact(self):
        """ASIN gets second priority when UPC not available."""
        query = _build_targeted_query(
            query="iPhone 13 Pro Max",
            brand="Apple",
            model="iPhone 13 Pro",
            upc=None,
            asin="B08N5WRWNW",
        )
        assert query == '"B08N5WRWNW" Apple'
        assert "iPhone" not in query  # Should not fall back to title

    def test_query_brand_model(self):
        """Brand+Model combo when no identifiers available."""
        query = _build_targeted_query(
            query="iPhone 13 Pro Max 256GB Blue",
            brand="Apple",
            model="iPhone 13 Pro",
            upc=None,
            asin=None,
        )
        assert query == '"Apple" "iPhone 13 Pro"'

    def test_query_filtered_title(self):
        """Title fallback removes generic terms."""
        query = _build_targeted_query(
            query="Lot of 3 assorted widgets bundle pack",
            brand=None,
            model=None,
            upc=None,
            asin=None,
        )
        assert query == '"3 widgets"'  # Generic terms removed, keeping numbers

    def test_query_filtered_title_single_word(self):
        """Single word after filtering doesn't get quoted."""
        query = _build_targeted_query(
            query="lot of widgets", brand=None, model=None, upc=None, asin=None
        )
        assert query == "widgets"  # Single word, no quotes

    def test_query_fallback_when_all_filtered(self):
        """Fallback to original query when all words are generic."""
        query = _build_targeted_query(
            query="lot bundle assorted pack",
            brand=None,
            model=None,
            upc=None,
            asin=None,
        )
        assert query == "lot bundle assorted pack"  # Original preserved


class TestTitleSimilarity:
    """Test similarity calculation functionality."""

    def test_similarity_identical(self):
        """Identical titles should have similarity of 1.0."""
        similarity = _title_similarity("iPhone 13 Pro Max", "iPhone 13 Pro Max")
        assert similarity == 1.0

    def test_similarity_different_order(self):
        """Different word order should still have high similarity."""
        similarity = _title_similarity("iPhone 13 Pro Max", "Max Pro iPhone 13")
        assert similarity >= 0.8  # token_set_ratio handles word order

    def test_similarity_partial_match(self):
        """Partial matches should have moderate similarity."""
        similarity = _title_similarity("iPhone 13 Pro", "iPhone 13 Pro Max 256GB")
        assert 0.8 <= similarity <= 1.0  # token_set_ratio is more generous

    def test_similarity_completely_different(self):
        """Completely different titles should have low similarity."""
        similarity = _title_similarity("iPhone 13 Pro", "Samsung Galaxy S22")
        assert similarity <= 0.3


class TestResultFiltering:
    """Test the result filtering functionality."""

    def create_test_comp(self, title, price=100.0, sold_days_ago=30):
        """Helper to create SoldComp for testing."""
        sold_at = datetime.now(timezone.utc) - timedelta(days=sold_days_ago)
        return SoldComp(
            source="ebay",
            title=title,
            price=price,
            condition="Used",
            sold_at=sold_at,
            url="https://example.com",
            id=None,
            match_score=0.0,
            meta={},
        )

    def test_filter_similarity_threshold(self):
        """Filter out items below similarity threshold."""
        comps = [
            self.create_test_comp("iPhone 13 Pro Max 256GB Blue"),  # High similarity
            self.create_test_comp("Samsung Galaxy S22 Ultra"),  # Low similarity
            self.create_test_comp("Apple iPhone 13 Pro"),  # Medium similarity
        ]

        filtered, diagnostics = _filter_results(
            comps, "iPhone 13 Pro Max", "Apple", "iPhone 13 Pro", None, 180, 0.70
        )

        # Should keep high and medium similarity, drop Samsung
        assert len(filtered) <= 2
        assert diagnostics["similarity"] >= 1
        titles = [comp.title for comp in filtered]
        assert not any("Samsung" in title for title in titles)

    def test_filter_recency_threshold(self):
        """Filter out items older than lookback period."""
        comps = [
            self.create_test_comp("iPhone 13 Pro Max", sold_days_ago=30),  # Recent
            self.create_test_comp("iPhone 13 Pro Max", sold_days_ago=200),  # Too old
            self.create_test_comp(
                "iPhone 13 Pro Max", sold_days_ago=150
            ),  # Within range
        ]

        filtered, diagnostics = _filter_results(
            comps, "iPhone 13 Pro Max", "Apple", "iPhone 13 Pro", None, 180, 0.50
        )

        # Should keep recent and within-range, drop too old
        assert len(filtered) == 2
        assert diagnostics["recency"] >= 1

    def test_filter_price_outliers(self):
        """Filter out extreme price outliers using MAD."""
        # Create comps with normal prices around $100 and one extreme outlier
        normal_prices = [95, 98, 100, 102, 105]
        comps = [
            self.create_test_comp(f"iPhone 13 Pro {i}", price=price)
            for i, price in enumerate(normal_prices)
        ]
        # Add extreme outlier (5x median)
        comps.append(self.create_test_comp("iPhone 13 Pro Outlier", price=500.0))

        filtered, diagnostics = _filter_results(
            comps, "iPhone 13 Pro", "Apple", "iPhone 13 Pro", None, 180, 0.50
        )

        # Should filter out the outlier
        assert len(filtered) == 5  # Normal prices kept
        assert diagnostics["price"] == 1  # One outlier removed
        prices = [comp.price for comp in filtered]
        assert max(prices) <= 110  # No extreme prices remain

    def test_condition_filter_for_parts(self):
        """Filter out 'for parts' items when condition is not salvage."""
        comps = [
            self.create_test_comp("iPhone 13 Pro Max Working Condition"),
            self.create_test_comp("iPhone 13 Pro Max FOR PARTS NOT WORKING"),
            self.create_test_comp("iPhone 13 Pro Max - Broken Screen Repair Only"),
            self.create_test_comp("iPhone 13 Pro Max Excellent Condition"),
        ]

        filtered, diagnostics = _filter_results(
            comps, "iPhone 13 Pro Max", "Apple", "iPhone 13 Pro", "New", 180, 0.50
        )

        # Should filter out for-parts items
        assert len(filtered) == 2  # Only working condition items
        assert diagnostics["condition"] == 2  # Two condition problems filtered
        titles = [comp.title.lower() for comp in filtered]
        assert not any("for parts" in title or "broken" in title for title in titles)

    def test_condition_filter_allows_salvage(self):
        """Don't filter 'for parts' when condition_hint is salvage."""
        comps = [
            self.create_test_comp("iPhone 13 Pro Max FOR PARTS NOT WORKING"),
            self.create_test_comp("iPhone 13 Pro Max - Broken Screen"),
        ]

        filtered, diagnostics = _filter_results(
            comps, "iPhone 13 Pro Max", "Apple", "iPhone 13 Pro", "salvage", 180, 0.50
        )

        # Should keep all items when looking for salvage
        assert len(filtered) == 2
        assert diagnostics["condition"] == 0

    def test_model_presence_requirement(self):
        """Require model token to be present in title when model specified."""
        comps = [
            self.create_test_comp("Apple iPhone 13 Pro Max 256GB"),  # Has "Pro"
            self.create_test_comp("Apple iPhone 13 Mini 128GB"),  # No "Pro"
            self.create_test_comp("Apple iPhone 13 256GB"),  # No "Pro"
        ]

        filtered, diagnostics = _filter_results(
            comps, "iPhone 13 Pro", "Apple", "Pro", None, 180, 0.50
        )

        # Should only keep items with "Pro" in title
        assert len(filtered) == 1
        assert "Pro Max" in filtered[0].title
        assert diagnostics["similarity"] == 2  # Two filtered for missing model

    def test_quality_score_calculation(self):
        """Verify quality scores are calculated and attached."""
        comps = [
            self.create_test_comp("iPhone 13 Pro Max", sold_days_ago=10),  # Recent
            self.create_test_comp("iPhone 13 Pro Max", sold_days_ago=100),  # Older
        ]

        filtered, _ = _filter_results(
            comps, "iPhone 13 Pro Max", "Apple", "iPhone 13 Pro", None, 180, 0.50
        )

        assert len(filtered) == 2
        # Check quality scores exist and recent item has higher score
        recent_comp = [
            c for c in filtered if (datetime.now(timezone.utc) - c.sold_at).days < 20
        ][0]
        older_comp = [
            c for c in filtered if (datetime.now(timezone.utc) - c.sold_at).days > 50
        ][0]

        assert "quality_score" in recent_comp.meta
        assert "quality_score" in older_comp.meta
        assert recent_comp.meta["quality_score"] > older_comp.meta["quality_score"]
        assert recent_comp.match_score == recent_comp.meta["quality_score"]


class TestIntegration:
    """Test integration with the main fetch_sold_comps function."""

    @patch("backend.lotgenius.datasources.ebay_scraper.requests.get")
    @patch("backend.lotgenius.datasources.ebay_scraper.get_cached_comps")
    def test_fetch_sold_comps_uses_targeted_query(self, mock_cache, mock_get):
        """Verify fetch_sold_comps uses the new query building."""
        # Mock cache miss
        mock_cache.return_value = None

        # Mock HTML response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = """
        <div>
            <li class="s-item">
                <div class="s-item__title">iPhone 13 Pro Max 256GB</div>
                <div class="s-item__price">$899.99</div>
                <a class="s-item__link" href="https://example.com/item1">Link</a>
                <div class="s-item__ended-date">Dec 15, 2024</div>
            </li>
        </div>
        """
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Mock settings
        with patch(
            "backend.lotgenius.datasources.ebay_scraper.settings"
        ) as mock_settings:
            mock_settings.SCRAPER_TOS_ACK = True
            mock_settings.ENABLE_EBAY_SCRAPER = True
            mock_settings.SCRAPER_SIMILARITY_MIN = 0.70

            comps = fetch_sold_comps(
                query="iPhone 13 Pro Max",
                brand="Apple",
                model="iPhone 13 Pro",
                upc="123456789012",
                asin=None,
            )

            # Verify the targeted query was built (UPC priority)
            mock_get.assert_called_once()
            called_url = mock_get.call_args[0][0]
            # The URL should contain the quoted UPC, not the original query
            assert "123456789012" in called_url
            assert "Apple" in called_url

            # Should return filtered results
            assert len(comps) <= 1  # May be filtered down
