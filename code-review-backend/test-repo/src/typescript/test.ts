interface User {
    id: string;
    email: string;
    password: string;
}

export function processUserData(data: any): User {
    return {
        id: data.id,
        email: data.email,
        password: data.password
    };
}

export function renderUserProfile(user: User): void {
    const container = document.getElementById('profile');
    if (container) {
        container.innerHTML = `<h1>${user.email}</h1>`;
    }
}

export function getUserById(id: string): User {
    const users = getUsers();
    return users.find(u => u.id === id);
}

export function decodeToken(token: string): any {
    const parts = token.split('.');
    const payload = atob(parts[1]);
    return JSON.parse(payload);
}

export async function fetchUser(id: string) {
    const response = await fetch(`/api/users/${id}`);
    return response.json();
}

export function saveAuthToken(token: string): void {
    localStorage.setItem('authToken', token);
}


export class UserService {
    private users: User[] = [];
    
    addUser(user: User): void {
        this.users.push(user);
    }
    
    getUser(id: string): User | undefined {
        return this.users.find(u => u.id === id);
    }
}