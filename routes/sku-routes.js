const express = require('express');
const router = express.Router();
const db = require('../config/database');

// Quick add stock
router.post('/quick-add', async (req, res) => {
    try {
        const { sku, quantity } = req.body;
        if (!sku) return res.status(400).json({ success: false, message: 'SKU required' });
        
        const addQty = parseInt(quantity) || 1;
        const [items] = await db.query('SELECT * FROM items WHERE sku = ?', [sku]);
        
        if (items.length === 0) {
            return res.status(404).json({ success: false, message: 'Not found', action: 'create' });
        }
        
        const item = items[0];
        const newQty = item.quantity + addQty;
        await db.query('UPDATE items SET quantity = ? WHERE id = ?', [newQty, item.id]);
        const [updated] = await db.query('SELECT * FROM items WHERE id = ?', [item.id]);
        
        res.json({ success: true, message: `Added ${addQty}. Total: ${newQty}`, data: updated });
    } catch (error) {
        res.status(500).json({ success: false, message: error.message });
    }
});

// Process arrival
router.post('/process', async (req, res) => {
    try {
        const { sku, item_name, category, quantity, size, color, price, location } = req.body;
        if (!sku) return res.status(400).json({ success: false, message: 'SKU required' });
        
        const [existing] = await db.query('SELECT * FROM items WHERE sku = ?', [sku]);
        
        if (existing.length > 0) {
            const item = existing[0];
            const newQty = item.quantity + (parseInt(quantity) || 1);
            await db.query('UPDATE items SET quantity = ? WHERE id = ?', [newQty, item.id]);
            const [updated] = await db.query('SELECT * FROM items WHERE id = ?', [item.id]);
            res.json({ success: true, action: 'updated', message: `Updated! Total: ${newQty}`, data: updated });
        } else {
            const addQty = parseInt(quantity) || 1;
            const [result] = await db.query(
                'INSERT INTO items (item_name, quantity, size, color, description, sku, category, price, location) VALUES (?,?,?,?,?,?,?,?,?)',
                [item_name || 'New', addQty, size || null, color || null, 'Arrival', sku, category || null, parseFloat(price) || 0, location || null]
            );
            const [newItem] = await db.query('SELECT * FROM items WHERE id = ?', [result.insertId]);
            res.json({ success: true, action: 'created', message: `Created!`, data: newItem });
        }
    } catch (error) {
        res.status(500).json({ success: false, message: error.message });
    }
});

// Generate SKU
router.post('/generate', async (req, res) => {
    try {
        const { category } = req.body;
        if (!category) return res.status(400).json({ success: false, message: 'Category required' });
        
        const prefix = category.replace(/[^A-Za-z]/g, '').substring(0, 3).toUpperCase() || 'CAT';
        const [rows] = await db.query('SELECT * FROM items WHERE sku LIKE ?', [`${prefix}-%`]);
        const count = rows.length + 1;
        const sku = `${prefix}-${String(count).padStart(5, '0')}`;
        
        res.json({ success: true, data: { sku, prefix, number: count } });
    } catch (error) {
        res.status(500).json({ success: false, message: error.message });
    }
});

// Get prefixes
router.get('/prefixes', async (req, res) => {
    try {
        const [rows] = await db.query('SELECT DISTINCT LEFT(sku, 3) as prefix, category FROM items WHERE sku IS NOT NULL AND sku != ""');
        res.json({ success: true, data: rows });
    } catch (error) {
        res.json({ success: true, data: [] });
    }
});

module.exports = router;