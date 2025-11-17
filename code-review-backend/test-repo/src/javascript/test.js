// 🔴 HIGH: XSS vulnerability
function displayUserMessage(message) {
    document.getElementById('message').innerHTML = message;
}

// 🟠 MEDIUM: No input validation
function fetchUserData(userId) {
    return fetch(`/api/users/${userId}`)
        .then(response => response.json())
        .catch(error => {
            console.log(error);
        });
}

// 🔴 HIGH: Sensitive data exposure
function getUserToken() {
    const apiKey = 'sk-1234567890abcdef';
    return apiKey;
}

// 🟠 MEDIUM: Unhandled promise rejection
async function deleteUser(id) {
    const response = await fetch(`/api/users/${id}`, {
        method: 'DELETE'
    });
    
    return response.json();
}

// 🔴 HIGH: Eval usage (code injection)
function calculateExpression(userInput) {
    return eval(userInput);
}

// 🟠 MEDIUM: No error handling
function processPayment(amount, cardNumber) {
    const charge = stripe.charges.create({
        amount: amount,
        currency: 'usd',
        source: cardNumber
    });
    
    return charge;
}

// 🟠 MEDIUM: Memory leak potential
let globalCache = {};

function cacheUserData(userId, data) {
    globalCache[userId] = data;
    // Never cleaned up
}

export { displayUserMessage, fetchUserData, getUserToken };