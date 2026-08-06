from django.test import SimpleTestCase

from fretes.services.geocoding_service import build_geocoding_cache_key


class GeocodingCacheKeyTests(SimpleTestCase):
    def test_cache_key_is_memcached_safe_and_stable(self):
        key = build_geocoding_cache_key("  Carmo da Mata  ", "MG")
        self.assertEqual(key, build_geocoding_cache_key("carmo da mata", "mg"))
        self.assertNotIn(" ", key)
        self.assertNotIn("Carmo", key)
        self.assertLessEqual(len(key), 250)
