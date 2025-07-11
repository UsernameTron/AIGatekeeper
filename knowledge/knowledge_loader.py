"""
Knowledge Base Loader for Confidence Agent
"""

import json
import os
from typing import List, Dict, Any
from knowledge.knowledge_base_setup import SupportKnowledgeBaseManager

class KnowledgeLoader:
    """Loads knowledge base data for confidence agent"""
    
    @staticmethod
    async def load_sample_knowledge() -> List[Dict[str, Any]]:
        """Load sample knowledge base items"""
        
        # Create sample knowledge items
        knowledge_items = []
        
        # Password reset
        knowledge_items.append({
            'id': 'pwd_reset_001',
            'content': 'How to reset password: Go to login page, click forgot password, enter email address, check email for reset link, follow instructions to create new password',
            'title': 'Password Reset Guide',
            'category': 'authentication',
            'keywords': ['password', 'reset', 'login', 'forgot'],
            'metadata': {'difficulty': 'easy', 'category': 'auth'}
        })
        
        # Application crash
        knowledge_items.append({
            'id': 'app_crash_001',
            'content': 'Application crashing issues: Check system requirements, update to latest version, clear application cache, restart in safe mode, check error logs, reinstall if necessary',
            'title': 'Application Crash Troubleshooting',
            'category': 'troubleshooting',
            'keywords': ['crash', 'application', 'error', 'freeze'],
            'metadata': {'difficulty': 'medium', 'category': 'technical'}
        })
        
        # Network issues
        knowledge_items.append({
            'id': 'network_001',
            'content': 'Network connectivity problems: Check cable connections, restart router and modem, verify network settings, run network diagnostics, check firewall settings, contact ISP if needed',
            'title': 'Network Connectivity Issues',
            'category': 'networking',
            'keywords': ['network', 'internet', 'connection', 'wifi'],
            'metadata': {'difficulty': 'medium', 'category': 'network'}
        })
        
        # Email setup
        knowledge_items.append({
            'id': 'email_setup_001',
            'content': 'Email client configuration: Open email application, add new account, enter email and password, configure IMAP/POP3 settings, set SMTP server, test send and receive',
            'title': 'Email Client Setup',
            'category': 'configuration',
            'keywords': ['email', 'setup', 'configuration', 'outlook'],
            'metadata': {'difficulty': 'easy', 'category': 'email'}
        })
        
        # Software installation
        knowledge_items.append({
            'id': 'install_001',
            'content': 'Software installation problems: Run installer as administrator, disable antivirus temporarily, check compatibility, clear previous installation files, download fresh copy, use compatibility mode',
            'title': 'Software Installation Issues',
            'category': 'installation',
            'keywords': ['install', 'software', 'setup', 'compatibility'],
            'metadata': {'difficulty': 'medium', 'category': 'software'}
        })
        
        return knowledge_items
    
    @staticmethod
    async def load_from_file(filepath: str) -> List[Dict[str, Any]]:
        """Load knowledge base from JSON file"""
        try:
            with open(filepath, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Knowledge file {filepath} not found, using sample data")
            return await KnowledgeLoader.load_sample_knowledge()