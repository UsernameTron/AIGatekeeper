"""
AI Model Usage and Cost Tracking
Monitors OpenAI API usage, token consumption, and estimated costs
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict
import logging


@dataclass
class ModelUsage:
    """Track model usage and costs."""
    model_name: str
    request_count: int = 0
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost: float = 0.0
    last_updated: datetime = field(default_factory=datetime.now)


class AIMetricsTracker:
    """Track AI model usage and costs."""

    # OpenAI pricing per 1M tokens (updated for 2024/2025)
    PRICING = {
        'gpt-4o': {'prompt': 2.50, 'completion': 10.00},
        'gpt-4o-mini': {'prompt': 0.150, 'completion': 0.600},
        'gpt-4-turbo': {'prompt': 10.00, 'completion': 30.00},
        'gpt-4': {'prompt': 30.00, 'completion': 60.00},
        'gpt-3.5-turbo': {'prompt': 0.50, 'completion': 1.50},
        'text-embedding-3-small': {'prompt': 0.020, 'completion': 0.0},
        'text-embedding-3-large': {'prompt': 0.130, 'completion': 0.0},
        'text-embedding-ada-002': {'prompt': 0.100, 'completion': 0.0},
    }

    def __init__(self, metrics_collector=None):
        self.metrics = metrics_collector
        self.usage_by_model: Dict[str, ModelUsage] = defaultdict(
            lambda: ModelUsage(model_name="unknown")
        )
        self.usage_by_agent: Dict[str, Dict[str, ModelUsage]] = defaultdict(
            lambda: defaultdict(lambda: ModelUsage(model_name="unknown"))
        )
        self.daily_costs: Dict[str, float] = {}  # date -> cost
        self.hourly_requests: Dict[str, int] = {}  # hour -> count

    def track_completion(self, model: str, prompt_tokens: int, completion_tokens: int,
                        agent_type: Optional[str] = None):
        """
        Track completion API call.

        Args:
            model: Model name
            prompt_tokens: Number of prompt tokens
            completion_tokens: Number of completion tokens
            agent_type: Optional agent type for breakdown
        """
        total_tokens = prompt_tokens + completion_tokens

        # Calculate cost
        pricing = self.PRICING.get(model, {'prompt': 0.0, 'completion': 0.0})
        cost = (
            (prompt_tokens / 1_000_000) * pricing['prompt'] +
            (completion_tokens / 1_000_000) * pricing['completion']
        )

        # Update model usage
        usage = self.usage_by_model[model]
        usage.model_name = model
        usage.request_count += 1
        usage.total_prompt_tokens += prompt_tokens
        usage.total_completion_tokens += completion_tokens
        usage.total_tokens += total_tokens
        usage.estimated_cost += cost
        usage.last_updated = datetime.now()

        # Update agent usage if provided
        if agent_type:
            agent_usage = self.usage_by_agent[agent_type][model]
            agent_usage.model_name = model
            agent_usage.request_count += 1
            agent_usage.total_prompt_tokens += prompt_tokens
            agent_usage.total_completion_tokens += completion_tokens
            agent_usage.total_tokens += total_tokens
            agent_usage.estimated_cost += cost
            agent_usage.last_updated = datetime.now()

        # Update daily cost
        today = datetime.now().strftime('%Y-%m-%d')
        self.daily_costs[today] = self.daily_costs.get(today, 0.0) + cost

        # Update hourly requests
        current_hour = datetime.now().strftime('%Y-%m-%d:%H')
        self.hourly_requests[current_hour] = self.hourly_requests.get(current_hour, 0) + 1

        # Track metrics if collector available
        if self.metrics:
            self.metrics.counter('ai_requests_total', 1.0, {'model': model})
            self.metrics.counter('ai_prompt_tokens_total', prompt_tokens, {'model': model})
            self.metrics.counter('ai_completion_tokens_total', completion_tokens, {'model': model})
            self.metrics.gauge('ai_estimated_cost_usd', cost, {'model': model})

            if agent_type:
                self.metrics.counter('ai_requests_by_agent', 1.0,
                                   {'agent': agent_type, 'model': model})

        logging.debug(f"AI usage tracked: {model} - {total_tokens} tokens, ${cost:.4f}")

    def track_embedding(self, model: str, tokens: int, agent_type: Optional[str] = None):
        """
        Track embedding API call.

        Args:
            model: Model name
            tokens: Number of tokens
            agent_type: Optional agent type for breakdown
        """
        # Calculate cost
        pricing = self.PRICING.get(model, {'prompt': 0.0, 'completion': 0.0})
        cost = (tokens / 1_000_000) * pricing['prompt']

        # Update model usage
        usage = self.usage_by_model[model]
        usage.model_name = model
        usage.request_count += 1
        usage.total_prompt_tokens += tokens
        usage.total_tokens += tokens
        usage.estimated_cost += cost
        usage.last_updated = datetime.now()

        # Update agent usage if provided
        if agent_type:
            agent_usage = self.usage_by_agent[agent_type][model]
            agent_usage.model_name = model
            agent_usage.request_count += 1
            agent_usage.total_prompt_tokens += tokens
            agent_usage.total_tokens += tokens
            agent_usage.estimated_cost += cost
            agent_usage.last_updated = datetime.now()

        # Update daily cost
        today = datetime.now().strftime('%Y-%m-%d')
        self.daily_costs[today] = self.daily_costs.get(today, 0.0) + cost

        # Update hourly requests
        current_hour = datetime.now().strftime('%Y-%m-%d:%H')
        self.hourly_requests[current_hour] = self.hourly_requests.get(current_hour, 0) + 1

        # Track metrics
        if self.metrics:
            self.metrics.counter('ai_embedding_requests_total', 1.0, {'model': model})
            self.metrics.counter('ai_embedding_tokens_total', tokens, {'model': model})
            self.metrics.gauge('ai_embedding_cost_usd', cost, {'model': model})

        logging.debug(f"AI embedding tracked: {model} - {tokens} tokens, ${cost:.4f}")

    def get_usage_summary(self, days: int = 7) -> Dict[str, Any]:
        """
        Get usage summary for the last N days.

        Args:
            days: Number of days to include in summary

        Returns:
            Dictionary with usage statistics
        """
        total_requests = sum(u.request_count for u in self.usage_by_model.values())
        total_tokens = sum(u.total_tokens for u in self.usage_by_model.values())
        total_cost = sum(u.estimated_cost for u in self.usage_by_model.values())

        # Calculate daily costs for period
        cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        recent_costs = {
            date: cost for date, cost in self.daily_costs.items()
            if date >= cutoff_date
        }

        # Model breakdown
        model_breakdown = {
            model: {
                'requests': usage.request_count,
                'prompt_tokens': usage.total_prompt_tokens,
                'completion_tokens': usage.total_completion_tokens,
                'total_tokens': usage.total_tokens,
                'estimated_cost_usd': round(usage.estimated_cost, 4),
                'avg_tokens_per_request': (
                    usage.total_tokens // usage.request_count
                    if usage.request_count > 0 else 0
                ),
                'cost_per_request_usd': round(
                    usage.estimated_cost / usage.request_count, 6
                ) if usage.request_count > 0 else 0
            }
            for model, usage in self.usage_by_model.items()
        }

        # Agent breakdown
        agent_breakdown = {
            agent: {
                model: {
                    'requests': usage.request_count,
                    'total_tokens': usage.total_tokens,
                    'estimated_cost_usd': round(usage.estimated_cost, 4)
                }
                for model, usage in models.items()
            }
            for agent, models in self.usage_by_agent.items()
        }

        return {
            'period_days': days,
            'total_requests': total_requests,
            'total_tokens': total_tokens,
            'total_cost_usd': round(total_cost, 2),
            'avg_tokens_per_request': total_tokens // total_requests if total_requests > 0 else 0,
            'avg_cost_per_request_usd': round(total_cost / total_requests, 6) if total_requests > 0 else 0,
            'daily_costs': {date: round(cost, 2) for date, cost in sorted(recent_costs.items())},
            'model_breakdown': model_breakdown,
            'agent_breakdown': agent_breakdown
        }

    def get_cost_alerts(self, daily_threshold_usd: float = 50.0) -> Dict[str, Any]:
        """
        Check for cost alerts.

        Args:
            daily_threshold_usd: Daily cost threshold for alerts

        Returns:
            Dictionary with alert information
        """
        today = datetime.now().strftime('%Y-%m-%d')
        today_cost = self.daily_costs.get(today, 0.0)

        alerts = []

        # Check daily threshold
        if today_cost > daily_threshold_usd:
            alerts.append({
                'severity': 'high',
                'message': f"Daily cost ${today_cost:.2f} exceeds threshold ${daily_threshold_usd:.2f}",
                'current_cost': today_cost,
                'threshold': daily_threshold_usd
            })

        # Check for unusual patterns (2x recent average)
        recent_days = sorted([
            (date, cost) for date, cost in self.daily_costs.items()
            if date >= (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        ])

        if len(recent_days) >= 3:
            avg_cost = sum(cost for _, cost in recent_days[:-1]) / (len(recent_days) - 1)
            if today_cost > avg_cost * 2:
                alerts.append({
                    'severity': 'medium',
                    'message': f"Today's cost ${today_cost:.2f} is 2x the recent average ${avg_cost:.2f}",
                    'current_cost': today_cost,
                    'average_cost': avg_cost
                })

        # Check for request spikes
        current_hour = datetime.now().strftime('%Y-%m-%d:%H')
        current_hour_requests = self.hourly_requests.get(current_hour, 0)

        if current_hour_requests > 100:
            alerts.append({
                'severity': 'medium',
                'message': f"High request rate this hour: {current_hour_requests} requests",
                'current_hour_requests': current_hour_requests
            })

        return {
            'has_alerts': len(alerts) > 0,
            'alert_count': len(alerts),
            'alerts': alerts,
            'today_cost_usd': round(today_cost, 2),
            'threshold_usd': daily_threshold_usd
        }

    def get_realtime_stats(self) -> Dict[str, Any]:
        """
        Get real-time statistics for the current hour.

        Returns:
            Dictionary with current hour statistics
        """
        current_hour = datetime.now().strftime('%Y-%m-%d:%H')
        hour_requests = self.hourly_requests.get(current_hour, 0)

        # Calculate cost for current hour (approximate from daily total)
        today = datetime.now().strftime('%Y-%m-%d')
        today_cost = self.daily_costs.get(today, 0.0)

        return {
            'current_hour': current_hour,
            'requests_this_hour': hour_requests,
            'estimated_cost_today_usd': round(today_cost, 2),
            'models_in_use': list(self.usage_by_model.keys())
        }


# Global AI metrics tracker instance
ai_metrics_tracker = AIMetricsTracker()


def init_ai_metrics(metrics_collector=None):
    """
    Initialize AI metrics tracker.

    Args:
        metrics_collector: Optional metrics collector instance
    """
    global ai_metrics_tracker
    ai_metrics_tracker = AIMetricsTracker(metrics_collector)
    logging.info("AI metrics tracker initialized")
    return ai_metrics_tracker
