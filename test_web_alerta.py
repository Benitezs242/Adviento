import unittest

import web_alerta


class TestWebAlerta(unittest.TestCase):
    def test_start_monitor_service_returns_result(self):
        result = web_alerta.start_monitor_service()
        self.assertIn("status", result)
        self.assertIn("message", result)

    def test_build_status_payload_has_expected_keys(self):
        payload = web_alerta.build_status_payload()
        self.assertIn("items", payload)
        self.assertIn("events", payload)
        self.assertIn("error", payload)
        self.assertIn("checked_at", payload)

    def test_probe_product_returns_result(self):
        result = web_alerta.probe_product("Serum Crecimiento De Pestanas Trendy 4,5g")
        self.assertIn("searched_for", result)
        self.assertIn("matches", result)
        self.assertIn("status", result)


if __name__ == "__main__":
    unittest.main()
