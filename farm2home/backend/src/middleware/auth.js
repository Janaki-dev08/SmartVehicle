/**
 * JWT Auth Middleware + Role-Based Access Control
 *
 * Usage:
 *   router.get('/route', authenticate, authorize('farmer'), handler)
 *   router.get('/route', authenticate, authorize(['farmer', 'admin']), handler)
 */

const jwt = require('jsonwebtoken');

/**
 * authenticate — verifies the Bearer token from Authorization header.
 * Attaches decoded user payload to req.user.
 */
const authenticate = (req, res, next) => {
  const authHeader = req.headers['authorization'];
  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    return res.status(401).json({ error: 'No token provided. Please log in.' });
  }

  const token = authHeader.split(' ')[1];
  try {
    const decoded = jwt.verify(token, process.env.JWT_SECRET);
    req.user = decoded; // { id, email, role }
    next();
  } catch (err) {
    return res.status(401).json({ error: 'Invalid or expired token. Please log in again.' });
  }
};

/**
 * authorize — checks that req.user.role matches the allowed role(s).
 * @param {string|string[]} roles - allowed role(s)
 */
const authorize = (roles) => {
  const allowedRoles = Array.isArray(roles) ? roles : [roles];
  return (req, res, next) => {
    if (!req.user) {
      return res.status(401).json({ error: 'Not authenticated.' });
    }
    if (!allowedRoles.includes(req.user.role)) {
      return res.status(403).json({
        error: `Access denied. Required role(s): ${allowedRoles.join(', ')}. Your role: ${req.user.role}`,
      });
    }
    next();
  };
};

module.exports = { authenticate, authorize };
