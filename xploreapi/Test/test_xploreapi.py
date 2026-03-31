import unittest
import logging
import sys
import os
import json
import xmltodict

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from xploreapi import XPLORE

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class TestXploreImages(unittest.TestCase):

    def setUp(self):
        # ==== CONFIGURATION ====
        self.api_key = ""
        self.auth_token = ""
        self.response_format = "json"   # Change to "xml" to test XML response

        # Initialize SDK
        self.xplore = XPLORE(self.api_key)

        # Obtain CLToken
        self.xplore.cltoken = self.xplore.getImageToken(self.auth_token)
        logging.info("CLToken obtained: %s", self.xplore.cltoken)

    def test_search_images(self):
        """Search images and print response in JSON or XML format, with auto-conversion."""
        query_text = "AI"

        # Retry once if 401 occurs
        for attempt in range(2):
            try:
                response = self.xplore.searchImages(
                    querytext=query_text,
                    image_keyword=None,
                    content_type=None,
                    start_record=1,
                    max_records=5,
                    sort_by="newest",
                    format=self.response_format
                )
                break
            except Exception as e:
                if "401" in str(e) and attempt == 0:
                    logging.warning("401 Unauthorized - refreshing CLToken and retrying")
                    self.xplore.cltoken = self.xplore.getImageToken(self.auth_token)
                else:
                    raise

        print("\n=== Search Images Response ===")

        # Convert XML to JSON automatically if needed
        if isinstance(response, str):
            if self.response_format.lower() == "xml":
                try:
                    parsed_xml = xmltodict.parse(response)
                    print(json.dumps(parsed_xml, indent=4))
                except Exception as e:
                    print("❌ Failed to parse XML response:", e)
                    print("Raw XML response:\n", response)
            else:
                # Try JSON parse directly
                try:
                    print(json.dumps(json.loads(response), indent=4))
                except Exception as e:
                    print("❌ Failed to parse JSON response:", e)
                    print("Raw response:\n", response)
        else:
            # Already parsed as dict
            print(json.dumps(response, indent=4))

if __name__ == "__main__":
    unittest.main()
