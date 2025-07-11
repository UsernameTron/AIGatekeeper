# 🛡️ AI Gatekeeper System

An intelligent support ticketing automation system that provides automated technical support with intelligent escalation to human experts.

## 🎯 Overview

The AI Gatekeeper is a complete support automation platform that provides:

- **Intelligent Support Request Evaluation** using TriageAgent
- **Automated Solution Generation** via enhanced ResearchAgent
- **Knowledge Base Management** with vector database integration
- **Slack Integration** for seamless communication
- **Continuous Learning** from user feedback and resolution outcomes

## 🏗️ Architecture

```
AI Gatekeeper System
├── Core Engine
│   ├── SupportRequestProcessor     # Main request processing
│   └── SolutionGenerator          # AI-powered solution creation
├── Knowledge Base
│   ├── KnowledgeBaseManager       # Vector database management
│   └── 10 Support Categories      # Structured knowledge storage
├── Integrations
│   ├── Flask API Routes           # RESTful API endpoints
│   └── Slack Connector           # Real-time Slack integration
└── Testing Framework
    └── Comprehensive Test Suite   # Full system validation
```

## ✨ Key Features

### Intelligent Request Processing
- **Confidence Scoring**: AI evaluates its ability to solve each request
- **Risk Assessment**: Analyzes potential impact of automated solutions
- **Smart Escalation**: Routes complex issues to appropriate human experts
- **Priority Management**: Automatic prioritization based on content and context

### Knowledge Base Management
- **Vector Database Storage**: Semantic search across support documentation
- **10 Knowledge Categories**: Technical solutions, troubleshooting, configuration, etc.
- **Continuous Learning**: Knowledge base updates from successful resolutions
- **Multi-format Support**: Text, audio, and interactive content

### Slack Integration
- **Real-time Processing**: Immediate response to support requests
- **Rich Message Formatting**: Interactive buttons and formatted responses
- **Expert Handoff**: Seamless escalation with full context

### Enhanced Monitoring & Analytics
- **Real-time Metrics**: Request rates, response times, success rates
- **Health Monitoring**: Component status and system uptime tracking
- **Performance Analytics**: Confidence calibration and escalation patterns
- **Prometheus Integration**: Compatible with standard monitoring tools

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- OpenAI/Helpdesk API key
- Vector database (ChromaDB)
- Optional: Slack workspace and bot token

### Installation

1. **Install dependencies**:
```bash
pip install -r requirements.txt
```

2. **Set environment variables**:
```bash
export OPENAI_API_KEY="your-openai-api-key"
export SLACK_BOT_TOKEN="xoxb-your-slack-bot-token"  # Optional
```

3. **Run the test suite**:
```bash
python3 tests/test_ai_gatekeeper.py
```

4. **Start the AI Gatekeeper**:
```bash
python3 app.py
```

The AI Gatekeeper endpoints will be available at `/api/support/*`

### Configuration

Add to your environment variables:
```bash
# Optional: Slack integration
export SLACK_BOT_TOKEN="xoxb-your-slack-bot-token"

# Optional: AI Gatekeeper thresholds
export SUPPORT_CONFIDENCE_THRESHOLD=0.8
export SUPPORT_RISK_THRESHOLD=0.3
```

## 📡 API Endpoints

### Core Support API

#### Evaluate Support Request
```http
POST /api/support/evaluate
Content-Type: application/json

{
  "message": "My application keeps crashing when I try to save files",
  "context": {
    "user_level": "intermediate",
    "system": "Windows 10",
    "priority": "medium"
  }
}
```

**Response** (Automated Resolution):
```json
{
  "action": "automated_resolution",
  "request_id": "req_12345",
  "solution": {
    "title": "Application Crash Resolution",
    "steps": [...],
    "estimated_time": "10-15 minutes"
  },
  "confidence": 0.89,
  "status": "automated_resolution"
}
```

**Response** (Escalation):
```json
{
  "action": "escalate_to_human",
  "request_id": "req_12345",
  "analysis": {
    "confidence_score": 0.65,
    "risk_score": 0.45,
    "escalation_reason": "Complex system integration issue"
  },
  "enriched_context": {...},
  "status": "escalated"
}
```

#### Generate Detailed Solution
```http
POST /api/support/generate-solution
Content-Type: application/json

{
  "issue_description": "Password reset not working",
  "context": {
    "user_level": "beginner"
  },
  "solution_type": "step_by_step"
}
```

#### Check Request Status
```http
GET /api/support/status/{request_id}
```

#### Slack Integration
```http
POST /api/support/slack-integration
Content-Type: application/json

{
  "channel": "C1234567890",
  "user": "U0987654321",
  "message": "Need help with login issues",
  "context": {
    "user_level": "beginner"
  }
}
```

### Additional Endpoints

- `GET /api/support/active-requests` - List all active requests
- `POST /api/support/feedback` - Submit solution feedback
- `GET /api/support/health` - System health check

### Monitoring and Analytics Endpoints

- `GET /api/monitoring/health` - Detailed system health with component status
- `GET /api/monitoring/metrics` - Real-time metrics data (JSON or Prometheus format)
- `GET /api/monitoring/performance` - Performance summary and statistics
- `GET /api/monitoring/dashboard` - Combined dashboard data

## 🧪 Testing

### Run Full Test Suite
```bash
python3 tests/test_ai_gatekeeper.py
```

### Run Specific Test Classes
```bash
# Test support request processor
python3 tests/test_ai_gatekeeper.py --single TestSupportRequestProcessor

# Test solution generator
python3 tests/test_ai_gatekeeper.py --single TestSolutionGenerator

# Test Slack integration
python3 tests/test_ai_gatekeeper.py --single TestSlackIntegration
```

### Manual Testing Examples

#### Test Automated Resolution
```bash
curl -X POST http://localhost:5000/api/support/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "message": "How do I reset my password?",
    "context": {"user_level": "beginner"}
  }'
```

#### Test Escalation
```bash
curl -X POST http://localhost:5000/api/support/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Critical database corruption affecting all users",
    "context": {"user_level": "beginner", "priority": "critical"}
  }'
```

## 🔧 Configuration

### Confidence and Risk Thresholds

Adjust in `core/support_request_processor.py`:
```python
# High confidence + low risk = automated resolution
confidence_threshold = 0.8  # 80% confidence required
risk_threshold = 0.3         # Max 30% risk acceptable
```

### Knowledge Base Categories

Modify categories in `knowledge/knowledge_base_setup.py`:
```python
SUPPORT_KNOWLEDGE_CATEGORIES = [
    'technical_solutions',
    'troubleshooting_guides',
    'configuration_guides',
    # Add custom categories here
]
```

### Slack Message Templates

Customize in `integrations/slack_integration.py`:
```python
self.message_templates = {
    'automated_solution': 'Your custom template here...',
    'escalation_notification': 'Your escalation template...'
}
```

## 📊 Monitoring and Analytics

### Built-in Metrics

The system tracks:
- **Resolution Success Rate**: Percentage of successfully automated resolutions
- **Confidence Calibration**: How well confidence scores predict success
- **Escalation Patterns**: Common reasons for human escalation
- **Response Times**: Time from request to resolution
- **User Satisfaction**: Feedback scores and follow-up requests

### Access Analytics

Enhanced monitoring and analytics endpoints:
```bash
# System health with component status
curl http://localhost:5000/api/monitoring/health

# Real-time metrics (JSON format)
curl http://localhost:5000/api/monitoring/metrics

# Prometheus format metrics
curl http://localhost:5000/api/monitoring/metrics?format=prometheus

# Performance summary (last 24 hours)
curl http://localhost:5000/api/monitoring/performance?hours=24

# Complete dashboard data
curl http://localhost:5000/api/monitoring/dashboard

# Active support requests
curl http://localhost:5000/api/support/active-requests
```

## 🔍 Troubleshooting

### Common Issues

#### AI Gatekeeper Not Responding
```bash
# Check system health
curl http://localhost:5000/api/support/health

# Check system status
curl http://localhost:5000/health
```

#### Low Confidence Scores
- Check knowledge base content: Ensure sufficient training data
- Review user context: More detailed context improves confidence
- Adjust thresholds: Lower confidence threshold for more automation

#### Slack Integration Issues
- Verify `SLACK_BOT_TOKEN` environment variable
- Check bot permissions in Slack workspace
- Test with manual API calls first

### Debug Mode

Enable detailed logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Performance Optimization

For high-volume environments:
1. **Cache frequent solutions**: Implement Redis caching for common responses
2. **Batch processing**: Queue multiple requests for efficient processing
3. **Load balancing**: Scale across multiple instances
4. **Database optimization**: Tune vector database performance

## 🔒 Security Considerations

### Data Protection
- All support requests are processed in-memory
- Sensitive information is automatically redacted
- User context is anonymized in logs
- Knowledge base access is role-based

### Access Control
- API endpoints require authentication (configure as needed)
- Slack integration uses secure token-based authentication
- Admin functions require elevated permissions

## 🤝 Contributing

### Adding New Solution Types

1. **Extend SolutionType enum**:
```python
class SolutionType(Enum):
    STEP_BY_STEP = "step_by_step"
    TROUBLESHOOTING = "troubleshooting"
    YOUR_NEW_TYPE = "your_new_type"  # Add here
```

2. **Update solution generator logic**:
```python
def _determine_solution_type(self, issue_description: str):
    # Add detection logic for your new type
    if 'your_keywords' in issue_description.lower():
        return SolutionType.YOUR_NEW_TYPE
```

### Adding Knowledge Categories

1. **Update category list**:
```python
SUPPORT_KNOWLEDGE_CATEGORIES = [
    'existing_category',
    'your_new_category'  # Add here
]
```

2. **Create sample data**:
```python
def _generate_sample_knowledge_data(self):
    return {
        'your_new_category': [
            {
                'title': 'Sample Document',
                'content': 'Document content...',
                'keywords': ['relevant', 'keywords']
            }
        ]
    }
```

## 📄 License

This AI Gatekeeper system is built on the existing Unified AI Platform. Please refer to the main project for licensing terms.

## 🎉 Success Metrics

After implementation, you should see:
- **80%+ automation rate** for routine support requests
- **<30 second response time** for automated solutions
- **95%+ accuracy** for escalation decisions
- **Improved user satisfaction** due to faster resolution times
- **Reduced support team workload** allowing focus on complex issues

---

**🛡️ AI Gatekeeper: Intelligent Support Automation Ready for Production Use!**
