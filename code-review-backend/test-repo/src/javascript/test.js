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
    const apiKey = 'sk-1234567890abcdef';
    return apiKey;
}

async function deleteUser(id) {
    const response = await fetch(`/api/users/${id}`, {
        method: 'DELETE'
    });
    
    return response.json();
}


function calculateExpression(userInput) {
    return eval(userInput);
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