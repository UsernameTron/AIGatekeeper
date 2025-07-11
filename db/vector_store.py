"""
Vector database integration for AI Gatekeeper
"""

import os
import logging
from typing import List, Dict, Any, Optional, Tuple
import chromadb
from chromadb.config import Settings
import numpy as np
from sqlalchemy.orm import Session

from .crud import KnowledgeBaseCRUD
from .models import KnowledgeBase

class VectorStore:
    """Vector database manager using ChromaDB"""
    
    def __init__(self, persist_directory: str = None):
        self.persist_directory = persist_directory or os.getenv('CHROMA_PERSIST_DIR', './chroma_db')
        self.client = None
        self.collections = {}
        
    def initialize(self):
        """Initialize ChromaDB client"""
        try:
            settings = Settings(
                chroma_db_impl="duckdb+parquet",
                persist_directory=self.persist_directory
            )
            self.client = chromadb.Client(settings)
            logging.info("Vector store initialized successfully")
            return True
        except Exception as e:
            logging.error(f"Vector store initialization failed: {e}")
            return False
    
    def get_or_create_collection(self, name: str, metadata: Dict[str, Any] = None):
        """Get or create a vector collection"""
        if name not in self.collections:
            try:
                self.collections[name] = self.client.get_or_create_collection(
                    name=name,
                    metadata=metadata or {}
                )
                logging.info(f"Collection '{name}' ready")
            except Exception as e:
                logging.error(f"Failed to create collection '{name}': {e}")
                return None
        return self.collections[name]
    
    def add_documents(self, collection_name: str, documents: List[Dict[str, Any]]):
        """Add documents to vector collection"""
        collection = self.get_or_create_collection(collection_name)
        if not collection:
            return False
        
        try:
            ids = [doc['id'] for doc in documents]
            texts = [doc['content'] for doc in documents]
            metadatas = [doc.get('metadata', {}) for doc in documents]
            
            collection.add(
                documents=texts,
                metadatas=metadatas,
                ids=ids
            )
            logging.info(f"Added {len(documents)} documents to collection '{collection_name}'")
            return True
        except Exception as e:
            logging.error(f"Failed to add documents to collection '{collection_name}': {e}")
            return False
    
    def search_documents(self, collection_name: str, query: str, n_results: int = 10,
                        where: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Search documents in vector collection"""
        collection = self.get_or_create_collection(collection_name)
        if not collection:
            return []
        
        try:
            results = collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where
            )
            
            # Format results
            formatted_results = []
            for i in range(len(results['ids'][0])):
                formatted_results.append({
                    'id': results['ids'][0][i],
                    'content': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i],
                    'similarity': 1.0 - results['distances'][0][i]  # Convert distance to similarity
                })
            
            return formatted_results
        except Exception as e:
            logging.error(f"Search failed in collection '{collection_name}': {e}")
            return []
    
    def update_document(self, collection_name: str, doc_id: str, content: str = None,
                       metadata: Dict[str, Any] = None):
        """Update document in vector collection"""
        collection = self.get_or_create_collection(collection_name)
        if not collection:
            return False
        
        try:
            update_data = {}
            if content:
                update_data['documents'] = [content]
            if metadata:
                update_data['metadatas'] = [metadata]
            
            collection.update(
                ids=[doc_id],
                **update_data
            )
            return True
        except Exception as e:
            logging.error(f"Failed to update document '{doc_id}' in collection '{collection_name}': {e}")
            return False
    
    def delete_document(self, collection_name: str, doc_id: str):
        """Delete document from vector collection"""
        collection = self.get_or_create_collection(collection_name)
        if not collection:
            return False
        
        try:
            collection.delete(ids=[doc_id])
            return True
        except Exception as e:
            logging.error(f"Failed to delete document '{doc_id}' from collection '{collection_name}': {e}")
            return False
    
    def health_check(self):
        """Check vector store health"""
        try:
            if not self.client:
                return False
            
            # Try to list collections
            collections = self.client.list_collections()
            return True
        except Exception as e:
            logging.error(f"Vector store health check failed: {e}")
            return False

class KnowledgeBaseManager:
    """Enhanced knowledge base manager with vector store integration"""
    
    def __init__(self, db_session: Session, vector_store: VectorStore):
        self.db_session = db_session
        self.vector_store = vector_store
        self.categories = [
            'technical_solutions',
            'troubleshooting_guides',
            'configuration_guides',
            'user_documentation',
            'escalation_procedures',
            'best_practices',
            'common_issues',
            'system_requirements',
            'installation_guides',
            'api_documentation'
        ]
    
    def initialize_knowledge_base(self):
        """Initialize knowledge base with sample data"""
        sample_data = self._generate_sample_knowledge_data()
        
        for category, items in sample_data.items():
            # Create vector collection
            collection = self.vector_store.get_or_create_collection(
                category, 
                metadata={'category': category}
            )
            
            # Add to vector store
            vector_docs = []
            for item in items:
                vector_docs.append({
                    'id': item['id'],
                    'content': item['content'],
                    'metadata': {
                        'title': item['title'],
                        'category': category,
                        'keywords': item['keywords']
                    }
                })
            
            self.vector_store.add_documents(category, vector_docs)
            
            # Add to SQL database
            for item in items:
                kb_item = KnowledgeBaseCRUD.create_knowledge_item(
                    self.db_session,
                    title=item['title'],
                    content=item['content'],
                    category=category,
                    keywords=item['keywords'],
                    metadata=item.get('metadata', {})
                )
                logging.info(f"Added knowledge item: {kb_item.title}")
    
    def search_knowledge(self, query: str, categories: List[str] = None, 
                        limit: int = 10) -> List[Dict[str, Any]]:
        """Search knowledge base using vector similarity"""
        if not categories:
            categories = self.categories
        
        all_results = []
        
        for category in categories:
            # Search vector store
            vector_results = self.vector_store.search_documents(
                category, query, n_results=limit
            )
            
            # Enrich with SQL database data
            for result in vector_results:
                kb_item = self.db_session.query(KnowledgeBase).filter(
                    KnowledgeBase.id == result['id']
                ).first()
                
                if kb_item:
                    result['effectiveness_score'] = kb_item.effectiveness_score
                    result['usage_count'] = kb_item.usage_count
                    result['updated_at'] = kb_item.updated_at.isoformat()
                
                all_results.append(result)
        
        # Sort by similarity score
        all_results.sort(key=lambda x: x['similarity'], reverse=True)
        return all_results[:limit]
    
    def add_knowledge_item(self, title: str, content: str, category: str,
                          keywords: List[str] = None, metadata: Dict[str, Any] = None):
        """Add new knowledge item to both vector store and SQL database"""
        # Add to SQL database
        kb_item = KnowledgeBaseCRUD.create_knowledge_item(
            self.db_session,
            title=title,
            content=content,
            category=category,
            keywords=keywords,
            metadata=metadata
        )
        
        # Add to vector store
        vector_doc = {
            'id': str(kb_item.id),
            'content': content,
            'metadata': {
                'title': title,
                'category': category,
                'keywords': keywords or []
            }
        }
        
        self.vector_store.add_documents(category, [vector_doc])
        return kb_item
    
    def update_knowledge_effectiveness(self, kb_id: str, effective: bool):
        """Update knowledge item effectiveness"""
        # Update SQL database
        kb_item = KnowledgeBaseCRUD.update_knowledge_effectiveness(
            self.db_session, kb_id, effective
        )
        
        # Update vector store metadata
        if kb_item:
            self.vector_store.update_document(
                kb_item.category,
                str(kb_item.id),
                metadata={
                    'title': kb_item.title,
                    'category': kb_item.category,
                    'keywords': kb_item.keywords or [],
                    'effectiveness_score': kb_item.effectiveness_score,
                    'usage_count': kb_item.usage_count
                }
            )
        
        return kb_item
    
    def _generate_sample_knowledge_data(self) -> Dict[str, List[Dict[str, Any]]]:
        """Generate sample knowledge base data"""
        return {
            'technical_solutions': [
                {
                    'id': 'tech_001',
                    'title': 'Application Crash Resolution',
                    'content': 'To resolve application crashes: 1. Check system requirements 2. Update to latest version 3. Clear application cache 4. Restart in safe mode 5. Check error logs 6. Reinstall if necessary',
                    'keywords': ['crash', 'application', 'error', 'troubleshooting'],
                    'metadata': {'difficulty': 'medium', 'estimated_time': '15-30 minutes'}
                },
                {
                    'id': 'tech_002',
                    'title': 'Database Connection Issues',
                    'content': 'Database connection problems: 1. Verify connection strings 2. Check database server status 3. Test network connectivity 4. Validate credentials 5. Review firewall settings 6. Check connection pool settings',
                    'keywords': ['database', 'connection', 'server', 'network'],
                    'metadata': {'difficulty': 'high', 'estimated_time': '30-60 minutes'}
                }
            ],
            'troubleshooting_guides': [
                {
                    'id': 'trouble_001',
                    'title': 'Network Connectivity Troubleshooting',
                    'content': 'Network connectivity problems: 1. Check cable connections 2. Restart router and modem 3. Verify network settings 4. Run network diagnostics 5. Check firewall settings 6. Contact ISP if needed',
                    'keywords': ['network', 'internet', 'connection', 'wifi'],
                    'metadata': {'difficulty': 'medium', 'estimated_time': '20-45 minutes'}
                },
                {
                    'id': 'trouble_002',
                    'title': 'Performance Issues Diagnosis',
                    'content': 'Performance troubleshooting: 1. Monitor system resources 2. Check running processes 3. Review system logs 4. Test with minimal configuration 5. Update drivers and software 6. Check hardware health',
                    'keywords': ['performance', 'slow', 'resources', 'optimization'],
                    'metadata': {'difficulty': 'high', 'estimated_time': '45-90 minutes'}
                }
            ],
            'configuration_guides': [
                {
                    'id': 'config_001',
                    'title': 'Email Client Configuration',
                    'content': 'Email client setup: 1. Open email application 2. Add new account 3. Enter email and password 4. Configure IMAP/POP3 settings 5. Set SMTP server 6. Test send and receive',
                    'keywords': ['email', 'setup', 'configuration', 'IMAP', 'SMTP'],
                    'metadata': {'difficulty': 'easy', 'estimated_time': '10-20 minutes'}
                },
                {
                    'id': 'config_002',
                    'title': 'SSL Certificate Installation',
                    'content': 'SSL certificate installation: 1. Generate certificate request 2. Submit to certificate authority 3. Download certificate files 4. Install on web server 5. Configure server settings 6. Test HTTPS functionality',
                    'keywords': ['ssl', 'certificate', 'https', 'security'],
                    'metadata': {'difficulty': 'high', 'estimated_time': '60-120 minutes'}
                }
            ],
            'user_documentation': [
                {
                    'id': 'user_001',
                    'title': 'Password Reset Guide',
                    'content': 'Password reset procedure: 1. Go to login page 2. Click "Forgot Password" 3. Enter email address 4. Check email for reset link 5. Follow instructions to create new password 6. Log in with new password',
                    'keywords': ['password', 'reset', 'login', 'account'],
                    'metadata': {'difficulty': 'easy', 'estimated_time': '5-10 minutes'}
                },
                {
                    'id': 'user_002',
                    'title': 'Account Settings Management',
                    'content': 'Managing account settings: 1. Log into your account 2. Navigate to Settings 3. Update profile information 4. Configure notification preferences 5. Set privacy settings 6. Save changes',
                    'keywords': ['account', 'settings', 'profile', 'preferences'],
                    'metadata': {'difficulty': 'easy', 'estimated_time': '5-15 minutes'}
                }
            ],
            'best_practices': [
                {
                    'id': 'best_001',
                    'title': 'Data Backup Best Practices',
                    'content': 'Data backup best practices: 1. Follow 3-2-1 rule 2. Automate backup processes 3. Test restore procedures 4. Use encryption for sensitive data 5. Monitor backup success 6. Document backup procedures',
                    'keywords': ['backup', 'data', 'security', 'recovery'],
                    'metadata': {'difficulty': 'medium', 'estimated_time': '30-60 minutes'}
                }
            ]
        }

# Global vector store instance
vector_store = VectorStore()

def init_vector_store():
    """Initialize vector store"""
    return vector_store.initialize()

def get_vector_store():
    """Get vector store instance"""
    return vector_store