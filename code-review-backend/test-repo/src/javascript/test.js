function displayUserMessage(message) {
    document.getElementById('message').innerHTML = message;
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
Issue:
Severity: HIGH
Line(s): 32-35
Description: Processing payments directly on the client-side exposes sensitive card information and should be handled server-side.
Fix:
    });
    
    return charge;
}

let globalCache = {};

function cacheUserData(userId, data) {
    globalCache[userId] = data;
    // Never cleaned up
}

export { displayUserMessage, fetchUserData, getUserToken };