"""
Test cases for intelligent code block range detection in CodeApplier.

This tests the ability to detect complete function/class blocks when
the AI suggestion identifies an issue in a subset of lines but the fix
requires replacing the entire block.
"""
import pytest
from app.services.code_applier import CodeApplier


class TestCodeBlockRangeDetection:
    """Test intelligent line range detection for code fixes"""
    
    def test_javascript_function_expansion(self):
        """Test: JavaScript function - Issue at lines 32-35, fix contains full function"""
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
        
        # Fix code contains the complete function
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
        # But the fix should replace lines 5-21 (the entire function)
        start, end = CodeApplier.detect_code_block_range(
            original_code=original_code,
            fix_code=fix_code,
            suggested_start=6,
            suggested_end=10,
            file_path="test.js"
        )
        
        # Should detect the complete function from line 5 to 21
        assert start == 5, f"Expected start=5, got {start}"
        assert end == 21, f"Expected end=21, got {end}"
    
    def test_python_function_expansion(self):
        """Test: Python function - Issue inside function, fix replaces complete function"""
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
        
        # AI suggests line 4 (the SQL injection line)
        # But fix should replace lines 3-6 (the entire function)
        start, end = CodeApplier.detect_code_block_range(
            original_code=original_code,
            fix_code=fix_code,
            suggested_start=4,
            suggested_end=4,
            file_path="test.py"
        )
        
        assert start == 3, f"Expected start=3, got {start}"
        assert end == 6, f"Expected end=6, got {end}"
    
    def test_java_method_expansion(self):
        """Test: Java method - Issue in method body, fix replaces entire method"""
        original_code = """public class UserService {
    private Connection db;

    public User getUserByEmail(String email) {
        try {
            Statement stmt = db.createStatement();
            String query = "SELECT * FROM users WHERE email = '" + email + "'";
            ResultSet rs = stmt.executeQuery(query);

            if (rs.next()) {
                return new User(rs.getString("id"), rs.getString("name"));
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
        return null;
    }
}"""
        
        fix_code = """public User getUserByEmail(String email) {
        try {
            PreparedStatement stmt = db.prepareStatement("SELECT * FROM users WHERE email = ?");
            stmt.setString(1, email);
            ResultSet rs = stmt.executeQuery();

            if (rs.next()) {
                return new User(rs.getString("id"), rs.getString("name"));
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
        return null;
    }"""
        
        # AI suggests line 7 (SQL injection)
        # But fix should replace lines 4-17 (entire method)
        start, end = CodeApplier.detect_code_block_range(
            original_code=original_code,
            fix_code=fix_code,
            suggested_start=7,
            suggested_end=7,
            file_path="UserService.java"
        )
        
        assert start == 4, f"Expected start=4, got {start}"
        assert end == 17, f"Expected end=17, got {end}"
    
    def test_no_expansion_for_simple_replacement(self):
        """Test: Simple replacement - No function definition, no expansion"""
        original_code = """const API_KEY = "12345-secret-key";
const BASE_URL = "https://api.example.com";

function fetchData() {
    return fetch(BASE_URL);
}"""
        
        # Fix is just a simple line replacement, not a function
        fix_code = """const API_KEY = process.env.API_KEY;"""
        
        start, end = CodeApplier.detect_code_block_range(
            original_code=original_code,
            fix_code=fix_code,
            suggested_start=1,
            suggested_end=1,
            file_path="config.js"
        )
        
        # Should not expand, return original range
        assert start == 1
        assert end == 1
    
    def test_fallback_on_detection_failure(self):
        """Test: Complex code where detection fails - Use original range"""
        original_code = """const obj = {
    method1() { return 1; },
    method2() { return 2; }
};"""
        
        # Fix code that might be hard to detect
        fix_code = """method1() { return Math.random(); }"""
        
        start, end = CodeApplier.detect_code_block_range(
            original_code=original_code,
            fix_code=fix_code,
            suggested_start=2,
            suggested_end=2,
            file_path="test.js"
        )
        
        # Should fall back to original range
        assert start == 2
        assert end == 2


class TestSmartApplySuggestion:
    """Test the complete smart_apply_suggestion flow with range detection"""
    
    def test_apply_with_auto_range_detection(self):
        """Test: Applying a fix with automatic range detection"""
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
        
        # AI suggestion identifies eval() issue at line 4
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
        
        assert result["applied"] is True
        assert result["error"] is None
        
        # Verify the entire function was replaced, not just line 4
        modified = result["modified_code"]
        assert "function calculateTotal(items)" in modified
        assert "parseFloat(items[i].price)" in modified
        assert "eval" not in modified
        
        # Verify it didn't break the next function
        assert "function processOrder()" in modified
