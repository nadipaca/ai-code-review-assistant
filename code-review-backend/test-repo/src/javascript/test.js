function displayUserMessage(message) {
    document.getElementById('message').textContent = message;
}

function fetchUserData(userId) {
    return fetch(`/api/users/${userId}`)
        .then(response => response.json())
        .catch(error => {
            console.log(error);
        });
}

function getUserToken() {
    const apiKey = process.env.API_KEY;
    return apiKey;
}

async function deleteUser(id) {
    const response = await fetch(`/api/users/${id}`, {
        method: 'DELETE'
    });
    
    return response.json();
}


function calculateExpression(userInput) {
    // Remove this function - it's inherently unsafe.
    // If you need math evaluation, use a library like 'expr-eval':
    // const Parser = require('expr-eval').Parser;
    // const parser = new Parser();
    // return parser.evaluate(userInput);
    throw new Error('This function has been removed for security reasons. Use a safe expression parser.');
}

function processPayment(amount, cardNumber) {
    const charge = stripe.charges.create({
        amount: amount,
        currency: 'usd',
        source: cardNumber
    });
    
    return charge;
}

let globalCache = {};

function cacheUserData(userId, data) {
    globalCache[userId] = data;
    // Never cleaned up
}

export { displayUserMessage, fetchUserData, getUserToken };