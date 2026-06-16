const express = require('express');
const cors = require('cors');
const morgan = require('morgan');
const path = require('path');
const fs = require('fs');
require('dotenv').config();

const app = express();
const PORT = process.env.PORT || 3000;

const itemsRouter = require('./routes/items');
const skuRouter = require('../routes/sku-routes');
const authRouter = require('./routes/auth');


// Paths for data files
const DATA_DIR = path.join(__dirname, 'data');
const ANALYTICS_FILE = path.join(DATA_DIR, 'analytics.json');
const PIN_FILE = path.join(DATA_DIR, 'admin_pin.json');
const DECREASE_LOG_FILE = path.join(DATA_DIR, 'decrease_log.json');
const ARRIVAL_LOG_FILE = path.join(DATA_DIR, 'arrival_log.json');
const ACTIVITY_LOG_FILE = path.join(DATA_DIR, 'activity_log.json');
const ORDER_FILE = path.join(DATA_DIR, 'item_order.json');

// Ensure data directory exists
if (!fs.existsSync(DATA_DIR)) {
    fs.mkdirSync(DATA_DIR, { recursive: true });
    console.log('Created data directory:', DATA_DIR);
}

// Ensure all data files exist
if (!fs.existsSync(ANALYTICS_FILE)) {
    fs.writeFileSync(ANALYTICS_FILE, JSON.stringify({ visitors: [] }, null, 2));
}
if (!fs.existsSync(PIN_FILE)) {
    fs.writeFileSync(PIN_FILE, JSON.stringify({ pin: '1234' }, null, 2));
}
if (!fs.existsSync(DECREASE_LOG_FILE)) {
    fs.writeFileSync(DECREASE_LOG_FILE, JSON.stringify([], null, 2));
}
if (!fs.existsSync(ARRIVAL_LOG_FILE)) {
    fs.writeFileSync(ARRIVAL_LOG_FILE, JSON.stringify([], null, 2));
}
if (!fs.existsSync(ACTIVITY_LOG_FILE)) {
    fs.writeFileSync(ACTIVITY_LOG_FILE, JSON.stringify([], null, 2));
}
if (!fs.existsSync(ORDER_FILE)) {
    fs.writeFileSync(ORDER_FILE, JSON.stringify({}, null, 2));
}

// ============ FILE HELPERS ============
function readJSON(file) {
    try { return JSON.parse(fs.readFileSync(file, 'utf8')); } catch (e) { return null; }
}
function writeJSON(file, data) {
    try { fs.writeFileSync(file, JSON.stringify(data, null, 2)); } catch (e) { console.error('Write error:', e.message); }
}

// Load analytics on startup
let analyticsData = readJSON(ANALYTICS_FILE) || { visitors: [] };
console.log('Analytics loaded:', analyticsData.visitors.length, 'visitor records');

// ============ MIDDLEWARE ============
app.use(cors());
app.use(morgan('dev'));
app.use(express.json({ limit: '50mb' }));
app.use(express.urlencoded({ extended: true, limit: '50mb' }));

// Serve static files from public folder
app.use(express.static(path.join(__dirname, '..', 'public')));

// ============ ITEM ORDER (before /api/items router) ============
app.get('/api/items/order', (req, res) => {
    const orders = readJSON(ORDER_FILE) || {};
    const cat = req.query.category || 'all';
    const sort = req.query.sort || 'default';
    const key = cat + '_' + sort;
    res.json({ success: true, data: orders[key] || [] });
});

app.post('/api/items/order', (req, res) => {
    const orders = readJSON(ORDER_FILE) || {};
    const { category, sort, order } = req.body;
    const key = (category || 'all') + '_' + (sort || 'default');
    orders[key] = order;
    if (order && order.length > 500) orders[key] = order.slice(0, 500);
    writeJSON(ORDER_FILE, orders);
    console.log('Order saved for:', key, '- Items:', order ? order.length : 0);
    res.json({ success: true, message: 'Order saved' });
});

// ============ PERMANENT ACTIVITY LOG ============
app.get('/api/items/activity-log', (req, res) => {
    const log = readJSON(ACTIVITY_LOG_FILE) || [];
    res.json({ success: true, data: log.slice(0, 500) });
});

app.post('/api/items/activity-log', (req, res) => {
    const log = readJSON(ACTIVITY_LOG_FILE) || [];
    log.unshift(req.body);
    if (log.length > 2000) log.length = 2000;
    writeJSON(ACTIVITY_LOG_FILE, log);
    console.log('Activity log saved. Total:', log.length);
    res.json({ success: true, message: 'Activity saved' });
});

app.delete('/api/items/activity-log', (req, res) => {
    writeJSON(ACTIVITY_LOG_FILE, []);
    console.log('Activity log cleared');
    res.json({ success: true, message: 'Activity cleared' });
});

// ============ DECREASE LOG ============
app.get('/api/items/decrease-log', (req, res) => {
    const log = readJSON(DECREASE_LOG_FILE) || [];
    res.json({ success: true, data: log.slice(0, 100) });
});

app.post('/api/items/decrease-log', (req, res) => {
    const log = readJSON(DECREASE_LOG_FILE) || [];
    log.unshift(req.body);
    if (log.length > 100) log.length = 100;
    writeJSON(DECREASE_LOG_FILE, log);
    console.log('Decrease log saved. Total entries:', log.length);
    res.json({ success: true, message: 'Log saved' });
});

app.delete('/api/items/decrease-log', (req, res) => {
    writeJSON(DECREASE_LOG_FILE, []);
    console.log('Decrease log cleared');
    res.json({ success: true, message: 'Log cleared' });
});

// ============ ARRIVAL LOG ============
app.get('/api/items/arrival-log', (req, res) => {
    const log = readJSON(ARRIVAL_LOG_FILE) || [];
    res.json({ success: true, data: log.slice(0, 50) });
});

app.post('/api/items/arrival-log', (req, res) => {
    const log = readJSON(ARRIVAL_LOG_FILE) || [];
    log.unshift(req.body);
    if (log.length > 50) log.length = 50;
    writeJSON(ARRIVAL_LOG_FILE, log);
    console.log('Arrival log saved. Total entries:', log.length);
    res.json({ success: true, message: 'Arrival log saved' });
});

app.delete('/api/items/arrival-log', (req, res) => {
    writeJSON(ARRIVAL_LOG_FILE, []);
    console.log('Arrival log cleared');
    res.json({ success: true, message: 'Arrival log cleared' });
});

// API Routes (these come AFTER specific routes)
app.use('/api/items', itemsRouter);
app.use('/api/items/sku', skuRouter);
app.use('/api/items/arrival', skuRouter);
app.use('/api/auth', authRouter);


// ============ ANALYTICS - TRACK ============
app.post('/api/analytics/track', (req, res) => {
    const visitorData = {
        ip: req.ip || req.connection.remoteAddress || req.socket.remoteAddress || 'unknown',
        device: req.body.device || 'Unknown',
        browser: req.body.browser || 'Unknown',
        page: req.body.page || '/',
        time: req.body.time || new Date().toISOString(),
        userAgent: req.body.userAgent || '',
        language: req.body.language || 'Unknown',
        screenSize: req.body.screenSize || 'Unknown'
    };
    
    analyticsData.visitors.push(visitorData);
    if (analyticsData.visitors.length > 2000) analyticsData.visitors = analyticsData.visitors.slice(-2000);
    writeJSON(ANALYTICS_FILE, analyticsData);
    
    console.log('Tracked:', visitorData.browser, '-', visitorData.page, '- Total:', analyticsData.visitors.length);
    res.json({ success: true, message: 'Visit tracked', totalVisits: analyticsData.visitors.length });
});

// ============ ANALYTICS - GET ============
app.get('/api/analytics', (req, res) => {
    analyticsData = readJSON(ANALYTICS_FILE) || { visitors: [] };
    const now = new Date();
    const today = now.toDateString();
    const visitors = analyticsData.visitors;
    const todayVisitors = visitors.filter(v => new Date(v.time).toDateString() === today);
    const uniqueIPs = [...new Set(visitors.map(v => v.ip))];
    
    res.json({
        success: true,
        data: {
            totalVisits: visitors.length,
            uniqueVisitors: uniqueIPs.length,
            todayVisits: todayVisitors.length,
            liveNow: visitors.filter(v => (now - new Date(v.time)) < 5 * 60 * 1000).length,
            visitors: visitors.slice(-200).reverse()
        }
    });
});

// ============ ANALYTICS - CLEAR ============
app.delete('/api/analytics/clear', (req, res) => {
    analyticsData = { visitors: [] };
    writeJSON(ANALYTICS_FILE, analyticsData);
    res.json({ success: true, message: 'All analytics data cleared' });
});

// ============ PIN CODE - VERIFY ============
app.post('/api/admin/verify-pin', (req, res) => {
    const data = readJSON(PIN_FILE) || { pin: '1234' };
    res.json({ success: req.body.pin === data.pin });
});

// ============ PIN CODE - CHANGE ============
app.post('/api/admin/change-pin', (req, res) => {
    const { currentPin, newPin } = req.body;
    const data = readJSON(PIN_FILE) || { pin: '1234' };
    
    if (currentPin !== data.pin) return res.json({ success: false, message: 'Current PIN incorrect' });
    if (!newPin || !/^\d{4}$/.test(newPin)) return res.json({ success: false, message: 'PIN must be 4 digits' });
    
    data.pin = newPin;
    writeJSON(PIN_FILE, data);
    res.json({ success: true, message: 'PIN updated' });
});

// ============ CATCH-ALL ============
app.get('*', (req, res) => {
    if (req.url.startsWith('/api/')) {
        return res.status(404).json({ success: false, message: 'API endpoint not found' });
    }
    res.sendFile(path.join(__dirname, '..', 'public', 'index.html'));
});

// ============ START SERVER ============
app.listen(PORT, function() {
    console.log('');
    console.log('========================================');
    console.log('  Server: http://localhost:' + PORT);
    console.log('  API: http://localhost:' + PORT + '/api/items');
    console.log('  Analytics: http://localhost:' + PORT + '/api/analytics');
    console.log('  Dashboard: http://localhost:' + PORT + '/analytics.html');
    console.log('  Statistics: http://localhost:' + PORT + '/statistics.html');
    console.log('========================================');
    console.log('');
});