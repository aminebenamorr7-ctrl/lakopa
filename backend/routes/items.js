const express = require('express');
const router = express.Router();
const { body, validationResult } = require('express-validator');
const db = require('../config/database');

// ===== STATIC ROUTES FIRST (before /:id routes) =====

// GET statistics
router.get('/stats/summary', async (req, res) => {
    try {
        const [totalItems] = await db.query('SELECT COUNT(*) as count FROM items');
        const [totalQuantity] = await db.query('SELECT SUM(quantity) as total FROM items');
        const [categories] = await db.query('SELECT COUNT(DISTINCT category) as count FROM items WHERE category IS NOT NULL AND category != ""');
        const [lowStock] = await db.query('SELECT COUNT(*) as count FROM items WHERE quantity < 10 AND quantity > 0');
        const [outOfStock] = await db.query('SELECT COUNT(*) as count FROM items WHERE quantity = 0');
        const [totalValue] = await db.query('SELECT SUM(quantity * price) as total FROM items WHERE price > 0');

        res.json({
            success: true,
            data: {
                totalItems: totalItems[0].count,
                totalQuantity: totalQuantity[0].total || 0,
                categories: categories[0].count,
                lowStock: lowStock[0].count,
                outOfStock: outOfStock[0].count,
                totalValue: totalValue[0].total || 0
            }
        });
    } catch (error) {
        console.error('Error fetching statistics:', error);
        res.status(500).json({
            success: false,
            message: 'Error fetching statistics',
            error: error.message
        });
    }
});

// GET categories list
router.get('/categories/list', async (req, res) => {
    try {
        const [rows] = await db.query(
            'SELECT DISTINCT category FROM items WHERE category IS NOT NULL AND category != "" ORDER BY category'
        );
        res.json({
            success: true,
            data: rows.map(row => row.category)
        });
    } catch (error) {
        console.error('Error fetching categories:', error);
        res.status(500).json({
            success: false,
            message: 'Error fetching categories',
            error: error.message
        });
    }
});

// ============ SKU & ARRIVAL ROUTES ============

// Get all category prefixes
router.get('/sku/prefixes', async (req, res) => {
    try {
        const [rows] = await db.query('SELECT * FROM category_prefixes ORDER BY category');
        res.json({ success: true, data: rows });
    } catch (error) {
        res.json({ success: true, data: [] });
    }
});

// Generate unique SKU for an item based on category
router.post('/sku/generate', async (req, res) => {
    try {
        const { category } = req.body;
        if (!category) {
            return res.status(400).json({ success: false, message: 'Category is required' });
        }

        let [prefixes] = await db.query('SELECT * FROM category_prefixes WHERE category = ?', [category]);
        
        if (prefixes.length === 0) {
            const prefix = category.replace(/[^A-Za-z]/g, '').substring(0, 3).toUpperCase() || 
                          category.substring(0, 3).toUpperCase();
            await db.query('INSERT INTO category_prefixes (category, prefix, last_number) VALUES (?, ?, 0)', [category, prefix]);
            [prefixes] = await db.query('SELECT * FROM category_prefixes WHERE category = ?', [category]);
        }

        const prefixData = prefixes[0];
        const newNumber = prefixData.last_number + 1;
        await db.query('UPDATE category_prefixes SET last_number = ? WHERE id = ?', [newNumber, prefixData.id]);
        const sku = `${prefixData.prefix}-${String(newNumber).padStart(5, '0')}`;
        
        res.json({ success: true, data: { sku, prefix: prefixData.prefix, number: newNumber } });
    } catch (error) {
        console.error('SKU generation error:', error);
        res.status(500).json({ success: false, message: 'Error generating SKU' });
    }
});

// Get item by SKU
router.get('/sku/lookup/:sku', async (req, res) => {
    try {
        const [rows] = await db.query('SELECT * FROM items WHERE sku = ?', [req.params.sku]);
        if (rows.length === 0) {
            return res.status(404).json({ success: false, message: 'SKU not found', action: 'create' });
        }
        res.json({ success: true, data: rows[0] });
    } catch (error) {
        res.status(500).json({ success: false, message: 'Error fetching SKU' });
    }
});

// Quick add stock - scan SKU and add quantity
router.post('/sku/quick-add', async (req, res) => {
    try {
        const { sku, quantity } = req.body;
        if (!sku) {
            return res.status(400).json({ success: false, message: 'SKU is required' });
        }

        const addQty = parseInt(quantity) || 1;
        const [items] = await db.query('SELECT * FROM items WHERE sku = ?', [sku]);
        
        if (items.length === 0) {
            return res.status(404).json({ 
                success: false, 
                message: 'Item not found. Would you like to create it?',
                sku: sku,
                action: 'create'
            });
        }

        const item = items[0];
        const newQty = item.quantity + addQty;
        await db.query('UPDATE items SET quantity = ? WHERE id = ?', [newQty, item.id]);
        const [updatedItem] = await db.query('SELECT * FROM items WHERE id = ?', [item.id]);
        
        res.json({ 
            success: true, 
            message: `Added ${addQty} units. New total: ${newQty}`,
            data: updatedItem[0]
        });
    } catch (error) {
        res.status(500).json({ success: false, message: 'Error updating stock' });
    }
});

// Process arrival - new stock arrival
router.post('/arrival/process', async (req, res) => {
    try {
        const { sku, item_name, category, quantity, size, color, price, location } = req.body;
        if (!sku) {
            return res.status(400).json({ success: false, message: 'SKU is required' });
        }

        const [existing] = await db.query('SELECT * FROM items WHERE sku = ?', [sku]);
        
        if (existing.length > 0) {
            const item = existing[0];
            const newQty = item.quantity + (parseInt(quantity) || 1);
            await db.query('UPDATE items SET quantity = ? WHERE id = ?', [newQty, item.id]);
            const [updated] = await db.query('SELECT * FROM items WHERE id = ?', [item.id]);
            res.json({
                success: true,
                action: 'updated',
                message: `Stock updated! Added ${quantity || 1} units. Total: ${newQty}`,
                data: updated[0]
            });
        } else {
            const addQty = parseInt(quantity) || 1;
            const [result] = await db.query(
                `INSERT INTO items (item_name, quantity, size, color, description, sku, category, price, location) 
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`,
                [item_name || 'New Item', addQty, size || null, color || null, 'Auto-added from arrival', sku, category || null, parseFloat(price) || 0, location || null]
            );
            const [newItem] = await db.query('SELECT * FROM items WHERE id = ?', [result.insertId]);
            res.json({
                success: true,
                action: 'created',
                message: `New item created and ${addQty} units added!`,
                data: newItem[0]
            });
        }
    } catch (error) {
        console.error('Arrival processing error:', error);
        res.status(500).json({ success: false, message: 'Error processing arrival' });
    }
});

// POST bulk import items from text
router.post('/bulk-import', async (req, res) => {
    try {
        console.log('Bulk import request received');
        console.log('Request body:', req.body);
        
        const { text } = req.body;
        
        if (!text || !text.trim()) {
            return res.status(400).json({
                success: false,
                message: 'Text content is required'
            });
        }

        const items = parseBulkText(text);
        console.log(`Parsed ${items.length} items from text`);
        
        if (items.length === 0) {
            return res.status(400).json({
                success: false,
                message: 'No valid items found in the text. Please check the format.'
            });
        }

        const insertedItems = [];
        const errors = [];

        for (let i = 0; i < items.length; i++) {
            const item = items[i];
            try {
                if (!item.item_name || !item.item_name.trim()) {
                    errors.push(`Row ${i + 1}: Item name is required`);
                    continue;
                }

                const [result] = await db.query(
                    `INSERT INTO items 
                    (item_name, quantity, size, color, description, sku, category, price, location) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`,
                    [
                        item.item_name.trim(),
                        item.quantity || 0,
                        item.size || null,
                        item.color || null,
                        item.description || null,
                        item.sku || null,
                        item.category || null,
                        item.price || 0,
                        item.location || null
                    ]
                );

                const [newItem] = await db.query('SELECT * FROM items WHERE id = ?', [result.insertId]);
                insertedItems.push(newItem[0]);
            } catch (error) {
                console.error(`Error inserting row ${i + 1}:`, error.message);
                if (error.code === 'ER_DUP_ENTRY') {
                    errors.push(`Row ${i + 1}: SKU "${item.sku}" already exists - item "${item.item_name}" skipped`);
                } else {
                    errors.push(`Row ${i + 1}: ${error.message}`);
                }
            }
        }

        res.json({
            success: true,
            message: `Successfully imported ${insertedItems.length} of ${items.length} items`,
            data: {
                total: items.length,
                imported: insertedItems.length,
                failed: errors.length,
                items: insertedItems,
                errors: errors
            }
        });
    } catch (error) {
        console.error('Bulk import error:', error);
        res.status(500).json({
            success: false,
            message: 'Error during bulk import',
            error: error.message
        });
    }
});

// POST bulk delete
router.post('/bulk-delete', async (req, res) => {
    try {
        const { ids } = req.body;
        
        if (!ids || !Array.isArray(ids) || ids.length === 0) {
            return res.status(400).json({
                success: false,
                message: 'Please provide an array of item IDs to delete'
            });
        }

        const [result] = await db.query('DELETE FROM items WHERE id IN (?)', [ids]);

        res.json({
            success: true,
            message: `Successfully deleted ${result.affectedRows} items`,
            data: {
                deleted: result.affectedRows
            }
        });
    } catch (error) {
        console.error('Bulk delete error:', error);
        res.status(500).json({
            success: false,
            message: 'Error deleting items',
            error: error.message
        });
    }
});

// ===== DYNAMIC ROUTES (after static routes) =====

// GET all items with optional search and filter
router.get('/', async (req, res) => {
    try {
        const { search, category, sort, order } = req.query;
        
        let query = 'SELECT * FROM items WHERE 1=1';
        const params = [];
        
        if (search) {
            query += ' AND (item_name LIKE ? OR description LIKE ? OR sku LIKE ? OR color LIKE ? OR size LIKE ?)';
            const searchTerm = `%${search}%`;
            params.push(searchTerm, searchTerm, searchTerm, searchTerm, searchTerm);
        }
        
        if (category) {
            query += ' AND category = ?';
            params.push(category);
        }
        
        const sortColumn = sort || 'created_at';
        const sortOrder = order || 'DESC';
        const allowedColumns = ['created_at', 'item_name', 'quantity', 'price', 'id'];
        const allowedOrders = ['ASC', 'DESC'];
        
        if (allowedColumns.includes(sortColumn) && allowedOrders.includes(sortOrder.toUpperCase())) {
            query += ` ORDER BY ${sortColumn} ${sortOrder}`;
        } else {
            query += ' ORDER BY created_at DESC';
        }
        
        const [rows] = await db.query(query, params);
        res.json({
            success: true,
            count: rows.length,
            data: rows
        });
    } catch (error) {
        console.error('Error fetching items:', error);
        res.status(500).json({
            success: false,
            message: 'Error fetching items',
            error: error.message
        });
    }
});

// POST create new item
router.post('/', [
    body('item_name').trim().notEmpty().withMessage('Item name is required'),
    body('quantity').isInt({ min: 0 }).withMessage('Quantity must be a positive number'),
    body('size').optional().trim(),
    body('color').optional().trim(),
    body('description').optional().trim(),
    body('sku').optional().trim(),
    body('category').optional().trim(),
    body('price').optional().isFloat({ min: 0 }).withMessage('Price must be a positive number'),
    body('location').optional().trim()
], async (req, res) => {
    const errors = validationResult(req);
    if (!errors.isEmpty()) {
        return res.status(400).json({
            success: false,
            errors: errors.array()
        });
    }

    try {
        const {
            item_name,
            quantity,
            size,
            color,
            description,
            sku,
            category,
            price,
            location
        } = req.body;

        const [result] = await db.query(
            `INSERT INTO items 
            (item_name, quantity, size, color, description, sku, category, price, location) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`,
            [item_name, quantity, size || null, color || null, description || null, sku || null, category || null, price || 0, location || null]
        );

        const [newItem] = await db.query('SELECT * FROM items WHERE id = ?', [result.insertId]);

        res.status(201).json({
            success: true,
            message: 'Item created successfully',
            data: newItem[0]
        });
    } catch (error) {
        console.error('Create item error:', error);
        if (error.code === 'ER_DUP_ENTRY') {
            return res.status(400).json({
                success: false,
                message: 'SKU already exists'
            });
        }
        res.status(500).json({
            success: false,
            message: 'Error creating item',
            error: error.message
        });
    }
});

// GET single item by ID
router.get('/:id', async (req, res) => {
    try {
        if (isNaN(req.params.id)) {
            return res.status(404).json({
                success: false,
                message: 'Route not found'
            });
        }
        
        const [rows] = await db.query('SELECT * FROM items WHERE id = ?', [req.params.id]);
        
        if (rows.length === 0) {
            return res.status(404).json({
                success: false,
                message: 'Item not found'
            });
        }
        
        res.json({
            success: true,
            data: rows[0]
        });
    } catch (error) {
        res.status(500).json({
            success: false,
            message: 'Error fetching item',
            error: error.message
        });
    }
});

// PUT update item
router.put('/:id', [
    body('item_name').trim().notEmpty().withMessage('Item name is required'),
    body('quantity').isInt({ min: 0 }).withMessage('Quantity must be a positive number'),
    body('size').optional().trim(),
    body('color').optional().trim(),
    body('description').optional().trim(),
    body('sku').optional().trim(),
    body('category').optional().trim(),
    body('price').optional().isFloat({ min: 0 }).withMessage('Price must be a positive number'),
    body('location').optional().trim()
], async (req, res) => {
    const errors = validationResult(req);
    if (!errors.isEmpty()) {
        return res.status(400).json({
            success: false,
            errors: errors.array()
        });
    }

    try {
        const {
            item_name,
            quantity,
            size,
            color,
            description,
            sku,
            category,
            price,
            location
        } = req.body;

        const [result] = await db.query(
            `UPDATE items SET 
            item_name = ?, quantity = ?, size = ?, color = ?, 
            description = ?, sku = ?, category = ?, price = ?, location = ?
            WHERE id = ?`,
            [item_name, quantity, size || null, color || null, description || null, sku || null, category || null, price || 0, location || null, req.params.id]
        );

        if (result.affectedRows === 0) {
            return res.status(404).json({
                success: false,
                message: 'Item not found'
            });
        }

        const [updatedItem] = await db.query('SELECT * FROM items WHERE id = ?', [req.params.id]);

        res.json({
            success: true,
            message: 'Item updated successfully',
            data: updatedItem[0]
        });
    } catch (error) {
        console.error('Update error:', error);
        if (error.code === 'ER_DUP_ENTRY') {
            return res.status(400).json({
                success: false,
                message: 'SKU already exists'
            });
        }
        res.status(500).json({
            success: false,
            message: 'Error updating item',
            error: error.message
        });
    }
});

// PATCH update quantity
router.patch('/:id/quantity', [
    body('quantity').isInt({ min: 0 }).withMessage('Quantity must be a positive number'),
    body('operation').optional().isIn(['add', 'subtract', 'set']).withMessage('Operation must be add, subtract, or set')
], async (req, res) => {
    const errors = validationResult(req);
    if (!errors.isEmpty()) {
        return res.status(400).json({
            success: false,
            errors: errors.array()
        });
    }

    try {
        const { quantity, operation = 'set' } = req.body;
        
        let newQuantity;
        if (operation === 'add') {
            const [current] = await db.query('SELECT quantity FROM items WHERE id = ?', [req.params.id]);
            if (current.length === 0) {
                return res.status(404).json({ success: false, message: 'Item not found' });
            }
            newQuantity = current[0].quantity + quantity;
        } else if (operation === 'subtract') {
            const [current] = await db.query('SELECT quantity FROM items WHERE id = ?', [req.params.id]);
            if (current.length === 0) {
                return res.status(404).json({ success: false, message: 'Item not found' });
            }
            newQuantity = Math.max(0, current[0].quantity - quantity);
        } else {
            newQuantity = quantity;
        }

        await db.query('UPDATE items SET quantity = ? WHERE id = ?', [newQuantity, req.params.id]);
        
        const [updatedItem] = await db.query('SELECT * FROM items WHERE id = ?', [req.params.id]);
        
        res.json({
            success: true,
            message: 'Quantity updated successfully',
            data: updatedItem[0]
        });
    } catch (error) {
        res.status(500).json({
            success: false,
            message: 'Error updating quantity',
            error: error.message
        });
    }
});

// DELETE item
router.delete('/:id', async (req, res) => {
    try {
        const [result] = await db.query('DELETE FROM items WHERE id = ?', [req.params.id]);

        if (result.affectedRows === 0) {
            return res.status(404).json({
                success: false,
                message: 'Item not found'
            });
        }

        res.json({
            success: true,
            message: 'Item deleted successfully'
        });
    } catch (error) {
        res.status(500).json({
            success: false,
            message: 'Error deleting item',
            error: error.message
        });
    }
});

// ===== HELPER FUNCTIONS =====

function parseBulkText(text) {
    const items = [];
    const lines = text.split('\n').filter(line => line.trim());
    
    if (lines.length === 0) return items;
    
    const firstLine = lines[0];
    let isStructured = false;
    let delimiter = ',';
    
    if (firstLine.includes('\t')) {
        isStructured = true;
        delimiter = '\t';
    } else if (firstLine.includes(',') && firstLine.split(',').length >= 2) {
        const parts = firstLine.split(',');
        if (parts.length >= 2 && parts[1] && !isNaN(parts[1].trim())) {
            isStructured = true;
            delimiter = ',';
        }
    } else if (firstLine.includes('|')) {
        isStructured = true;
        delimiter = '|';
    } else if (firstLine.includes(';')) {
        isStructured = true;
        delimiter = ';';
    }
    
    if (isStructured) {
        return parseStructuredText(lines, delimiter);
    }
    
    for (const line of lines) {
        const item = parseFreeTextLine(line);
        if (item && item.item_name && item.item_name.trim()) {
            items.push(item);
        }
    }
    
    return items;
}

function parseStructuredText(lines, delimiter) {
    const items = [];
    const firstLine = lines[0].toLowerCase();
    const headers = firstLine.split(delimiter).map(h => h.trim().replace(/["']/g, ''));
    
    const headerKeywords = ['name', 'item', 'product', 'quantity', 'qty', 'size', 'color', 'category', 'price', 'sku', 'location', 'description'];
    const isHeader = headers.some(h => headerKeywords.some(keyword => h.includes(keyword)));
    
    const startIndex = isHeader ? 1 : 0;
    
    const colMap = {
        name: headers.findIndex(h => h.includes('name') || h.includes('item') || h.includes('product')),
        quantity: headers.findIndex(h => h.includes('quant') || h.includes('qty')),
        size: headers.findIndex(h => h === 'size' || h.includes('size')),
        color: headers.findIndex(h => h === 'color' || h.includes('color')),
        category: headers.findIndex(h => h.includes('cat')),
        price: headers.findIndex(h => h.includes('price')),
        sku: headers.findIndex(h => h === 'sku' || h.includes('sku')),
        location: headers.findIndex(h => h.includes('loc')),
        description: headers.findIndex(h => h.includes('desc'))
    };
    
    for (let i = startIndex; i < lines.length; i++) {
        const columns = lines[i].split(delimiter).map(c => c.trim().replace(/["']/g, ''));
        
        if (columns.length >= 1 && columns[0]) {
            const item = {
                item_name: colMap.name >= 0 ? columns[colMap.name] : columns[0],
                quantity: colMap.quantity >= 0 ? (parseInt(columns[colMap.quantity]) || 0) : (columns[1] ? parseInt(columns[1]) || 0 : 0),
                size: colMap.size >= 0 ? (columns[colMap.size] || null) : (columns[2] || null),
                color: colMap.color >= 0 ? (columns[colMap.color] || null) : (columns[3] || null),
                category: colMap.category >= 0 ? (columns[colMap.category] || null) : (columns[4] || null),
                price: colMap.price >= 0 ? (parseFloat(columns[colMap.price]) || 0) : (columns[5] ? parseFloat(columns[5]) || 0 : 0),
                sku: colMap.sku >= 0 ? (columns[colMap.sku] || null) : null,
                location: colMap.location >= 0 ? (columns[colMap.location] || null) : null,
                description: colMap.description >= 0 ? (columns[colMap.description] || null) : null
            };
            
            if (item.item_name && item.item_name.trim()) {
                items.push(item);
            }
        }
    }
    
    return items;
}

function parseFreeTextLine(line) {
    const item = {
        item_name: '',
        quantity: 0,
        size: null,
        color: null,
        description: null,
        sku: null,
        category: null,
        price: 0,
        location: null
    };
    
    const detailedMatch = line.match(/^(.+?)\s*[-–:]\s*(.+)$/);
    
    if (detailedMatch) {
        item.item_name = detailedMatch[1].trim();
        const details = detailedMatch[2];
        
        const qtyMatch = details.match(/(?:qty|quantity|qte)\s*:?\s*(\d+)/i);
        if (qtyMatch) item.quantity = parseInt(qtyMatch[1]);
        
        const sizeMatch = details.match(/(?:size|taille)\s*:?\s*([^,;]+?)(?=\s*(?:,|;|\b(?:qty|quantity|color|price|sku|cat|loc)\b|$))/i);
        if (sizeMatch) item.size = sizeMatch[1].trim();
        
        const colorMatch = details.match(/(?:color|couleur)\s*:?\s*([^,;]+?)(?=\s*(?:,|;|\b(?:qty|quantity|size|price|sku|cat|loc)\b|$))/i);
        if (colorMatch) item.color = colorMatch[1].trim();
        
        const skuMatch = details.match(/(?:sku|ref)\s*:?\s*([^,;]+?)(?=\s*(?:,|;|\b(?:qty|quantity|size|color|price|cat|loc)\b|$))/i);
        if (skuMatch) item.sku = skuMatch[1].trim();
        
        const catMatch = details.match(/(?:cat|category)\s*:?\s*([^,;]+?)(?=\s*(?:,|;|\b(?:qty|quantity|size|color|price|sku|loc)\b|$))/i);
        if (catMatch) item.category = catMatch[1].trim();
        
        const priceMatch = details.match(/(?:price|prix)\s*:?\s*\$?([\d.]+)/i);
        if (priceMatch) item.price = parseFloat(priceMatch[1]);
        
        const locMatch = details.match(/(?:loc|location|emplacement)\s*:?\s*([^,;]+?)(?=\s*(?:,|;|$))/i);
        if (locMatch) item.location = locMatch[1].trim();
        
        return item;
    }
    
    const parts = line.split(',').map(p => p.trim());
    if (parts.length >= 2 && parts[1] && !isNaN(parts[1])) {
        item.item_name = parts[0];
        item.quantity = parseInt(parts[1]) || 0;
        if (parts[2]) item.size = parts[2];
        if (parts[3]) item.color = parts[3];
        if (parts[4]) item.category = parts[4];
        if (parts[5]) item.price = parseFloat(parts[5]) || 0;
        return item;
    }
    
    item.item_name = line.trim();
    return item;
}

module.exports = router;