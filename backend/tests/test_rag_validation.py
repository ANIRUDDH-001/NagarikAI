"""
RAG Validation Suite — Phase 5
Measures Precision@3 and Mean Reciprocal Rank (MRR) across 12 gold-standard cases.
Not pass/fail, but a benchmark reporting tool with minimum assertions.
"""
import sys
import os
from pathlib import Path
import json

# Add backend to path to allow direct tools reference
backend_path = Path(__file__).resolve().parent.parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from agent.tools import search_schemes

class RagValidator:
    def __init__(self):
        # 12 Gold Standard Test Cases
        self.test_cases = [
            {
                "profile": {"age": 45, "state": "bihar", "category": "SC", "annual_income": 60000, "occupation": "farmer"},
                "query": "farming support",
                "expected_schemes": ["PM Kisan Samman Nidhi", "PM Fasal Bima Yojana"]
            },
            {
                "profile": {"age": 30, "state": "uttar_pradesh", "category": "OBC", "annual_income": 150000, "gender": "female"},
                "query": "business loan",
                "expected_schemes": ["PM MUDRA Yojana"]
            },
            {
                "profile": {"age": 19, "state": "maharashtra", "category": "SC", "annual_income": 90000},
                "query": "scholarship for studies",
                "expected_schemes": ["Post Matric Scholarship"]
            },
            {
                "profile": {"age": 60, "state": "bihar", "category": "General", "annual_income": 30000, "is_bpl": True},
                "query": "old age pension",
                "expected_schemes": ["National Social Assistance Programme"]
            },
            {
                "profile": {"age": 35, "gender": "female", "state": "uttar_pradesh", "category": "OBC", "annual_income": 80000, "is_bpl": True},
                "query": "free gas connection",
                "expected_schemes": ["PM Ujjwala Yojana"]
            },
            {
                "profile": {"age": 25, "gender": "female", "state": "bihar", "annual_income": 100000},
                "query": "housing for family",
                "expected_schemes": ["PM Awas Yojana Gramin"]
            },
            {
                "profile": {"age": 40, "occupation": "street_vendor", "state": "delhi", "annual_income": 100000},
                "query": "working capital loan",
                "expected_schemes": ["PM SVANidhi"]
            },
            {
                "profile": {"age": 55, "marital_status": "widow", "state": "maharashtra", "annual_income": 40000},
                "query": "support for widow",
                "expected_schemes": ["NSAP Widow Pension"]
            },
            {
                "profile": {"age": 8, "gender": "female", "state": "uttar_pradesh", "annual_income": 150000},
                "query": "savings for daughter education",
                "expected_schemes": ["Sukanya Samridhi Yojana"]
            },
            {
                "profile": {"age": 35, "occupation": "farmer", "state": "bihar", "annual_income": 70000},
                "query": "health insurance coverage",
                "expected_schemes": ["Ayushman Bharat PM-JAY"]
            },
            {
                "profile": {"age": 28, "annual_income": 50000, "is_bpl": True, "state": "rajasthan"},
                "query": "free food grains",
                "expected_schemes": ["PM Garib Kalyan Anna Yojana"]
            },
            {
                "profile": {"age": 32, "occupation": "farmer", "state": "uttar_pradesh", "annual_income": 85000},
                "query": "crop loan credit",
                "expected_schemes": ["Kisan Credit Card"]
            }
        ]

    def _matches_expected(self, result_name: str, expected_list: list) -> bool:
        """Helper to check if result name overlaps significantly with expected titles.
        Normalizes acronyms ('PM' <=> 'Pradhan Mantri') for accurate string matching.
        """
        r_clean = result_name.lower().strip().replace("pradhan mantri", "pm")
        for exp in expected_list:
            exp_clean = exp.lower().strip().replace("pradhan mantri", "pm")
            if exp_clean in r_clean or r_clean in exp_clean:
                return True
        return False

    def precision_at_k(self, k=3):
        """Calculates percentage of queries where AT LEAST ONE expected scheme sits in top k."""
        hits = 0
        details = []

        print(f"\nEvaluating Precision@{k}...")
        for i, case in enumerate(self.test_cases, 1):
            res = search_schemes(case["profile"])
            top_k = res[:k]
            
            found = False
            found_name = ""
            for r in top_k:
                if self._matches_expected(r["scheme_name"], case["expected_schemes"]):
                    found = True
                    found_name = r["scheme_name"]
                    break

            if found:
                hits += 1
                print(f"  [Case {i}] Hit: {found_name}")
            else:
                top_3_list = [r["scheme_name"] for r in top_k]
                print(f"  [Case {i}] Miss: Expected {case['expected_schemes']} | Got: {top_3_list}")
                details.append({
                    "case": i,
                    "query": case["query"],
                    "expected": case["expected_schemes"],
                    "got": top_3_list
                })

        score = hits / len(self.test_cases)
        return score, hits, len(self.test_cases), details

    def mean_reciprocal_rank(self):
        """Calculates Mean Reciprocal Rank (MRR = average 1/Rank of first expected response)."""
        rr_sum = 0
        
        print("\nEvaluating MRR...")
        for i, case in enumerate(self.test_cases, 1):
            res = search_schemes(case["profile"])
            rank = 0
            for r_idx, r in enumerate(res, 1):
                if self._matches_expected(r["scheme_name"], case["expected_schemes"]):
                    rank = r_idx
                    break
            if rank > 0:
                recip = 1.0 / rank
                rr_sum += recip
                print(f"  [Case {i}] Rank: {rank} (1/R: {recip:.3f})")
            else:
                print(f"  [Case {i}] Rank: Not Found (1/R: 0.0)")

        score = rr_sum / len(self.test_cases)
        return score

    def false_positive_check(self) -> bool:
        """Confirms that a rich person profile doesn't include BPL schemes."""
        rich_profile = {"age": 45, "state": "bihar", "annual_income": 500000}
        res = search_schemes(rich_profile)
        
        print("\nEvaluating False Positives for Rich Person...")
        failures = []
        for r in res:
            breakdown = r.get("eligibility_breakdown", {})
            bpl_req = breakdown.get("bpl")
            
            # If bpl criteria exists and it fails (passes=False), then it's a BPL scheme rich person doesn't qualify for.
            if bpl_req and not bpl_req["passes"]:
                failures.append(r["scheme_name"])
            
            # Check if name contains implicit BPL triggers just to double check
            if "bpl" in r["scheme_name"].lower() or "anna yojana" in r["scheme_name"].lower():
                 failures.append(r["scheme_name"])

        if failures:
             print(f"  FAIL: Found ineligible BPL/Poor schemes for rich person: {failures}")
             return False
        
        print("  PASS: No BPL-only schemes returned for high-income profile")
        return True

    def generate_validation_report(self) -> dict:
        """Runs benchmarks and compiles into dictionary verdict bundle."""
        p_score, hits, total, failure_cases = self.precision_at_k(3)
        mrr_score = self.mean_reciprocal_rank()
        fp_status = self.false_positive_check()

        precision_ok = p_score >= 0.75
        mrr_ok = mrr_score >= 0.5
        fp_ok = fp_status is True

        passed = precision_ok and mrr_ok and fp_ok

        report = {
            "test_timestamp": "",
            "metrics": {
                "precision_at_3": round(p_score, 2),
                "hits": hits,
                "total": total,
                "mean_reciprocal_rank": round(mrr_score, 2)
            },
            "false_positive": {
                "safe": fp_status
            },
            "compliance": {
                "precision_threshold": precision_ok,
                "mrr_threshold": mrr_ok,
                "fp_threshold": fp_ok
            },
            "valid_passed": passed,
            "missed_cases": failure_cases
        }

        print("\n" + "="*50)
        print("          RAG VALIDATION REPORT Summary")
        print("="*50)
        print(f"Precision@3 : {p_score:.2%} ({hits}/{total}) " + ("✅" if precision_ok else "❌"))
        print(f"MRR          : {mrr_score:.3f}             " + ("✅" if mrr_ok else "❌"))
        print(f"False Pos.   : {'✅ Clean' if fp_status else '❌ Leaks found'}")
        print("-"*50)
        print(f"Verdict: {'🚀 ACCEPTABLE' if passed else '⚠️ FAIL - Fix DB/Metadata'}")

        return report

# --------------------------------------------------------------------------
# Pytest compatibility structured asserts (if running standard testing)
# --------------------------------------------------------------------------

def test_rag_benchmark():
    """Single test function for Pytest asserting minimum threshold validations."""
    validator = RagValidator()
    rep = validator.generate_validation_report()
    
    assert rep["metrics"]["precision_at_3"] >= 0.75, "Precision@3 below 75%"
    assert rep["metrics"]["mean_reciprocal_rank"] >= 0.5, "MRR below 0.5"
    assert rep["false_positive"]["safe"] is True, "Ineligible BPL schemes leaked for high-income"

if __name__ == "__main__":
    validator = RagValidator()
    validator.generate_validation_report()
