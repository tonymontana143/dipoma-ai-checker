"""
Test suite for ToxicShield API

Run this after starting the API server:
    python app.py
    
Then in another terminal:
    python test_api.py
"""

import requests
import json
import time
from typing import List, Tuple

# Configuration
API_URL = "https://dipoma-ai-checker.onrender.com/api/check"
TIMEOUT = 10  # seconds

# ANSI Colors for output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def print_header(text: str):
    """Print a formatted header"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text.center(60)}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}\n")


def print_success(text: str):
    """Print success message"""
    print(f"{Colors.OKGREEN}✅ {text}{Colors.ENDC}")


def print_error(text: str):
    """Print error message"""
    print(f"{Colors.FAIL}❌ {text}{Colors.ENDC}")


def print_info(text: str):
    """Print info message"""
    print(f"{Colors.OKCYAN}ℹ️  {text}{Colors.ENDC}")


def print_warning(text: str):
    """Print warning message"""
    print(f"{Colors.WARNING}⚠️  {text}{Colors.ENDC}")


def check_api_alive():
    """Check if API is running"""
    try:
        response = requests.get(f"{API_URL}/", timeout=TIMEOUT)
        if response.status_code == 200:
            print_success(f"API is running at {API_URL}")
            data = response.json()
            print_info(f"API Version: {data.get('version', 'Unknown')}")
            return True
    except requests.exceptions.ConnectionError:
        print_error(f"Cannot connect to API at {API_URL}")
        print_warning("Make sure to start the server first: python app.py")
        return False
    except Exception as e:
        print_error(f"Error checking API: {e}")
        return False


def test_health_check():
    """Test the health check endpoint"""
    print_info("Testing /health endpoint...")
    try:
        response = requests.get(f"{API_URL}/health", timeout=TIMEOUT)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data["status"] == "ok", "Status should be 'ok'"
        assert "model" in data, "Response should contain 'model'"
        assert "device" in data, "Response should contain 'device'"
        
        print_success(f"Health check passed")
        print_info(f"  Status: {data['status']}")
        print_info(f"  Model: {data['model']}")
        print_info(f"  Device: {data['device']}")
        return True
    except AssertionError as e:
        print_error(f"Assertion failed: {e}")
        return False
    except Exception as e:
        print_error(f"Health check failed: {e}")
        return False


def test_toxic_comments():
    """Test detection of toxic comments"""
    print_info("Testing toxic comment detection...")
    
    toxic_examples = [
        ("You are stupid idiot!", "English insult"),
        ("Ты идиот!", "Russian insult"),
        ("Сен ақымақсың!", "Kazakh insult"),
        ("I hate you so much", "English hate speech"),
        ("You suck", "English negative comment"),
    ]
    
    results = []
    for text, description in toxic_examples:
        try:
            response = requests.post(
                f"{API_URL}/api/check",
                json={"text": text, "threshold": 0.15},
                timeout=TIMEOUT
            )
            
            assert response.status_code == 200, f"Expected 200, got {response.status_code}"
            data = response.json()
            
            assert "is_toxic" in data, "Response should contain 'is_toxic'"
            assert "toxicity_score" in data, "Response should contain 'toxicity_score'"
            assert "model_used" in data, "Response should contain 'model_used'"
            
            status = "✓" if data["is_toxic"] else "✗"
            results.append((status, text, data["is_toxic"], data["toxicity_score"]))
            
            print_info(f"{status} [{description}] '{text}'")
            print(f"    └─ Toxic: {data['is_toxic']}, Score: {data['toxicity_score']:.2%}")
            
        except Exception as e:
            print_error(f"Error testing '{text}': {e}")
            results.append(("E", text, None, None))
    
    return results


def test_normal_comments():
    """Test detection of normal comments"""
    print_info("Testing normal comment detection...")
    
    normal_examples = [
        ("Thank you! Great article!", "English gratitude"),
        ("Рахмет! Өте жақсы мақала!", "Kazakh gratitude"),
        ("Спасибо, интересно!", "Russian gratitude"),
        ("I completely agree", "English agreement"),
        ("This is helpful information", "English feedback"),
    ]
    
    results = []
    for text, description in normal_examples:
        try:
            response = requests.post(
                f"{API_URL}/api/check",
                json={"text": text, "threshold": 0.15},
                timeout=TIMEOUT
            )
            
            assert response.status_code == 200
            data = response.json()
            
            assert "is_toxic" in data, "Response should contain 'is_toxic'"
            
            status = "✓" if not data["is_toxic"] else "✗"
            results.append((status, text, not data["is_toxic"], data["toxicity_score"]))
            
            print_info(f"{status} [{description}] '{text}'")
            print(f"    └─ Toxic: {data['is_toxic']}, Score: {data['toxicity_score']:.2%}")
            
        except Exception as e:
            print_error(f"Error testing '{text}': {e}")
            results.append(("E", text, None, None))
    
    return results


def test_threshold_behavior():
    """Test different threshold values"""
    print_info("Testing threshold behavior...")
    
    test_text = "You are bad"
    thresholds = [0.1, 0.3, 0.5, 0.7, 0.9]
    
    print_info(f"Testing with text: '{test_text}'")
    print()
    
    results = []
    for threshold in thresholds:
        try:
            response = requests.post(
                f"{API_URL}/api/check",
                json={"text": test_text, "threshold": threshold},
                timeout=TIMEOUT
            )
            
            assert response.status_code == 200
            data = response.json()
            
            toxicity = data["toxicity_score"]
            is_toxic = data["is_toxic"]
            expected = toxicity > threshold
            
            status = "✓" if is_toxic == expected else "✗"
            results.append((status, threshold, is_toxic, toxicity))
            
            print_info(f"{status} Threshold: {threshold:.1f}, "
                      f"Score: {toxicity:.2%}, Is Toxic: {is_toxic}")
            
        except Exception as e:
            print_error(f"Error with threshold {threshold}: {e}")
            results.append(("E", threshold, None, None))
    
    return results


def test_edge_cases():
    """Test edge cases"""
    print_info("Testing edge cases...")
    
    test_cases = [
        ("a", "Very short text", 200),
        ("word " * 200, "Very long text", 200),  # 1000 chars
        ("", "Empty text", 400),  # Should fail validation
        ("normal comment", "Threshold 0.0", 200),
        ("normal comment", "Threshold 1.0", 200),
    ]
    
    for text, description, expected_status in test_cases:
        try:
            # Skip validation tests with threshold edge cases
            threshold = 0.0 if "Threshold 0.0" in description else (1.0 if "Threshold 1.0" in description else 0.5)
            
            response = requests.post(
                f"{API_URL}/api/check",
                json={"text": text, "threshold": threshold},
                timeout=TIMEOUT
            )
            
            if response.status_code == expected_status:
                print_success(f"{description}: Got expected {expected_status}")
            else:
                print_warning(f"{description}: Expected {expected_status}, got {response.status_code}")
            
        except Exception as e:
            if expected_status == 400:
                print_success(f"{description}: Correctly rejected - {e}")
            else:
                print_error(f"Error testing {description}: {e}")


def test_multilingual():
    """Test multilingual support"""
    print_info("Testing multilingual support...")
    
    multilingual_tests = [
        ("Chinese: 你太愚蠢了", "Chinese insult"),
        ("Arabic: أنت غبي جداً", "Arabic insult"),
        ("Spanish: ¡Eres un idiota!", "Spanish insult"),
        ("German: Du bist dumm!", "German insult"),
        ("French: Tu es stupide!", "French insult"),
        ("Turkish: Sen aptal bir insansın!", "Turkish insult"),
        ("Polish: Jesteś głupi!", "Polish insult"),
    ]
    
    for text, description in multilingual_tests:
        try:
            response = requests.post(
                f"{API_URL}/api/check",
                json={"text": text, "threshold": 0.15},
                timeout=TIMEOUT
            )
            
            if response.status_code == 200:
                data = response.json()
                print_info(f"{description}")
                print(f"    └─ Toxic: {data['is_toxic']}, Score: {data['toxicity_score']:.2%}")
            else:
                print_error(f"{description}: Got status {response.status_code}")
        except Exception as e:
            print_error(f"{description}: {e}")


def test_performance():
    """Test API performance"""
    print_info("Testing API performance...")
    
    test_text = "This is a test comment for performance measurement"
    num_requests = 10
    
    print_info(f"Sending {num_requests} requests...")
    
    times = []
    for i in range(num_requests):
        try:
            start_time = time.time()
            response = requests.post(
                f"{API_URL}/api/check",
                json={"text": test_text, "threshold": 0.15},
                timeout=TIMEOUT
            )
            elapsed = (time.time() - start_time) * 1000  # Convert to ms
            
            if response.status_code == 200:
                times.append(elapsed)
        except Exception as e:
            print_error(f"Request {i+1} failed: {e}")
    
    if times:
        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)
        
        print_success(f"Performance metrics ({len(times)} requests):")
        print(f"    ├─ Average: {avg_time:.2f}ms")
        print(f"    ├─ Min: {min_time:.2f}ms")
        print(f"    ├─ Max: {max_time:.2f}ms")
        print(f"    └─ RPS: {1000 / avg_time:.1f} requests/sec")
    else:
        print_error("No successful requests to measure performance")


def run_all_tests():
    """Run all tests"""
    print_header("🧪 ToxicShield API Test Suite")
    
    # Check API availability
    if not check_api_alive():
        return False
    
    # Run tests
    all_passed = True
    
    print_header("1️⃣  Health Check")
    if not test_health_check():
        all_passed = False
    
    print_header("2️⃣  Toxic Comments Detection")
    test_toxic_comments()
    
    print_header("3️⃣  Normal Comments Detection")
    test_normal_comments()
    
    print_header("4️⃣  Threshold Behavior")
    test_threshold_behavior()
    
    print_header("5️⃣  Edge Cases")
    test_edge_cases()
    
    print_header("6️⃣  Multilingual Support")
    test_multilingual()
    
    print_header("7️⃣  Performance Metrics")
    test_performance()
    
    # Summary
    print_header("✅ Test Suite Complete")
    
    if all_passed:
        print_success("All critical tests passed!")
    else:
        print_warning("Some tests had issues - see details above")
    
    print_info("View interactive API docs at: http://localhost:8000/docs")
    print()


if __name__ == "__main__":
    try:
        run_all_tests()
    except KeyboardInterrupt:
        print("\n\n" + Colors.WARNING + "Tests interrupted by user" + Colors.ENDC)
    except Exception as e:
        print("\n" + Colors.FAIL + f"Unexpected error: {e}" + Colors.ENDC)
