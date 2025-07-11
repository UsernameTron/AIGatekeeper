"""
Shared Configuration Management System
Centralizes configuration for both VectorDBRAG and MindMeld projects
"""

import os
import json
import yaml
from typing import Dict, Any, Optional, Union, List
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum


class ConfigEnvironment(Enum):
    """Configuration environments."""
    DEVELOPMENT = "development"
    TESTING = "testing" 
    PRODUCTION = "production"


class ModelProvider(Enum):
    """Supported model providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    LOCAL = "local"


@dataclass
class ModelConfig:
    """Configuration for a specific model."""
    provider: ModelProvider
    model_name: str
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    max_tokens: int = 4000
    temperature: float = 0.1
    timeout: int = 30
    max_retries: int = 3


@dataclass
class AgentConfig:
    """Configuration for agent behavior."""
    default_model: str = "gpt-4o"
    fast_model: str = "gpt-4o-mini"
    multimodal_model: str = "gpt-4o"
    max_execution_time: int = 300  # 5 minutes
    enable_safety_checks: bool = True
    enable_monitoring: bool = True
    max_concurrent_executions: int = 10


@dataclass
class RAGConfig:
    """Configuration for RAG system."""
    embedding_model: str = "text-embedding-3-small"
    chunk_size: int = 1000
    chunk_overlap: int = 200
    max_search_results: int = 10
    similarity_threshold: float = 0.7
    enable_hybrid_search: bool = True


@dataclass
class AnalyticsConfig:
    """Configuration for analytics integration."""
    enable_analytics: bool = True
    reporting_interval: int = 3600  # 1 hour in seconds
    metrics_retention_days: int = 30
    enable_performance_monitoring: bool = True


@dataclass
class SupportConfig:
    """Configuration for AI Gatekeeper support system."""
    confidence_threshold: float = 0.8
    risk_threshold: float = 0.3
    enable_swarm_intelligence: bool = True
    max_escalation_time: int = 1800  # 30 minutes in seconds
    enable_learning_updates: bool = True
    feedback_required_for_learning: bool = True


@dataclass
class SharedConfig:
    """Centralized configuration for the shared agent framework."""
    
    # Environment
    environment: ConfigEnvironment = ConfigEnvironment.DEVELOPMENT
    debug: bool = True
    
    # Models
    models: Dict[str, ModelConfig] = field(default_factory=dict)
    
    # Components
    agent_config: AgentConfig = field(default_factory=AgentConfig)
    rag_config: RAGConfig = field(default_factory=RAGConfig)
    analytics_config: AnalyticsConfig = field(default_factory=AnalyticsConfig)
    support_config: SupportConfig = field(default_factory=SupportConfig)
    
    # System settings
    log_level: str = "INFO"
    enable_telemetry: bool = False
    workspace_path: Optional[str] = None
    
    # Security
    allowed_hosts: List[str] = field(default_factory=lambda: ["localhost", "127.0.0.1"])
    enable_cors: bool = True
    
    def __post_init__(self):
        """Initialize default models if none provided."""
        if not self.models:
            self._setup_default_models()
        self._load_environment_variables()
    
    def _setup_default_models(self):
        """Setup default model configurations."""
        openai_key = os.getenv('OPENAI_API_KEY')
        
        # Default OpenAI models
        self.models.update({
            'gpt-4o': ModelConfig(
                provider=ModelProvider.OPENAI,
                model_name='gpt-4o',
                api_key=openai_key,
                max_tokens=4000,
                temperature=0.1
            ),
            'gpt-4o-mini': ModelConfig(
                provider=ModelProvider.OPENAI,
                model_name='gpt-4o-mini',
                api_key=openai_key,
                max_tokens=2000,
                temperature=0.1
            ),
            'gpt-4': ModelConfig(
                provider=ModelProvider.OPENAI,
                model_name='gpt-4',
                api_key=openai_key,
                max_tokens=4000,
                temperature=0.1
            ),
            'gpt-3.5-turbo': ModelConfig(
                provider=ModelProvider.OPENAI,
                model_name='gpt-3.5-turbo',
                api_key=openai_key,
                max_tokens=2000,
                temperature=0.1
            ),
        })
    
    def _load_environment_variables(self):
        """Load configuration from environment variables."""
        # Support configuration
        if hasattr(self, 'support_config') and self.support_config:
            self.support_config.confidence_threshold = float(os.getenv(
                'CONFIDENCE_THRESHOLD', 
                os.getenv('SUPPORT_CONFIDENCE_THRESHOLD', str(self.support_config.confidence_threshold))
            ))
            self.support_config.risk_threshold = float(os.getenv(
                'RISK_THRESHOLD', 
                os.getenv('SUPPORT_RISK_THRESHOLD', str(self.support_config.risk_threshold))
            ))
            self.support_config.enable_swarm_intelligence = os.getenv(
                'ENABLE_SWARM_INTELLIGENCE', 'true'
            ).lower() == 'true'
            self.support_config.max_escalation_time = int(os.getenv(
                'MAX_ESCALATION_TIME', str(self.support_config.max_escalation_time)
            ))
            self.support_config.enable_learning_updates = os.getenv(
                'ENABLE_LEARNING_UPDATES', 'true'
            ).lower() == 'true'
            self.support_config.feedback_required_for_learning = os.getenv(
                'FEEDBACK_REQUIRED_FOR_LEARNING', 'true'
            ).lower() == 'true'
        
        # Environment
        env_name = os.getenv('ENVIRONMENT', 'development').lower()
        if env_name in ['development', 'dev']:
            self.environment = ConfigEnvironment.DEVELOPMENT
        elif env_name in ['testing', 'test']:
            self.environment = ConfigEnvironment.TESTING
        elif env_name in ['production', 'prod']:
            self.environment = ConfigEnvironment.PRODUCTION
        
        # Debug mode
        self.debug = os.getenv('DEBUG', 'true' if self.environment == ConfigEnvironment.DEVELOPMENT else 'false').lower() == 'true'
        
        # Log level
        self.log_level = os.getenv('LOG_LEVEL', self.log_level)
        
        # Telemetry
        self.enable_telemetry = os.getenv('ENABLE_TELEMETRY', 'false').lower() == 'true'
    
    def get_model_config(self, model_name: str) -> Optional[ModelConfig]:
        """Get configuration for a specific model."""
        return self.models.get(model_name)
    
    def add_model(self, name: str, config: ModelConfig):
        """Add a new model configuration."""
        self.models[name] = config
    
    def validate(self) -> List[str]:
        """Validate configuration and return list of errors."""
        errors = []
        
        # Check required API keys
        for model_name, model_config in self.models.items():
            if model_config.provider == ModelProvider.OPENAI:
                if not model_config.api_key:
                    errors.append(f"Missing OpenAI API key for model {model_name}")
        
        # Validate agent config
        if self.agent_config.max_execution_time <= 0:
            errors.append("Agent max_execution_time must be positive")
        
        if self.agent_config.max_concurrent_executions <= 0:
            errors.append("Agent max_concurrent_executions must be positive")
        
        # Validate RAG config
        if self.rag_config.chunk_size <= 0:
            errors.append("RAG chunk_size must be positive")
        
        if self.rag_config.similarity_threshold < 0 or self.rag_config.similarity_threshold > 1:
            errors.append("RAG similarity_threshold must be between 0 and 1")
        
        # Validate support config
        if self.support_config.confidence_threshold < 0 or self.support_config.confidence_threshold > 1:
            errors.append("Support confidence_threshold must be between 0 and 1")
        
        if self.support_config.risk_threshold < 0 or self.support_config.risk_threshold > 1:
            errors.append("Support risk_threshold must be between 0 and 1")
        
        if self.support_config.max_escalation_time <= 0:
            errors.append("Support max_escalation_time must be positive")
        
        return errors
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            'environment': self.environment.value,
            'debug': self.debug,
            'models': {
                name: {
                    'provider': config.provider.value,
                    'model_name': config.model_name,
                    'max_tokens': config.max_tokens,
                    'temperature': config.temperature,
                    'timeout': config.timeout,
                    'max_retries': config.max_retries
                }
                for name, config in self.models.items()
            },
            'agent_config': {
                'default_model': self.agent_config.default_model,
                'fast_model': self.agent_config.fast_model,
                'multimodal_model': self.agent_config.multimodal_model,
                'max_execution_time': self.agent_config.max_execution_time,
                'enable_safety_checks': self.agent_config.enable_safety_checks,
                'enable_monitoring': self.agent_config.enable_monitoring,
                'max_concurrent_executions': self.agent_config.max_concurrent_executions
            },
            'rag_config': {
                'embedding_model': self.rag_config.embedding_model,
                'chunk_size': self.rag_config.chunk_size,
                'chunk_overlap': self.rag_config.chunk_overlap,
                'max_search_results': self.rag_config.max_search_results,
                'similarity_threshold': self.rag_config.similarity_threshold,
                'enable_hybrid_search': self.rag_config.enable_hybrid_search
            },
            'analytics_config': {
                'enable_analytics': self.analytics_config.enable_analytics,
                'reporting_interval': self.analytics_config.reporting_interval,
                'metrics_retention_days': self.analytics_config.metrics_retention_days,
                'enable_performance_monitoring': self.analytics_config.enable_performance_monitoring
            },
            'support_config': {
                'confidence_threshold': self.support_config.confidence_threshold,
                'risk_threshold': self.support_config.risk_threshold,
                'enable_swarm_intelligence': self.support_config.enable_swarm_intelligence,
                'max_escalation_time': self.support_config.max_escalation_time,
                'enable_learning_updates': self.support_config.enable_learning_updates,
                'feedback_required_for_learning': self.support_config.feedback_required_for_learning
            },
            'log_level': self.log_level,
            'enable_telemetry': self.enable_telemetry,
            'workspace_path': self.workspace_path,
            'allowed_hosts': self.allowed_hosts,
            'enable_cors': self.enable_cors
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SharedConfig':
        """Create configuration from dictionary."""
        config = cls()
        
        # Environment
        if 'environment' in data:
            config.environment = ConfigEnvironment(data['environment'])
        
        config.debug = data.get('debug', True)
        config.log_level = data.get('log_level', 'INFO')
        config.enable_telemetry = data.get('enable_telemetry', False)
        config.workspace_path = data.get('workspace_path')
        config.allowed_hosts = data.get('allowed_hosts', ["localhost", "127.0.0.1"])
        config.enable_cors = data.get('enable_cors', True)
        
        # Models
        if 'models' in data:
            config.models = {}
            for name, model_data in data['models'].items():
                config.models[name] = ModelConfig(
                    provider=ModelProvider(model_data['provider']),
                    model_name=model_data['model_name'],
                    api_key=model_data.get('api_key'),
                    api_base=model_data.get('api_base'),
                    max_tokens=model_data.get('max_tokens', 4000),
                    temperature=model_data.get('temperature', 0.1),
                    timeout=model_data.get('timeout', 30),
                    max_retries=model_data.get('max_retries', 3)
                )
        
        # Agent config
        if 'agent_config' in data:
            agent_data = data['agent_config']
            config.agent_config = AgentConfig(
                default_model=agent_data.get('default_model', 'gpt-4o'),
                fast_model=agent_data.get('fast_model', 'gpt-4o-mini'),
                multimodal_model=agent_data.get('multimodal_model', 'gpt-4o'),
                max_execution_time=agent_data.get('max_execution_time', 300),
                enable_safety_checks=agent_data.get('enable_safety_checks', True),
                enable_monitoring=agent_data.get('enable_monitoring', True),
                max_concurrent_executions=agent_data.get('max_concurrent_executions', 10)
            )
        
        # RAG config
        if 'rag_config' in data:
            rag_data = data['rag_config']
            config.rag_config = RAGConfig(
                embedding_model=rag_data.get('embedding_model', 'text-embedding-3-small'),
                chunk_size=rag_data.get('chunk_size', 1000),
                chunk_overlap=rag_data.get('chunk_overlap', 200),
                max_search_results=rag_data.get('max_search_results', 10),
                similarity_threshold=rag_data.get('similarity_threshold', 0.7),
                enable_hybrid_search=rag_data.get('enable_hybrid_search', True)
            )
        
        # Analytics config
        if 'analytics_config' in data:
            analytics_data = data['analytics_config']
            config.analytics_config = AnalyticsConfig(
                enable_analytics=analytics_data.get('enable_analytics', True),
                reporting_interval=analytics_data.get('reporting_interval', 3600),
                metrics_retention_days=analytics_data.get('metrics_retention_days', 30),
                enable_performance_monitoring=analytics_data.get('enable_performance_monitoring', True)
            )
        
        return config


class ConfigManager:
    """Manages configuration loading and saving."""
    
    def __init__(self, config_dir: Optional[str] = None):
        """Initialize configuration manager."""
        self.config_dir = Path(config_dir) if config_dir else Path.cwd() / "config"
        self.config_dir.mkdir(exist_ok=True)
        
        self._config_cache: Dict[str, SharedConfig] = {}
    
    def load_config(self, 
                   config_name: str = "default",
                   environment: Optional[ConfigEnvironment] = None) -> SharedConfig:
        """Load configuration from file or environment."""
        
        # Check cache first
        cache_key = f"{config_name}_{environment.value if environment else 'default'}"
        if cache_key in self._config_cache:
            return self._config_cache[cache_key]
        
        # Try to load from file
        config_file = self.config_dir / f"{config_name}.yaml"
        if config_file.exists():
            config = self._load_from_file(config_file)
        else:
            config = SharedConfig()
        
        # Override with environment-specific settings
        if environment:
            config.environment = environment
            env_config_file = self.config_dir / f"{config_name}_{environment.value}.yaml"
            if env_config_file.exists():
                env_config = self._load_from_file(env_config_file)
                config = self._merge_configs(config, env_config)
        
        # Override with environment variables
        config = self._apply_env_overrides(config)
        
        # Cache and return
        self._config_cache[cache_key] = config
        return config
    
    def save_config(self, config: SharedConfig, config_name: str = "default"):
        """Save configuration to file."""
        config_file = self.config_dir / f"{config_name}.yaml"
        
        with open(config_file, 'w') as f:
            yaml.dump(config.to_dict(), f, default_flow_style=False)
    
    def _load_from_file(self, config_file: Path) -> SharedConfig:
        """Load configuration from YAML file."""
        with open(config_file, 'r') as f:
            data = yaml.safe_load(f)
        
        return SharedConfig.from_dict(data)
    
    def _merge_configs(self, base: SharedConfig, override: SharedConfig) -> SharedConfig:
        """Merge two configurations, with override taking precedence."""
        merged_dict = base.to_dict()
        override_dict = override.to_dict()
        
        # Deep merge dictionaries
        def deep_merge(d1, d2):
            for key, value in d2.items():
                if key in d1 and isinstance(d1[key], dict) and isinstance(value, dict):
                    deep_merge(d1[key], value)
                else:
                    d1[key] = value
        
        deep_merge(merged_dict, override_dict)
        return SharedConfig.from_dict(merged_dict)
    
    def _apply_env_overrides(self, config: SharedConfig) -> SharedConfig:
        """Apply environment variable overrides."""
        
        # Override environment
        if os.getenv('CONFIG_ENVIRONMENT'):
            config.environment = ConfigEnvironment(os.getenv('CONFIG_ENVIRONMENT'))
        
        # Override debug mode
        if os.getenv('DEBUG'):
            config.debug = os.getenv('DEBUG').lower() == 'true'
        
        # Override log level
        if os.getenv('LOG_LEVEL'):
            config.log_level = os.getenv('LOG_LEVEL')
        
        # Override workspace path
        if os.getenv('WORKSPACE_PATH'):
            config.workspace_path = os.getenv('WORKSPACE_PATH')
        
        # Override OpenAI API key for all OpenAI models
        if os.getenv('OPENAI_API_KEY'):
            for model_config in config.models.values():
                if model_config.provider == ModelProvider.OPENAI:
                    model_config.api_key = os.getenv('OPENAI_API_KEY')
        
        return config


# Global configuration manager instance
config_manager = ConfigManager()


def get_config(config_name: str = "default", 
               environment: Optional[ConfigEnvironment] = None) -> SharedConfig:
    """Get configuration with caching."""
    return config_manager.load_config(config_name, environment)


def create_default_config() -> SharedConfig:
    """Create a default configuration."""
    return SharedConfig()


def validate_config(config: SharedConfig) -> bool:
    """Validate configuration and raise exceptions if invalid."""
    errors = config.validate()
    
    if errors:
        error_msg = "Configuration validation failed:\n" + "\n".join(f"- {error}" for error in errors)
        raise ValueError(error_msg)
    
    return True


# Export main classes and functions
__all__ = [
    'SharedConfig', 'ConfigManager', 'ConfigEnvironment', 'ModelProvider',
    'ModelConfig', 'AgentConfig', 'RAGConfig', 'AnalyticsConfig',
    'get_config', 'create_default_config', 'validate_config', 'config_manager'
]
