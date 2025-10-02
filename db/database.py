"""
Database configuration and session management
"""

import os
from sqlalchemy import create_engine, event, pool
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.exc import SQLAlchemyError, OperationalError, DisconnectionError
import logging
import time
from contextlib import contextmanager

from .models import Base

class DatabaseManager:
    """Manages database connections and sessions with production-grade pooling"""

    def __init__(self, database_url=None):
        self.database_url = database_url or os.getenv('DATABASE_URL', 'postgresql://localhost/ai_gatekeeper')
        self.engine = None
        self.session_factory = None
        self.Session = None

        # Connection pool configuration
        self.pool_size = int(os.getenv('DB_POOL_SIZE', '20'))
        self.max_overflow = int(os.getenv('DB_MAX_OVERFLOW', '10'))
        self.pool_timeout = int(os.getenv('DB_POOL_TIMEOUT', '30'))
        self.pool_recycle = int(os.getenv('DB_POOL_RECYCLE', '3600'))

    def initialize(self):
        """Initialize database engine and session factory with production-grade pooling"""
        try:
            self.engine = create_engine(
                self.database_url,

                # Connection pooling
                poolclass=pool.QueuePool,
                pool_size=self.pool_size,
                max_overflow=self.max_overflow,
                pool_timeout=self.pool_timeout,
                pool_recycle=self.pool_recycle,
                pool_pre_ping=True,  # Verify connections before use

                # Performance optimizations
                echo=os.getenv('DATABASE_DEBUG', 'false').lower() == 'true',
                echo_pool=os.getenv('DATABASE_DEBUG_POOL', 'false').lower() == 'true',

                # Query optimization
                execution_options={
                    "isolation_level": "READ_COMMITTED"
                }
            )

            # Register event listeners
            self._register_event_listeners()

            self.session_factory = sessionmaker(
                bind=self.engine,
                expire_on_commit=False,  # Don't expire objects after commit
                autoflush=True,
                autocommit=False
            )
            self.Session = scoped_session(self.session_factory)

            logging.info(f"Database initialized with pool_size={self.pool_size}, "
                        f"max_overflow={self.max_overflow}")
            return True

        except SQLAlchemyError as e:
            logging.error(f"Database initialization failed: {e}")
            return False

    def _register_event_listeners(self):
        """Register SQLAlchemy event listeners for monitoring and optimization."""

        # Log slow queries
        @event.listens_for(self.engine, "before_cursor_execute")
        def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            conn.info.setdefault('query_start_time', []).append(time.time())

        @event.listens_for(self.engine, "after_cursor_execute")
        def receive_after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            total = time.time() - conn.info['query_start_time'].pop()
            if total > 1.0:  # Log queries taking > 1s
                logging.warning(f"Slow query ({total:.2f}s): {statement[:200]}")
    
    def create_tables(self):
        """Create all database tables with retry logic"""
        max_retries = 5
        retry_delay = 2  # seconds

        for attempt in range(max_retries):
            try:
                Base.metadata.create_all(self.engine)
                logging.info("Database tables created successfully")
                return True
            except (DisconnectionError, OperationalError) as e:
                if attempt < max_retries - 1:
                    logging.warning(f"Table creation failed (attempt {attempt + 1}/{max_retries}): {e}")
                    time.sleep(retry_delay * (attempt + 1))  # Exponential backoff
                else:
                    logging.error(f"Table creation failed after {max_retries} attempts: {e}")
                    return False
            except SQLAlchemyError as e:
                logging.error(f"Table creation failed: {e}")
                return False

    @contextmanager
    def get_session_context(self):
        """Context manager for database sessions with automatic cleanup."""
        session = self.get_session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

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
        """Enhanced health check with connection pool status"""
        try:
            with self.get_session_context() as session:
                session.execute("SELECT 1")

            # Get pool stats
            pool_stats = {
                'size': self.engine.pool.size(),
                'checked_out': self.engine.pool.checkedout(),
                'overflow': self.engine.pool.overflow(),
                'checkedin': self.engine.pool.checkedin()
            }

            logging.info(f"DB Health Check OK - Pool stats: {pool_stats}")
            return True

        except Exception as e:
            logging.error(f"Database health check failed: {e}")
            return False

    def get_pool_status(self) -> dict:
        """Get detailed connection pool status."""
        if not self.engine:
            return {}

        return {
            'pool_size': self.engine.pool.size(),
            'checked_out': self.engine.pool.checkedout(),
            'overflow': self.engine.pool.overflow(),
            'checked_in': self.engine.pool.checkedin(),
            'max_overflow': self.max_overflow,
            'total_capacity': self.pool_size + self.max_overflow
        }

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