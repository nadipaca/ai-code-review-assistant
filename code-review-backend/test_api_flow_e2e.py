"""
End-to-end test simulating the exact API flow from the screenshot.
This tests the REAL scenario where the frontend sends apply-suggestion request.
"""
import sys
import os

# Add app directory to path
sys.path.insert(0, os.path.dirname(__file__))

from app.services.code_applier import CodeApplier


def test_real_api_flow_with_diff():
    """
    Simulate the REAL API flow from the screenshot.
    
    The screenshot shows:
    - Severity: HIGH, Line(s): 32-35
    - Issue: Processing payments directly on client-side
    - Fix: Entire async function processPayment
    """
    print("\n" + "="*70)
    print("🔍 REAL API FLOW TEST - Strategy 1 (with diff)")
    print("="*70)
    
    # Original code from the screenshot
    original_code = """function getUserData(userId) {
    return fetch('/api/users/' + userId);
}

// ... other functions ...

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

    # AI suggestion from screenshot
    suggestion = """Code:
```javascript
const charge = stripe.charges.create({
    amount: amount,
    currency: 'usd',
    source: cardNumber
});
```
Issue:
Severity: HIGH
Line(s): 32-35
Description: Processing payments directly on the client-side exposes sensitive payment information and should be handled server-side to ensure security and compliance with PCI DSS.

Fix:
```javascript
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
```
This moves the payment processing to a server-side endpoint, keeping sensitive data secure."""

    # The API currently receives line_start=8 and line_end=11 (lines 32-35 adjusted)
    # Let's say in this file they map to lines 8-11
    line_start = 8
    line_end = 11
    
    print(f"\n📥 API Request:")
    print(f"   - line_start: {line_start}")
    print(f"   - line_end: {line_end}")
    print(f"   - suggestion: (Contains fix code block)")
    
    # Test Strategy 2: smart_apply_suggestion (OUR FIX)
    print(f"\n🧪 Testing Strategy 2 (CodeApplier.smart_apply_suggestion)...")
    result = CodeApplier.smart_apply_suggestion(
        original_code=original_code,
        suggestion=suggestion,
        line_start=line_start,
        line_end=line_end,
        file_path="test.js"
    )
    
    print(f"\n📊 Results:")
    print(f"   - Applied: {result['applied']}")
    print(f"   - Error: {result['error']}")
    
    if result['applied'] and result['changes']:
        change = result['changes'][0]
        detected_range = change['lines']
        print(f"   - Original range: {line_start}-{line_end}")
        print(f"   - Detected range: {detected_range[0]}-{detected_range[1]}")
        
        # Check if range was expanded
        if detected_range[0] < line_start or detected_range[1] > line_end:
            print(f"   ✅ Range was expanded (detected complete function)")
        else:
            print(f"   ❌ Range was NOT expanded")
        
        # Check the modified code
        modified = result['modified_code']
        print(f"\n📝 Modified code contains:")
        print(f"   - 'async function processPayment': {'✅' if 'async function processPayment' in modified else '❌'}")
        print(f"   - 'stripe.charges.create': {'❌ (good)' if 'stripe.charges.create' not in modified else '✅ (bad - should be removed)'}")
        print(f"   - 'fetch(\\'/ api/process-payment': {'✅' if '/api/process-payment' in modified else '❌'}")
        
        # Final verdict
        has_async = 'async function processPayment' in modified
        no_stripe = 'stripe.charges.create' not in modified
        has_fetch = '/api/process-payment' in modified
        range_expanded = detected_range[0] < line_start or detected_range[1] > line_end
        
        if has_async and no_stripe and has_fetch and range_expanded:
            print(f"\n✅ STRATEGY 2 (smart_apply_suggestion): PASSED")
            print(f"   The fix correctly replaced the entire function!")
            return True
        else:
            print(f"\n❌ STRATEGY 2 (smart_apply_suggestion): FAILED")
            print(f"   - has_async: {has_async}")
            print(f"   - no_stripe: {no_stripe}")
            print(f"   - has_fetch: {has_fetch}")
            print(f"   - range_expanded: {range_expanded}")
            return False
    else:
        print(f"❌ FAILED: Could not apply suggestion")
        return False


def test_api_strategy1_current_behavior():
    """
    Test the CURRENT API behavior (Strategy 1 - uses diff and exact line numbers).
    This is what's ACTUALLY running in production and has the bug.
    """
    print("\n" + "="*70)
    print("🔍 CURRENT API BEHAVIOR TEST - Strategy 1 (uses line_start/line_end)")
    print("="*70)
    
    original_code = """function getUserData(userId) {
    return fetch('/api/users/' + userId);
}

// ... other functions ...

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
    
    # Simulating Strategy 1 behavior (lines 382-388 in reviews.py)
    # It uses the EXACT line_start and line_end without intelligent detection
    line_start = 8
    line_end = 11
    
    # Fixed code from the Fix section
    fixed_lines = [
        "async function processPayment(amount, cardNumber) {",
        "    const response = await fetch('/api/process-payment', {",
        "        method: 'POST',",
        "        headers: {",
        "            'Content-Type': 'application/json'",
        "        },",
        "        body: JSON.stringify({ amount, cardNumber })",
        "    });",
        "    return response.json();",
        "}"
    ]
    
    print(f"\n📥 Current API Strategy 1:")
    print(f"   - Replaces lines: {line_start}-{line_end}")
    print(f"   - With fixed_lines: {len(fixed_lines)} lines")
    
    # Simulate the current API behavior
    base_lines = original_code.split('\n')
    start_idx = max(0, line_start - 1)
    end_idx = min(len(base_lines), line_end)
    
    new_lines = base_lines[:start_idx] + fixed_lines + base_lines[end_idx:]
    modified_code = '\n'.join(new_lines)
    
    print(f"\n📝 Modified code (first 12 lines):")
    for i, line in enumerate(modified_code.split('\n')[:15], 1):
        print(f"   {i:2d}: {line}")
    
    # Check for syntax errors
    print(f"\n🔍 Checking for syntax issues:")
    
    # Count function definitions
    func_defs = modified_code.count('function processPayment')
    print(f"   - function processPayment definitions: {func_defs}")
    
    # Check if there are nested or broken functions
    if 'async function processPayment' in modified_code and 'stripe.charges.create' in modified_code:
        print(f"   ❌ BROKEN: Both old and new code exist (partial replacement)")
        print(f"   This is the BUG - only lines 8-11 were replaced, but the function continues to line 23!")
        return False
    else:
        print(f"   ✅ Clean replacement")
        return True


if __name__ == "__main__":
    print("\n" + "="*70)
    print("END-TO-END VERIFICATION: Real API Flow")
    print("="*70)
    
    # Test current API behavior (Strategy 1 - has the bug)
    strategy1_works = test_api_strategy1_current_behavior()
    
    # Test our fix (Strategy 2 - should work)
    strategy2_works = test_real_api_flow_with_diff()
    
    print("\n" + "="*70)
    print("FINAL RESULTS:")
    print("="*70)
    print(f"Strategy 1 (current API with exact line numbers): {'✅ PASS' if strategy1_works else '❌ FAIL (has the bug)'}")
    print(f"Strategy 2 (smart_apply_suggestion with range detection): {'✅ PASS' if strategy2_works else '❌ FAIL'}")
    
    if not strategy1_works and strategy2_works:
        print(f"\n⚠️  CONCLUSION: Strategy 1 (current API default) is BROKEN")
        print(f"   The API needs to use Strategy 2 OR add range detection to Strategy 1")
        print(f"\n💡 SOLUTION: The API endpoint should call detect_code_block_range")
        print(f"   before applying the fix in lines 382-388 of reviews.py")
    
    sys.exit(0 if (strategy1_works or strategy2_works) else 1)
