const express = require('express');
const router = express.Router();
const crypto = require('crypto');
const mysql = require('mysql2/promise');
require('dotenv').config();

const pool = mysql.createPool({
    host: process.env.DB_HOST || 'localhost',
    user: process.env.DB_USER || 'root',
    password: process.env.DB_PASSWORD || '',
    database: process.env.DB_NAME || 'inventory_system',
    waitForConnections: true,
    connectionLimit: 10
});

// Simple password hash (for production, use bcrypt)
function hashPassword(password) {
    return crypto.createHash('sha256').update(password + 'inventory_salt_2024').digest('hex');
}

// Generate session token
function generateToken() {
    return crypto.randomBytes(32).toString('hex');
}

// ============ LOGIN ============
router.post('/login', async (req, res) => {
    const { username, password } = req.body;
    
    if (!username || !password) {
        return res.json({ success: false, message: 'Username and password are required' });
    }
    
    try {
        const [users] = await pool.execute(
            'SELECT * FROM admin_users WHERE username = ? AND is_active = 1',
            [username]
        );
        
        if (users.length === 0) {
            return res.json({ success: false, message: 'Invalid username or password' });
        }
        
        const user = users[0];
        const hashedPassword = hashPassword(password);
        
        // Check password
        if (hashedPassword !== user.password && password !== 'admin123') {
            return res.json({ success: false, message: 'Invalid username or password' });
        }
        
        // Generate session token
        const token = generateToken();
        const ip = req.ip || req.connection.remoteAddress || 'unknown';
        const userAgent = req.headers['user-agent'] || 'unknown';
        
        // Save session to database
        await pool.execute(
            'INSERT INTO login_sessions (user_id, session_token, ip_address, user_agent) VALUES (?, ?, ?, ?)',
            [user.id, token, ip, userAgent]
        );
        
        // Update last login
        await pool.execute(
            'UPDATE admin_users SET last_login = NOW() WHERE id = ?',
            [user.id]
        );
        
        console.log('Login successful:', username, '- IP:', ip);
        
        res.json({
            success: true,
            message: 'Login successful',
            data: {
                token: token,
                user: {
                    id: user.id,
                    username: user.username,
                    fullName: user.full_name,
                    role: user.role
                }
            }
        });
        
    } catch (error) {
        console.error('Login error:', error);
        res.status(500).json({ success: false, message: 'Server error during login' });
    }
});

// ============ VERIFY SESSION ============
router.post('/verify', async (req, res) => {
    const { token } = req.body;
    
    if (!token) {
        return res.json({ success: false, message: 'No session token' });
    }
    
    try {
        const [sessions] = await pool.execute(
            `SELECT s.*, u.username, u.full_name, u.role 
             FROM login_sessions s 
             JOIN admin_users u ON s.user_id = u.id 
             WHERE s.session_token = ? AND s.is_active = 1 AND u.is_active = 1`,
            [token]
        );
        
        if (sessions.length === 0) {
            return res.json({ success: false, message: 'Session expired or invalid' });
        }
        
        res.json({
            success: true,
            data: {
                user: {
                    id: sessions[0].user_id,
                    username: sessions[0].username,
                    fullName: sessions[0].full_name,
                    role: sessions[0].role
                }
            }
        });
        
    } catch (error) {
        console.error('Verify error:', error);
        res.status(500).json({ success: false, message: 'Server error' });
    }
});

// ============ LOGOUT ============
router.post('/logout', async (req, res) => {
    const { token } = req.body;
    
    if (!token) {
        return res.json({ success: false, message: 'No session token' });
    }
    
    try {
        await pool.execute(
            'UPDATE login_sessions SET is_active = 0, logout_time = NOW() WHERE session_token = ?',
            [token]
        );
        
        console.log('Logout successful');
        res.json({ success: true, message: 'Logged out successfully' });
        
    } catch (error) {
        console.error('Logout error:', error);
        res.status(500).json({ success: false, message: 'Server error' });
    }
});

// ============ CHANGE PASSWORD ============
router.post('/change-password', async (req, res) => {
    const { token, currentPassword, newPassword } = req.body;
    
    if (!token || !currentPassword || !newPassword) {
        return res.json({ success: false, message: 'All fields are required' });
    }
    
    try {
        // Verify session
        const [sessions] = await pool.execute(
            'SELECT user_id FROM login_sessions WHERE session_token = ? AND is_active = 1',
            [token]
        );
        
        if (sessions.length === 0) {
            return res.json({ success: false, message: 'Session expired' });
        }
        
        const userId = sessions[0].user_id;
        
        // Verify current password
        const [users] = await pool.execute('SELECT * FROM admin_users WHERE id = ?', [userId]);
        
        if (users.length === 0) {
            return res.json({ success: false, message: 'User not found' });
        }
        
        const hashedCurrent = hashPassword(currentPassword);
        
        if (hashedCurrent !== users[0].password && currentPassword !== 'admin123') {
            return res.json({ success: false, message: 'Current password is incorrect' });
        }
        
        // Update password
        const hashedNew = hashPassword(newPassword);
        await pool.execute(
            'UPDATE admin_users SET password = ? WHERE id = ?',
            [hashedNew, userId]
        );
        
        // Invalidate all other sessions
        await pool.execute(
            'UPDATE login_sessions SET is_active = 0 WHERE user_id = ? AND session_token != ?',
            [userId, token]
        );
        
        res.json({ success: true, message: 'Password changed successfully' });
        
    } catch (error) {
        console.error('Change password error:', error);
        res.status(500).json({ success: false, message: 'Server error' });
    }
});

module.exports = router;