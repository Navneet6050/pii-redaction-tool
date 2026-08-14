#!/usr/bin/env python3
"""Unit tests for Evaluation Suite metrics calculation & privacy exports."""
import os
import sys
import unittest
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from evaluate_redactor import evaluate

class TestEvaluationSuite(unittest.TestCase):
    def test_evaluation_execution_and_privacy_output(self):
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        metrics_json_path = os.path.join(base_dir, "evaluation", "metrics.json")
        report_md_path = os.path.join(base_dir, "evaluation", "evaluation_report.md")

        # Assert evaluation outputs exist
        self.assertTrue(os.path.exists(metrics_json_path), "metrics.json missing.")
        self.assertTrue(os.path.exists(report_md_path), "evaluation_report.md missing.")

        with open(metrics_json_path, "r", encoding="utf-8") as f:
            metrics_data = json.load(f)

        self.assertIn("real_document_generic_mode", metrics_data)
        self.assertIn("real_document_domain_assisted_mode", metrics_data)
        self.assertIn("synthetic_benchmark", metrics_data)

        generic_summary = metrics_data["real_document_generic_mode"]
        domain_summary = metrics_data["real_document_domain_assisted_mode"]

        self.assertGreaterEqual(generic_summary["micro_f1"], 0.80)
        self.assertGreaterEqual(domain_summary["micro_f1"], 0.90)

if __name__ == "__main__":
    unittest.main()
