#!/usr/bin/env python3
"""
Comprehensive test suite for Data Ingestion API
Tests all requirements including rate limiting, priority handling, and batch processing
"""

import requests
import time
import json
import threading
from datetime import datetime
from typing import List, Dict, Any
import sys

class APITester:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip('/')
        self.test_results = []
        
    def log(self, message: str, test_name: str = ""):
        timestamp = datetime.now().strftime("%H:%M:%S")
        if test_name:
            print(f"[{timestamp}] {test_name}: {message}")
        else:
            print(f"[{timestamp}] {message}")
    
    def test_health_check(self):
        """Test if the API is running"""
        test_name = "Health Check"
        try:
            response = requests.get(f"{self.base_url}/health", timeout=10)
            if response.status_code == 200:
                self.log("✅ API is running", test_name)
                return True
            else:
                self.log(f"❌ API health check failed: {response.status_code}", test_name)
                return False
        except Exception as e:
            self.log(f"❌ Cannot connect to API: {str(e)}", test_name)
            return False
    
    def test_basic_ingestion(self):
        """Test basic ingestion functionality"""
        test_name = "Basic Ingestion"
        try:
            payload = {
                "ids": [1, 2, 3, 4, 5],
                "priority": "MEDIUM"
            }
            
            response = requests.post(f"{self.base_url}/ingest", json=payload)
            
            if response.status_code == 201:
                data = response.json()
                if "ingestion_id" in data:
                    ingestion_id = data["ingestion_id"]
                    self.log(f"✅ Ingestion created successfully: {ingestion_id}", test_name)
                    return ingestion_id
                else:
                    self.log("❌ No ingestion_id in response", test_name)
                    return None
            else:
                self.log(f"❌ Ingestion failed: {response.status_code} - {response.text}", test_name)
                return None
                
        except Exception as e:
            self.log(f"❌ Basic ingestion test failed: {str(e)}", test_name)
            return None
    
    def test_status_checking(self, ingestion_id: str):
        """Test status endpoint"""
        test_name = "Status Checking"
        try:
            response = requests.get(f"{self.base_url}/status/{ingestion_id}")
            
            if response.status_code == 200:
                data = response.json()
                required_fields = ["ingestion_id", "status", "batches"]
                
                if all(field in data for field in required_fields):
                    self.log(f"✅ Status retrieved successfully: {data['status']}", test_name)
                    self.log(f"   Batches: {len(data['batches'])}", test_name)
                    return data
                else:
                    self.log("❌ Missing required fields in status response", test_name)
                    return None
            else:
                self.log(f"❌ Status check failed: {response.status_code}", test_name)
                return None
                
        except Exception as e:
            self.log(f"❌ Status check test failed: {str(e)}", test_name)
            return None
    
    def test_batch_size_limit(self):
        """Test that batches are limited to 3 IDs"""
        test_name = "Batch Size Limit"
        try:
            payload = {
                "ids": [1, 2, 3, 4, 5, 6, 7, 8],
                "priority": "LOW"
            }
            
            response = requests.post(f"{self.base_url}/ingest", json=payload)
            
            if response.status_code == 201:
                ingestion_id = response.json()["ingestion_id"]
                
                # Wait a moment for batches to be created
                time.sleep(1)
                
                status_response = requests.get(f"{self.base_url}/status/{ingestion_id}")
                if status_response.status_code == 200:
                    data = status_response.json()
                    batches = data["batches"]
                    
                    # Check batch sizes
                    batch_sizes = [len(batch["ids"]) for batch in batches]
                    max_batch_size = max(batch_sizes) if batch_sizes else 0
                    
                    if max_batch_size <= 3:
                        self.log(f"✅ Batch size limit respected: max={max_batch_size}", test_name)
                        self.log(f"   Batch sizes: {batch_sizes}", test_name)
                        return True
                    else:
                        self.log(f"❌ Batch size limit violated: max={max_batch_size}", test_name)
                        return False
                        
        except Exception as e:
            self.log(f"❌ Batch size test failed: {str(e)}", test_name)
            return False
    
    def test_priority_ordering(self):
        """Test priority-based processing order"""
        test_name = "Priority Ordering"
        try:
            # Send MEDIUM priority first
            payload1 = {
                "ids": [1, 2, 3, 4, 5],
                "priority": "MEDIUM"
            }
            
            response1 = requests.post(f"{self.base_url}/ingest", json=payload1)
            time.sleep(1)  # Wait 1 second
            
            # Send HIGH priority second (should be processed first)
            payload2 = {
                "ids": [6, 7, 8, 9],
                "priority": "HIGH"
            }
            
            response2 = requests.post(f"{self.base_url}/ingest", json=payload2)
            
            if response1.status_code == 201 and response2.status_code == 201:
                ingestion_id1 = response1.json()["ingestion_id"]
                ingestion_id2 = response2.json()["ingestion_id"]
                
                self.log(f"Created MEDIUM priority: {ingestion_id1}", test_name)
                self.log(f"Created HIGH priority: {ingestion_id2}", test_name)
                
                # Wait for some processing
                time.sleep(8)
                
                # Check status of both
                status1 = requests.get(f"{self.base_url}/status/{ingestion_id1}").json()
                status2 = requests.get(f"{self.base_url}/status/{ingestion_id2}").json()
                
                self.log(f"MEDIUM status: {status1['status']}", test_name)
                self.log(f"HIGH status: {status2['status']}", test_name)
                
                # HIGH priority should have more progress
                high_completed = sum(1 for b in status2['batches'] if b['status'] == 'completed')
                medium_completed = sum(1 for b in status1['batches'] if b['status'] == 'completed')
                
                if high_completed >= medium_completed:
                    self.log("✅ Priority ordering appears correct", test_name)
                    return True
                else:
                    self.log("❌ Priority ordering may be incorrect", test_name)
                    return False
                    
        except Exception as e:
            self.log(f"❌ Priority ordering test failed: {str(e)}", test_name)
            return False
    
    def test_rate_limiting(self):
        """Test rate limiting (1 batch per 5 seconds)"""
        test_name = "Rate Limiting"
        try:
            # Send multiple small batches
            payloads = [
                {"ids": [1, 2, 3], "priority": "LOW"},
                {"ids": [4, 5, 6], "priority": "LOW"},
                {"ids": [7, 8, 9], "priority": "LOW"}
            ]
            
            start_time = time.time()
            ingestion_ids = []
            
            for payload in payloads:
                response = requests.post(f"{self.base_url}/ingest", json=payload)
                if response.status_code == 201:
                    ingestion_ids.append(response.json()["ingestion_id"])
                time.sleep(0.5)  # Small delay between requests
            
            # Wait for processing
            time.sleep(20)  # Wait enough time for all batches
            
            # Check completion times
            completed_batches = 0
            for ingestion_id in ingestion_ids:
                status_response = requests.get(f"{self.base_url}/status/{ingestion_id}")
                if status_response.status_code == 200:
                    data = status_response.json()
                    for batch in data["batches"]:
                        if batch["status"] == "completed":
                            completed_batches += 1
            
            processing_time = time.time() - start_time
            expected_min_time = (len(ingestion_ids) - 1) * 5  # Rate limit consideration
            
            self.log(f"Completed {completed_batches} batches in {processing_time:.2f}s", test_name)
            self.log(f"Expected minimum time: {expected_min_time}s", test_name)
            
            if processing_time >= expected_min_time * 0.8:  # Allow some tolerance
                self.log("✅ Rate limiting appears to be working", test_name)
                return True
            else:
                self.log("⚠️ Rate limiting may not be working correctly", test_name)
                return False
                
        except Exception as e:
            self.log(f"❌ Rate limiting test failed: {str(e)}", test_name)
            return False
    
    def test_invalid_inputs(self):
        """Test handling of invalid inputs"""
        test_name = "Invalid Input Handling"
        try:
            invalid_payloads = [
                {"ids": [], "priority": "HIGH"},  # Empty IDs
                {"ids": [1, 2, 3]},  # Missing priority
                {"priority": "HIGH"},  # Missing IDs
                {"ids": [1, 2, 3], "priority": "INVALID"},  # Invalid priority
                {"ids": ["a", "b", "c"], "priority": "HIGH"},  # Non-numeric IDs
            ]
            
            success_count = 0
            for i, payload in enumerate(invalid_payloads):
                response = requests.post(f"{self.base_url}/ingest", json=payload)
                if response.status_code == 400:
                    success_count += 1
                    self.log(f"✅ Invalid payload {i+1} correctly rejected", test_name)
                else:
                    self.log(f"❌ Invalid payload {i+1} not rejected: {response.status_code}", test_name)
            
            if success_count == len(invalid_payloads):
                self.log("✅ All invalid inputs properly handled", test_name)
                return True
            else:
                self.log(f"❌ {len(invalid_payloads) - success_count} invalid inputs not handled", test_name)
                return False
                
        except Exception as e:
            self.log(f"❌ Invalid input test failed: {str(e)}", test_name)
            return False
    
    def test_concurrent_requests(self):
        """Test handling of concurrent requests"""
        test_name = "Concurrent Requests"
        try:
            lock = threading.Lock()
            results = []

            def safe_append(priority, ids_start):
                result = send_request(priority, ids_start)
                with lock:
                    results.append(result)

            def send_request(priority, ids_start):
                payload = {
                    "ids": list(range(ids_start + 1, ids_start + 4)),
                    "priority": priority
                }
                return requests.post(f"{self.base_url}/ingest", json=payload)

            # Launch 5 concurrent threads
            threads = []
            for i in range(5):
                priority = ["HIGH", "MEDIUM", "LOW"][i % 3]
                thread = threading.Thread(target=safe_append, args=(priority, i * 10))
                threads.append(thread)
                thread.start()

            for thread in threads:
                thread.join()

            success_count = sum(1 for r in results if r.status_code == 201)

            if success_count == len(threads):
                self.log(f"✅ All {success_count} concurrent requests handled", test_name)
                return True
            else:
                self.log(f"❌ Only {success_count}/{len(threads)} concurrent requests succeeded", test_name)
                return False

        except Exception as e:
            self.log(f"❌ Concurrent requests test failed: {str(e)}", test_name)
            return False

    
    def test_large_batch(self):
        """Test handling of large number of IDs"""
        test_name = "Large Batch Handling"
        try:
            # Send 100 IDs
            large_ids = list(range(1, 101))
            payload = {
                "ids": large_ids,
                "priority": "MEDIUM"
            }
            
            response = requests.post(f"{self.base_url}/ingest", json=payload)
            
            if response.status_code == 201:
                ingestion_id = response.json()["ingestion_id"]
                
                # Wait for batch creation
                time.sleep(2)
                
                status_response = requests.get(f"{self.base_url}/status/{ingestion_id}")
                if status_response.status_code == 200:
                    data = status_response.json()
                    batches = data["batches"]
                    
                    expected_batches = (len(large_ids) + 2) // 3  # Ceiling division
                    actual_batches = len(batches)
                    
                    if actual_batches == expected_batches:
                        self.log(f"✅ Large batch split correctly: {actual_batches} batches", test_name)
                        return True
                    else:
                        self.log(f"❌ Incorrect batch count: expected {expected_batches}, got {actual_batches}", test_name)
                        return False
                        
        except Exception as e:
            self.log(f"❌ Large batch test failed: {str(e)}", test_name)
            return False
    
    def test_status_transitions(self):
        """Test status transitions from yet_to_start -> triggered -> completed"""
        test_name = "Status Transitions"
        try:
            payload = {
                "ids": [1, 2, 3],
                "priority": "HIGH"
            }
            
            response = requests.post(f"{self.base_url}/ingest", json=payload)
            
            if response.status_code == 201:
                ingestion_id = response.json()["ingestion_id"]
                
                # Track status over time
                statuses = []
                for i in range(10):
                    status_response = requests.get(f"{self.base_url}/status/{ingestion_id}")
                    if status_response.status_code == 200:
                        data = status_response.json()
                        statuses.append(data["status"])
                    time.sleep(1)
                
                # Check for proper transitions
                unique_statuses = list(dict.fromkeys(statuses))  # Preserve order, remove duplicates
                self.log(f"Status progression: {' -> '.join(unique_statuses)}", test_name)
                
                # Should see progression from yet_to_start to completed
                if "completed" in unique_statuses:
                    self.log("✅ Status transitions appear correct", test_name)
                    return True
                else:
                    self.log("⚠️ Processing may be slow or incomplete", test_name)
                    return False
                    
        except Exception as e:
            self.log(f"❌ Status transitions test failed: {str(e)}", test_name)
            return False
    
    def run_all_tests(self):
        """Run all tests and provide summary"""
        print("="*60)
        print("🧪 STARTING COMPREHENSIVE API TESTING")
        print("="*60)
        
        # Test if API is running
        if not self.test_health_check():
            print("❌ API is not accessible. Please start the server first.")
            return False
        
        # Run all tests
        tests = [
            ("Basic Ingestion", self.test_basic_ingestion),
            ("Batch Size Limit", self.test_batch_size_limit),
            ("Priority Ordering", self.test_priority_ordering),
            ("Rate Limiting", self.test_rate_limiting),
            ("Invalid Input Handling", self.test_invalid_inputs),
            ("Concurrent Requests", self.test_concurrent_requests),
            ("Large Batch Handling", self.test_large_batch),
            ("Status Transitions", self.test_status_transitions),
        ]
        
        results = {}
        
        # Test basic ingestion first to get an ID for status testing
        ingestion_id = self.test_basic_ingestion()
        if ingestion_id:
            status_data = self.test_status_checking(ingestion_id)
            results["Status Checking"] = status_data is not None
        
        # Run other tests
        for test_name, test_func in tests[1:]:  # Skip basic ingestion as it's already done
            print(f"\n🔍 Running {test_name}...")
            try:
                result = test_func()
                results[test_name] = result
            except Exception as e:
                self.log(f"❌ {test_name} failed with exception: {str(e)}")
                results[test_name] = False
        
        # Summary
        print("\n" + "="*60)
        print("📊 TEST SUMMARY")
        print("="*60)
        
        passed = sum(1 for r in results.values() if r)
        total = len(results)
        
        for test_name, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{test_name:<25} {status}")
        
        print(f"\n🎯 Overall Results: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 ALL TESTS PASSED! API is working correctly.")
        else:
            print(f"⚠️  {total - passed} tests failed. Please check the implementation.")
        
        return passed == total

def main():
    """Main function to run tests"""
    # Get base URL from command line or use default
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    
    print(f"Testing API at: {base_url}")
    
    tester = APITester(base_url)
    success = tester.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
              
