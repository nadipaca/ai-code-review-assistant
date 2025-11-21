"""Debug script to check line counting"""
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

lines = original_code.split('\n')
for i, line in enumerate(lines, 1):
    print(f"{i:2d}: {line}")
