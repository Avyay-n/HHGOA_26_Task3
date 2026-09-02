"""
Automated tests for Face Detection & Blockchain Verification Pipeline.
"""

import os
import unittest
from pathlib import Path
from face_module.detector import process_face
from search_module.searcher import search_social_post, _detect_platform, _extract_author
from chain_module.verifier import hash_record, BlockchainVerifier


class TestPipeline(unittest.TestCase):

    def test_01_face_detection_vitalik(self):
        """Tests face detection on sample_vitalik.jpg."""
        img_path = "test_faces/sample_vitalik.jpg"
        if not os.path.exists(img_path):
            self.skipTest(f"{img_path} not found")
        
        result = process_face(img_path, margin_percent=0.15, output_path="temp_test_crop.jpg")
        self.assertTrue(result.success, f"Face detection failed: {result.error_message}")
        self.assertIsNotNone(result.crop_path)
        self.assertTrue(os.path.exists(result.crop_path))
        self.assertGreater(result.faces_detected_count, 0)
        self.assertEqual(len(result.face_box), 4)

    def test_02_face_detection_elon(self):
        """Tests face detection on sample_elon.jpg."""
        img_path = "test_faces/sample_elon.jpg"
        if not os.path.exists(img_path):
            self.skipTest(f"{img_path} not found")

        result = process_face(img_path, margin_percent=0.15, output_path="temp_test_crop_elon.jpg")
        self.assertTrue(result.success, f"Face detection failed: {result.error_message}")
        self.assertTrue(os.path.exists(result.crop_path))

    def test_03_platform_detection(self):
        """Tests URL platform detection helper."""
        self.assertEqual(_detect_platform("https://twitter.com/elonmusk/status/123"), "Twitter/X")
        self.assertEqual(_detect_platform("https://x.com/VitalikButerin/status/456"), "Twitter/X")
        self.assertEqual(_detect_platform("https://linkedin.com/in/satyanadella"), "LinkedIn")
        self.assertEqual(_detect_platform("https://reddit.com/r/ethereum/comments/abc"), "Reddit")
        self.assertEqual(_detect_platform("https://youtube.com/watch?v=xyz"), "YouTube")

    def test_04_author_extraction(self):
        """Tests handle extraction helper."""
        self.assertEqual(_extract_author("https://x.com/elonmusk/status/123", "", ""), "@elonmusk")
        self.assertEqual(_extract_author("https://linkedin.com/in/vitalik-buterin", "", ""), "vitalik-buterin")

    def test_05_deterministic_keccak256_hashing(self):
        """Tests deterministic keccak256 hashing across unordered dictionary keys."""
        dict1 = {"post_url": "https://x.com/test", "author": "@test", "title": "Test Title"}
        dict2 = {"title": "Test Title", "author": "@test", "post_url": "https://x.com/test"}

        hash1 = hash_record(dict1)
        hash2 = hash_record(dict2)

        self.assertIsInstance(hash1, bytes)
        self.assertTrue(hasattr(hash1, "hex"))
        self.assertEqual(len(hash1), 32)
        self.assertEqual(hash1.hex(), hash2.hex())

    def test_06_search_and_verifier_flow(self):
        """Tests integration of searcher and blockchain verification simulation."""
        search_res = search_social_post("temp_test_crop.jpg", mock_fallback=True)
        self.assertTrue(search_res.success)
        self.assertIn("http", search_res.post_url)

        content_hash = hash_record(search_res.to_dict())
        self.assertEqual(len(content_hash), 32)

        verifier = BlockchainVerifier()
        self.assertIsNotNone(verifier.get_network_name())


if __name__ == "__main__":
    unittest.main()
