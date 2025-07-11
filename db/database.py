"""
Database configuration and session management
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.exc import SQLAlchemyError
import logging

from .models import Base

class DatabaseManager:
    """Manages database connections and sessions"""
    
    def __init__(self, database_url=None):
        self.database_url = database_url or os.getenv('DATABASE_URL', 'postgresql://localhost/ai_gatekeeper')
        self.engine = None
        self.session_factory = None
        self.Session = None
        
    def initialize(self):
        """Initialize database engine and session factory"""
        try:
            self.engine = create_engine(
                self.database_url,
                echo=os.getenv('DATABASE_DEBUG', 'false').lower() == 'true',
                pool_pre_ping=True,
                pool_recycle=300
            )
            
            self.session_factory = sessionmaker(bind=self.engine)
            self.Session = scoped_session(self.session_factory)
            
            logging.info("Database initialized successfully")
            return True
            
        except SQLAlchemyError as e:
            logging.error(f"Database initialization failed: {e}")
            return False
    
    def create_tables(self):
        """Create all database tables"""
        try:
            Base.metadata.create_all(self.engine)
            logging.info("Database tables created successfully")
            return True
        except SQLAlchemyError as e:
            logging.error(f"Table creation failed: {e}")
            return False
    
    def get_session(self):
        """Get a database session"""
        if not self.Session:
            raise RuntimeError("Database not initialized")
        return self.Session()
    
    def close_session(self):
        """Close scoped session"""
        if self.Session:
            self.Session.remove()
    
    def health_check(self):
        """Check database health"""
        try:
            with self.get_session() as session:
                session.execute("SELECT 1")
            return True
        except Exception as e:
            logging.error(f"Database health check failed: {e}")
            return False

# Global database manager instance
db_manager = DatabaseManager()

def get_db_session():
    """Get database session - use this in routes"""
    return db_manager.get_session()

def init_database(app=None):
    """Initialize database with app context"""
    if not db_manager.initialize():
        raise RuntimeError("Failed to initialize database")
    
    if not db_manager.create_tables():
        raise RuntimeError("Failed to create database tables")
    
    if app:
        # Add teardown handler
        @app.teardown_appcontext
        def close_db(error):
            db_manager.close_session()
    
    return db_manager