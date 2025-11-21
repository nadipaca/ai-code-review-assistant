"""
Simple standalone test for code block range detection.
Run with: python3 test_range_detection_simple.py
"""
import sys
import os

# Add app directory to path
sys.path.insert(0, os.path.dirname(__file__))

from app.services.code_applier import CodeApplier


def test_javascript_function_expansion():
    """Test: JavaScript function - Issue at lines 6-10, fix contains full function"""
    print("\n=== Test 1: JavaScript Function Expansion ===")
    
    original_code = """function getUserData(userId) {
    return fetch('/api/users/' + userId);
}

function processPayment(amount, cardNumber) {
    const charge = stripe.charges.create({
        amount: amount,
        currency: 'usd',
        source: cardNumber
    });
    async function processPayment(amount, cardNumber) {
        const response = await fetch('/api/process-payment', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ amount, cardNumber })
        });
        return response.json();
    }
    return charge;
}

let globalCache = {};"""
    
    fix_code = """async function processPayment(amount, cardNumber) {
    const response = await fetch('/api/process-payment', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ amount, cardNumber })
    });
    return response.json();
}"""
    
    # AI suggests lines 6-10 (the problematic part)
    # Should detect lines 5-22 (the entire function)
    start, end = CodeApplier.detect_code_block_range(
        original_code=original_code,
        fix_code=fix_code,
        suggested_start=6,
        suggested_end=10,
        file_path="test.js"
    )
    
    print(f"Suggested range: 6-10")
    print(f"Detected range: {start}-{end}")
    
    if start == 5 and end == 22:
        print("✅ PASSED: Correctly detected full function range (5-22)")
        return True
    else:
        print(f"❌ FAILED: Expected 5-22, got {start}-{end}")
        return False


def test_python_function_expansion():
    """Test: Python function - Issue inside function, fix replaces complete function"""
    print("\n=== Test 2: Python Function Expansion ===")
    
    original_code = """import os

def get_user_by_email(email):
    query = "SELECT * FROM users WHERE email = '" + email + "'"
    result = db.execute(query)
    return result

def process_data():
    pass"""
    
    fix_code = """def get_user_by_email(email):
    query = "SELECT * FROM users WHERE email = ?"
    result = db.execute(query, [email])
    return result"""
    
    # AI suggests line 4 (SQL injection)
    # Should detect lines 3-6 (entire function)
    start, end = CodeApplier.detect_code_block_range(
        original_code=original_code,
        fix_code=fix_code,
        suggested_start=4,
        suggested_end=4,
        file_path="test.py"
    )
    
    print(f"Suggested range: 4-4")
    print(f"Detected range: {start}-{end}")
    
    if start == 3 and end == 6:
        print("✅ PASSED: Correctly detected full function range (3-6)")
        return True
    else:
        print(f"❌ FAILED: Expected 3-6, got {start}-{end}")
        return False


def test_no_expansion_simple_replacement():
    """Test: Simple replacement - No function definition, no expansion"""
    print("\n=== Test 3: No Expansion for Simple Replacement ===")
    
    original_code = """const API_KEY = "12345-secret-key";
const BASE_URL = "https://api.example.com";

function fetchData() {
    return fetch(BASE_URL);
}"""
    
    fix_code = """const API_KEY = process.env.API_KEY;"""
    
    start, end = CodeApplier.detect_code_block_range(
        original_code=original_code,
        fix_code=fix_code,
        suggested_start=1,
        suggested_end=1,
        file_path="config.js"
    )
    
    print(f"Suggested range: 1-1")
    print(f"Detected range: {start}-{end}")
    
    if start == 1 and end == 1:
        print("✅ PASSED: No expansion for simple replacement")
        return True
    else:
        print(f"❌ FAILED: Expected 1-1, got {start}-{end}")
        return False


def test_complete_apply_suggestion():
    """Test: Complete flow with smart_apply_suggestion"""
    print("\n=== Test 4: Complete Apply Suggestion Flow ===")
    
    original_code = """function calculateTotal(items) {
    let total = 0;
    for (let i = 0; i < items.length; i++) {
        total += eval(items[i].price);
    }
    return total;
}

function processOrder() {
    // other code
}"""
    
    suggestion = """Code:
```javascript
total += eval(items[i].price);
```
Issue:
Severity: HIGH
Line(s): 4
Description: eval() executes arbitrary code, allowing code injection attacks.

Fix:
```javascript
function calculateTotal(items) {
    let total = 0;
    for (let i = 0; i < items.length; i++) {
        total += parseFloat(items[i].price);
    }
    return total;
}
```
This uses parseFloat() which safely parses numbers without executing code."""
    
    result = CodeApplier.smart_apply_suggestion(
        original_code=original_code,
        suggestion=suggestion,
        line_start=4,
        line_end=4,
        file_path="cart.js"
    )
    
    print(f"Applied: {result['applied']}")
    print(f"Error: {result['error']}")
    
    if result["applied"] and result["error"] is None:
        modified = result["modified_code"]
        
        # Check that the fix was applied
        has_parseFloat = "parseFloat(items[i].price)" in modified
        no_eval = "eval" not in modified
        has_next_function = "function processOrder()" in modified
        
        print(f"Has parseFloat: {has_parseFloat}")
        print(f"No eval: {no_eval}")
        print(f"Preserved next function: {has_next_function}")
        
        if has_parseFloat and no_eval and has_next_function:
            print("✅ PASSED: Fix applied correctly with range detection")
            return True
        else:
            print("❌ FAILED: Fix not applied correctly")
            print("Modified code preview:")
            print(modified[:200])
            return False
    else:
        print(f"❌ FAILED: Could not apply suggestion - {result.get('error')}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("Code Block Range Detection Tests")
    print("=" * 60)
    
    results = []
    
    results.append(test_javascript_function_expansion())
    results.append(test_python_function_expansion())
    results.append(test_no_expansion_simple_replacement())
    results.append(test_complete_apply_suggestion())
    
    print("\n" + "=" * 60)
    print(f"Results: {sum(results)}/{len(results)} tests passed")
    print("=" * 60)
    
    if all(results):
        print("✅ All tests passed!")
        sys.exit(0)
    else:
        print("❌ Some tests failed")
        sys.exit(1)
