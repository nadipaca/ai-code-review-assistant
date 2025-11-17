package com.example.service;

import java.sql.Connection;
import java.sql.Statement;
import java.sql.ResultSet;
import javax.servlet.http.HttpServletRequest;

public class UserService {
    private Connection db;

    // 🔴 HIGH: SQL Injection vulnerability
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

    // 🟠 MEDIUM: Unvalidated user input
    public boolean deleteUser(HttpServletRequest request) {
        String userId = request.getParameter("userId");

        try {
            Statement stmt = db.createStatement();
            stmt.executeUpdate("DELETE FROM users WHERE id = " + userId);
            return true;
        } catch (Exception e) {
            return false;
        }
    }

    // 🔴 HIGH: Hardcoded credentials
    public void connectToDatabase() {
        String password = "admin123";
        String url = "jdbc:mysql://localhost:3306/mydb";
        // Database connection logic
    }

    // 🟠 MEDIUM: Race condition
    private static int counter = 0;

    public void incrementCounter() {
        counter++;
    }
}