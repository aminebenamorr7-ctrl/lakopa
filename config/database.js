const mysql = require('mysql2');

const pool = mysql.createPool({
    host: 'localhost',
    user: 'root',
    password: '',           // Default XAMPP password is empty
    database: 'inventory_system',
    waitForConnections: true,
    connectionLimit: 10,
    queueLimit: 0
});

const promisePool = pool.promise();

pool.getConnection((err, connection) => {
    if (err) {
        console.error('❌ Database connection failed:', err.message);
        console.log('Make sure XAMPP MySQL is running and the database "inventory_system" exists');
        return;
    }
    console.log('✅ Connected to MySQL database successfully');
    connection.release();
});

module.exports = promisePool;