"""
Enhanced Monitoring and Analytics System for AI Gatekeeper
Provides real-time metrics, health monitoring, and performance tracking
"""

import time
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import defaultdict, deque
import threading
from flask import Blueprint, jsonify, request

@dataclass
class MetricPoint:
    """Single metric data point."""
    timestamp: float
    value: float
    labels: Dict[str, str] = field(default_factory=dict)

@dataclass
class SystemHealth:
    """System health status."""
    status: str  # healthy, degraded, unhealthy
    components: Dict[str, bool]
    uptime: float
    last_check: float
    issues: List[str] = field(default_factory=list)

class MetricsCollector:
    """Lightweight metrics collection system."""
    
    def __init__(self, max_points: int = 1000):
        self.max_points = max_points
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_points))
        self.counters: Dict[str, float] = defaultdict(float)
        self.gauges: Dict[str, float] = defaultdict(float)
        self.histograms: Dict[str, List[float]] = defaultdict(list)
        self.lock = threading.Lock()
        
    def counter(self, name: str, value: float = 1.0, labels: Dict[str, str] = None):
        """Increment a counter metric."""
        with self.lock:
            key = self._metric_key(name, labels)
            self.counters[key] += value
            self._add_point(name, self.counters[key], labels)
    
    def gauge(self, name: str, value: float, labels: Dict[str, str] = None):
        """Set a gauge metric."""
        with self.lock:
            key = self._metric_key(name, labels)
            self.gauges[key] = value
            self._add_point(name, value, labels)
    
    def histogram(self, name: str, value: float, labels: Dict[str, str] = None):
        """Record a histogram value."""
        with self.lock:
            key = self._metric_key(name, labels)
            self.histograms[key].append(value)
            # Keep only last 100 values for efficiency
            if len(self.histograms[key]) > 100:
                self.histograms[key] = self.histograms[key][-100:]
    
    def timer(self, name: str, labels: Dict[str, str] = None):
        """Context manager for timing operations."""
        return TimerContext(self, name, labels)
    
    def _add_point(self, name: str, value: float, labels: Dict[str, str] = None):
        """Add a metric point."""
        point = MetricPoint(
            timestamp=time.time(),
            value=value,
            labels=labels or {}
        )
        self.metrics[name].append(point)
    
    def _metric_key(self, name: str, labels: Dict[str, str] = None) -> str:
        """Generate metric key from name and labels."""
        if not labels:
            return name
        label_str = "_".join(f"{k}_{v}" for k, v in sorted(labels.items()))
        return f"{name}_{label_str}"
    
    def get_metrics(self, name: str = None, since: float = None) -> Dict[str, Any]:
        """Get metrics data."""
        with self.lock:
            if name:
                return self._format_metric(name, since)
            
            return {
                metric_name: self._format_metric(metric_name, since)
                for metric_name in self.metrics.keys()
            }
    
    def _format_metric(self, name: str, since: float = None) -> Dict[str, Any]:
        """Format metric data for response."""
        points = list(self.metrics[name])
        
        if since:
            points = [p for p in points if p.timestamp >= since]
        
        if not points:
            return {"points": [], "latest": None, "count": 0}
        
        return {
            "points": [
                {
                    "timestamp": p.timestamp,
                    "value": p.value,
                    "labels": p.labels
                }
                for p in points
            ],
            "latest": {
                "timestamp": points[-1].timestamp,
                "value": points[-1].value,
                "labels": points[-1].labels
            },
            "count": len(points)
        }

class TimerContext:
    """Timer context manager."""
    
    def __init__(self, collector: MetricsCollector, name: str, labels: Dict[str, str] = None):
        self.collector = collector
        self.name = name
        self.labels = labels
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration = time.time() - self.start_time
            self.collector.histogram(f"{self.name}_duration", duration, self.labels)

class HealthChecker:
    """System health monitoring."""
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics = metrics_collector
        self.start_time = time.time()
        self.component_checks = {}
        
    def register_component(self, name: str, check_func):
        """Register a component health check."""
        self.component_checks[name] = check_func
    
    def check_health(self) -> SystemHealth:
        """Perform health check."""
        issues = []
        component_status = {}
        
        # Check each registered component
        for name, check_func in self.component_checks.items():
            try:
                is_healthy = check_func()
                component_status[name] = is_healthy
                if not is_healthy:
                    issues.append(f"Component {name} is unhealthy")
            except Exception as e:
                component_status[name] = False
                issues.append(f"Component {name} check failed: {str(e)}")
        
        # Determine overall status
        if not issues:
            status = "healthy"
        elif len(issues) <= len(component_status) // 2:
            status = "degraded"
        else:
            status = "unhealthy"
        
        health = SystemHealth(
            status=status,
            components=component_status,
            uptime=time.time() - self.start_time,
            last_check=time.time(),
            issues=issues
        )
        
        # Record health metrics
        self.metrics.gauge("system_health", 1.0 if status == "healthy" else 0.0)
        self.metrics.gauge("system_uptime", health.uptime)
        self.metrics.gauge("component_count", len(component_status))
        self.metrics.gauge("healthy_components", sum(component_status.values()))
        
        return health

class PerformanceTracker:
    """Track AI Gatekeeper performance metrics."""
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics = metrics_collector
        
    def track_request(self, request_type: str, success: bool, duration: float, 
                     confidence: float = None, risk: float = None):
        """Track a support request."""
        labels = {"type": request_type, "success": str(success)}
        
        self.metrics.counter("requests_total", 1.0, labels)
        self.metrics.histogram("request_duration", duration, labels)
        
        if confidence is not None:
            self.metrics.histogram("confidence_score", confidence, labels)
        
        if risk is not None:
            self.metrics.histogram("risk_score", risk, labels)
    
    def track_agent_execution(self, agent_type: str, success: bool, duration: float):
        """Track agent execution."""
        labels = {"agent": agent_type, "success": str(success)}
        
        self.metrics.counter("agent_executions", 1.0, labels)
        self.metrics.histogram("agent_duration", duration, labels)
    
    def track_escalation(self, reason: str):
        """Track escalation."""
        labels = {"reason": reason}
        self.metrics.counter("escalations_total", 1.0, labels)
    
    def track_feedback(self, outcome: str, rating: int = None, confidence_accuracy: float = None, processing_time: float = None):
        """Track feedback submission and learning metrics."""
        labels = {"outcome": outcome}
        
        self.metrics.counter("feedback_total", 1.0, labels)
        
        if rating is not None:
            self.metrics.histogram("feedback_rating", rating, labels)
        
        if confidence_accuracy is not None:
            self.metrics.histogram("confidence_accuracy", confidence_accuracy, labels)
        
        if processing_time is not None:
            self.metrics.histogram("feedback_processing_time", processing_time, labels)
    
    def get_performance_summary(self, hours: int = 1) -> Dict[str, Any]:
        """Get performance summary for the last N hours."""
        since = time.time() - (hours * 3600)
        
        # Get recent metrics
        requests = self.metrics.get_metrics("requests_total", since)
        durations = self.metrics.get_metrics("request_duration", since)
        escalations = self.metrics.get_metrics("escalations_total", since)
        
        # Calculate summary stats
        total_requests = len(requests.get("points", []))
        if total_requests == 0:
            return {"period_hours": hours, "no_data": True}
        
        successful_requests = len([
            p for p in requests.get("points", [])
            if p.get("labels", {}).get("success") == "True"
        ])
        
        avg_duration = sum(p["value"] for p in durations.get("points", [])) / len(durations.get("points", [])) if durations.get("points") else 0
        
        return {
            "period_hours": hours,
            "total_requests": total_requests,
            "successful_requests": successful_requests,
            "success_rate": successful_requests / total_requests if total_requests > 0 else 0,
            "avg_response_time": avg_duration,
            "total_escalations": len(escalations.get("points", [])),
            "escalation_rate": len(escalations.get("points", [])) / total_requests if total_requests > 0 else 0,
            "requests_per_hour": total_requests / hours
        }

# Flask Blueprint for monitoring endpoints
monitoring_bp = Blueprint('monitoring', __name__, url_prefix='/api/monitoring')

# Global instances (initialized by main app)
metrics_collector = MetricsCollector()
health_checker = HealthChecker(metrics_collector)
performance_tracker = PerformanceTracker(metrics_collector)

@monitoring_bp.route('/health', methods=['GET'])
def health_endpoint():
    """Health check endpoint."""
    health = health_checker.check_health()
    
    status_code = 200
    if health.status == "degraded":
        status_code = 200  # Still OK, but with warnings
    elif health.status == "unhealthy":
        status_code = 503  # Service unavailable
    
    return jsonify({
        "status": health.status,
        "timestamp": datetime.now().isoformat(),
        "uptime": health.uptime,
        "components": health.components,
        "issues": health.issues
    }), status_code

@monitoring_bp.route('/metrics', methods=['GET'])
def metrics_endpoint():
    """Metrics endpoint (Prometheus compatible)."""
    format_type = request.args.get('format', 'json')
    since = request.args.get('since', type=float)
    
    if format_type == 'prometheus':
        return _format_prometheus_metrics(since)
    
    # Default JSON format
    metrics_data = metrics_collector.get_metrics(since=since)
    
    return jsonify({
        "timestamp": datetime.now().isoformat(),
        "metrics": metrics_data
    })

@monitoring_bp.route('/performance', methods=['GET'])
def performance_endpoint():
    """Performance summary endpoint."""
    hours = request.args.get('hours', default=1, type=int)
    summary = performance_tracker.get_performance_summary(hours)
    
    return jsonify({
        "timestamp": datetime.now().isoformat(),
        "performance": summary
    })

@monitoring_bp.route('/dashboard', methods=['GET'])
def dashboard_endpoint():
    """Dashboard data endpoint."""
    health = health_checker.check_health()
    performance = performance_tracker.get_performance_summary(24)  # 24 hours
    
    return jsonify({
        "timestamp": datetime.now().isoformat(),
        "health": {
            "status": health.status,
            "uptime": health.uptime,
            "components": health.components,
            "issues": health.issues
        },
        "performance": performance
    })

@monitoring_bp.route('/feedback-analytics', methods=['GET'])
def feedback_analytics_endpoint():
    """Feedback analytics endpoint."""
    hours = request.args.get('hours', default=24, type=int)
    since = time.time() - (hours * 3600)
    
    # Get feedback metrics
    feedback_metrics = metrics_collector.get_metrics("feedback_total", since)
    rating_metrics = metrics_collector.get_metrics("feedback_rating", since)
    accuracy_metrics = metrics_collector.get_metrics("confidence_accuracy", since)
    
    # Calculate analytics
    total_feedback = len(feedback_metrics.get("points", []))
    
    # Group by outcome
    outcome_counts = {}
    for point in feedback_metrics.get("points", []):
        outcome = point.get("labels", {}).get("outcome", "unknown")
        outcome_counts[outcome] = outcome_counts.get(outcome, 0) + 1
    
    # Calculate average rating
    ratings = [p["value"] for p in rating_metrics.get("points", [])]
    avg_rating = sum(ratings) / len(ratings) if ratings else 0
    
    # Calculate confidence accuracy
    accuracies = [p["value"] for p in accuracy_metrics.get("points", [])]
    avg_accuracy = sum(accuracies) / len(accuracies) if accuracies else 0
    
    return jsonify({
        "timestamp": datetime.now().isoformat(),
        "period_hours": hours,
        "feedback_analytics": {
            "total_feedback": total_feedback,
            "outcomes": outcome_counts,
            "average_rating": round(avg_rating, 2),
            "average_confidence_accuracy": round(avg_accuracy, 3),
            "resolution_rate": outcome_counts.get("resolved", 0) / total_feedback if total_feedback > 0 else 0
        }
    })

def _format_prometheus_metrics(since: float = None) -> str:
    """Format metrics in Prometheus format."""
    lines = []
    metrics_data = metrics_collector.get_metrics(since=since)
    
    for metric_name, metric_data in metrics_data.items():
        latest = metric_data.get("latest")
        if latest:
            labels_str = ""
            if latest.get("labels"):
                label_pairs = [f'{k}="{v}"' for k, v in latest["labels"].items()]
                labels_str = "{" + ",".join(label_pairs) + "}"
            
            lines.append(f'{metric_name.replace("-", "_")}{labels_str} {latest["value"]}')
    
    return "\n".join(lines)

def initialize_health_checks(support_processor, solution_generator, search_system):
    """Initialize health checks for system components."""
    
    def check_support_processor():
        return support_processor is not None and support_processor.agent_manager is not None
    
    def check_solution_generator():
        return solution_generator is not None
    
    def check_search_system():
        return search_system is not None
    
    def check_ai_service():
        # Simple AI service check - could ping OpenAI API
        try:
            import openai
            return True
        except:
            return False
    
    health_checker.register_component("support_processor", check_support_processor)
    health_checker.register_component("solution_generator", check_solution_generator)
    health_checker.register_component("search_system", check_search_system)
    health_checker.register_component("ai_service", check_ai_service)

# Decorator for automatic metrics collection
def track_execution(operation_name: str):
    """Decorator to automatically track execution metrics."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            with metrics_collector.timer(operation_name):
                try:
                    result = func(*args, **kwargs)
                    metrics_collector.counter(f"{operation_name}_success", 1.0)
                    return result
                except Exception as e:
                    metrics_collector.counter(f"{operation_name}_error", 1.0)
                    raise
        return wrapper
    return decorator

# Export for use in main application
__all__ = [
    'metrics_collector',
    'health_checker', 
    'performance_tracker',
    'monitoring_bp',
    'initialize_health_checks',
    'track_execution'
]