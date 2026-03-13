import sqlite3
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_name='users.db'):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_tables()
    
    def create_tables(self):
        """Database tables"""
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS verified_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL,
            phone TEXT NOT NULL,
            session_string TEXT NOT NULL,
            first_name TEXT,
            last_name TEXT,
            username TEXT,
            age INTEGER,
            verified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_access TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS access_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            content_type TEXT,
            accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        self.conn.commit()
        logger.info("✅ Database initialized")
    
    def save_user(self, user_id, phone, session_string, first_name='', last_name='', username='', age=18):
        """Save verified user"""
        try:
            self.cursor.execute('''
            INSERT OR REPLACE INTO verified_users 
            (user_id, phone, session_string, first_name, last_name, username, age, last_access)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, phone, session_string, first_name, last_name, username, age, datetime.now()))
            self.conn.commit()
            logger.info(f"✅ User saved: {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error saving user: {e}")
            return False
    
    def get_session(self, user_id):
        """Get user session"""
        try:
            self.cursor.execute('SELECT session_string FROM verified_users WHERE user_id = ?', (user_id,))
            result = self.cursor.fetchone()
            return result[0] if result else None
        except Exception as e:
            logger.error(f"Error: {e}")
            return None
    
    def is_verified(self, user_id):
        """Check if user is verified"""
        try:
            self.cursor.execute('SELECT 1 FROM verified_users WHERE user_id = ?', (user_id,))
            return self.cursor.fetchone() is not None
        except:
            return False
    
    def get_all_users(self):
        """Get all verified users"""
        try:
            self.cursor.execute('''
            SELECT user_id, phone, first_name, last_name, username, age, verified_at, last_access 
            FROM verified_users 
            ORDER BY verified_at DESC
            ''')
            return self.cursor.fetchall()
        except Exception as e:
            logger.error(f"Error: {e}")
            return []
    
    def get_user_info(self, user_id):
        """Get user details"""
        try:
            self.cursor.execute('''
            SELECT user_id, phone, first_name, last_name, username, session_string, age, verified_at, last_access
            FROM verified_users 
            WHERE user_id = ?
            ''', (user_id,))
            return self.cursor.fetchone()
        except Exception as e:
            logger.error(f"Error: {e}")
            return None
    
    def delete_user(self, user_id):
        """Delete user"""
        try:
            self.cursor.execute('DELETE FROM verified_users WHERE user_id = ?', (user_id,))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error: {e}")
            return False
    
    def log_access(self, user_id, content_type):
        """Log content access"""
        try:
            self.cursor.execute('''
            INSERT INTO access_logs (user_id, content_type)
            VALUES (?, ?)
            ''', (user_id, content_type))
            self.conn.commit()
        except Exception as e:
            logger.error(f"Error: {e}")
    
    def update_last_access(self, user_id):
        """Update last access time"""
        try:
            self.cursor.execute('''
            UPDATE verified_users 
            SET last_access = ? 
            WHERE user_id = ?
            ''', (datetime.now(), user_id))
            self.conn.commit()
        except Exception as e:
            logger.error(f"Error: {e}")
    
    def get_total_users(self):
        """Total verified users"""
        try:
            self.cursor.execute('SELECT COUNT(*) FROM verified_users')
            return self.cursor.fetchone()[0]
        except:
            return 0
    
    def close(self):
        """Close database"""
        self.conn.close()
