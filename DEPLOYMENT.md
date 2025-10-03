# AI Gatekeeper Deployment Guide

This guide covers deploying AI Gatekeeper to production using Docker and Kubernetes.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Docker Deployment](#docker-deployment)
- [Kubernetes Deployment](#kubernetes-deployment)
- [Configuration](#configuration)
- [Monitoring](#monitoring)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### Required
- Docker 20.10+
- Docker Compose 2.0+ (for local deployment)
- Kubernetes 1.24+ (for production)
- PostgreSQL 15+
- Redis 7+
- OpenAI API Key

### Recommended
- Kubernetes cluster (GKE, EKS, or AKS)
- Ingress controller (nginx-ingress)
- Cert-manager for TLS
- Monitoring stack (Prometheus, Grafana)
- Tracing backend (Jaeger, Tempo, or Datadog)

## Docker Deployment

### Local Development

1. **Set up environment variables:**

```bash
cp .env.example .env
# Edit .env with your configuration
```

2. **Start services:**

```bash
docker-compose -f docker-compose.dev.yml up -d
```

3. **Check health:**

```bash
curl http://localhost:5000/health
```

4. **View logs:**

```bash
docker-compose -f docker-compose.dev.yml logs -f app
```

### Production with Docker Compose

1. **Configure secrets:**

```bash
# Set environment variables
export OPENAI_API_KEY="your-openai-api-key"
export JWT_SECRET_KEY="your-jwt-secret-min-32-chars"
export SECRET_KEY="your-flask-secret-min-24-chars"
export ADMIN_API_KEY="your-admin-key-min-32-chars"
```

2. **Build and deploy:**

```bash
docker-compose up -d
```

3. **Scale application:**

```bash
docker-compose up -d --scale app=3
```

## Kubernetes Deployment

### 1. Create Namespace

```bash
kubectl apply -f k8s/namespace.yaml
```

### 2. Configure Secrets

**Important:** Update secrets before deploying!

```bash
# Create secrets from environment variables
kubectl create secret generic ai-gatekeeper-secrets \
  --from-literal=openai-api-key=$OPENAI_API_KEY \
  --from-literal=jwt-secret-key=$JWT_SECRET_KEY \
  --from-literal=secret-key=$SECRET_KEY \
  --from-literal=admin-api-key=$ADMIN_API_KEY \
  --from-literal=database-url=$DATABASE_URL \
  -n ai-gatekeeper
```

Or use the template:

```bash
# Edit k8s/secrets.yaml with your actual values
kubectl apply -f k8s/secrets.yaml
```

### 3. Deploy Database Layer

```bash
# Deploy PostgreSQL
kubectl apply -f k8s/postgres-statefulset.yaml

# Deploy Redis
kubectl apply -f k8s/redis-deployment.yaml

# Create PVC for ChromaDB
kubectl apply -f k8s/pvc.yaml
```

### 4. Deploy Application

```bash
# Deploy services
kubectl apply -f k8s/service.yaml

# Deploy application
kubectl apply -f k8s/deployment.yaml

# Deploy autoscaling
kubectl apply -f k8s/hpa.yaml
```

### 5. Configure Ingress

```bash
# Update k8s/ingress.yaml with your domain
kubectl apply -f k8s/ingress.yaml
```

### 6. Verify Deployment

```bash
# Check pod status
kubectl get pods -n ai-gatekeeper

# Check services
kubectl get svc -n ai-gatekeeper

# Check ingress
kubectl get ingress -n ai-gatekeeper

# View logs
kubectl logs -f deployment/ai-gatekeeper -n ai-gatekeeper

# Check health
kubectl exec -it deployment/ai-gatekeeper -n ai-gatekeeper -- \
  curl http://localhost:5000/api/monitoring/health
```

## Configuration

### Environment Variables

#### Required
- `OPENAI_API_KEY`: OpenAI API key (must start with `sk-`)
- `JWT_SECRET_KEY`: JWT signing secret (min 32 chars)
- `SECRET_KEY`: Flask session secret (min 24 chars)
- `DATABASE_URL`: PostgreSQL connection string

#### Optional
- `ADMIN_API_KEY`: Admin API key (default: auto-generated)
- `ENVIRONMENT`: `development` or `production` (default: `development`)
- `LOG_LEVEL`: `DEBUG`, `INFO`, `WARNING`, `ERROR` (default: `INFO`)
- `DB_POOL_SIZE`: Database connection pool size (default: `20`)
- `DB_MAX_OVERFLOW`: Max overflow connections (default: `10`)
- `OTEL_ENABLED`: Enable distributed tracing (default: `true`)
- `OTEL_EXPORTER_OTLP_ENDPOINT`: OTLP endpoint (default: `http://localhost:4317`)

### Database Pool Monitoring

The system automatically monitors database connection pool health:

- **Healthy**: < 70% utilization
- **Warning**: 70-90% utilization (logged)
- **Critical**: > 90% utilization (alert triggered)

Metrics are collected every 60 seconds and available at:
```
GET /api/monitoring/db-pool-status
```

## Monitoring

### Health Checks

```bash
# Basic health
curl http://localhost:5000/health

# Comprehensive health (includes all components)
curl http://localhost:5000/api/monitoring/health

# Metrics
curl http://localhost:5000/api/monitoring/metrics

# Database pool status
curl http://localhost:5000/api/monitoring/db-pool-status
```

### Distributed Tracing

If OpenTelemetry is enabled, traces are sent to the configured OTLP endpoint:

```bash
# Set OTLP endpoint
export OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger:4317

# View traces in Jaeger
# Navigate to http://jaeger:16686
```

### Prometheus Metrics

Metrics are exposed in Prometheus format:

```bash
curl http://localhost:5000/api/monitoring/metrics?format=prometheus
```

## Scaling

### Horizontal Scaling (Kubernetes)

The HPA automatically scales based on CPU and memory:

```yaml
minReplicas: 3
maxReplicas: 10
targetCPUUtilizationPercentage: 70
targetMemoryUtilizationPercentage: 80
```

### Manual Scaling

```bash
# Scale deployment
kubectl scale deployment ai-gatekeeper --replicas=5 -n ai-gatekeeper

# Or with Docker Compose
docker-compose up -d --scale app=5
```

## Troubleshooting

### Application Won't Start

1. **Check environment validation:**
```bash
kubectl logs deployment/ai-gatekeeper -n ai-gatekeeper | grep "validation"
```

2. **Common issues:**
   - Missing OPENAI_API_KEY
   - Invalid secret format (check minimum lengths)
   - Database connection failed

### Database Pool Exhaustion

1. **Check pool status:**
```bash
curl http://localhost:5000/api/monitoring/db-pool-status
```

2. **Increase pool size:**
```bash
# Update environment
DB_POOL_SIZE=30 DB_MAX_OVERFLOW=20
```

3. **Scale application horizontally:**
```bash
kubectl scale deployment ai-gatekeeper --replicas=5 -n ai-gatekeeper
```

### High Memory Usage

1. **Check metrics:**
```bash
kubectl top pods -n ai-gatekeeper
```

2. **Increase resource limits:**
```yaml
resources:
  limits:
    memory: "4Gi"
    cpu: "2000m"
```

### Tracing Not Working

1. **Verify OTLP endpoint:**
```bash
echo $OTEL_EXPORTER_OTLP_ENDPOINT
```

2. **Check tracing enabled:**
```bash
echo $OTEL_ENABLED  # Should be "true"
```

3. **View application logs:**
```bash
kubectl logs deployment/ai-gatekeeper -n ai-gatekeeper | grep "tracing"
```

## Security Best Practices

1. **Never commit secrets to version control**
2. **Use Kubernetes secrets or external secret managers**
3. **Rotate secrets regularly**
4. **Enable TLS/SSL in production**
5. **Use network policies to restrict traffic**
6. **Run as non-root user (already configured)**
7. **Scan images for vulnerabilities**

## Backup and Recovery

### Database Backup

```bash
# PostgreSQL backup
kubectl exec -it postgres-0 -n ai-gatekeeper -- \
  pg_dump -U postgres ai_gatekeeper > backup.sql

# Restore
kubectl exec -i postgres-0 -n ai-gatekeeper -- \
  psql -U postgres ai_gatekeeper < backup.sql
```

### Vector Store Backup

```bash
# Backup ChromaDB persistent volume
kubectl cp ai-gatekeeper/ai-gatekeeper-<pod-id>:/app/chroma_data ./chroma_backup

# Restore
kubectl cp ./chroma_backup ai-gatekeeper/ai-gatekeeper-<pod-id>:/app/chroma_data
```

## Updates and Rollbacks

### Rolling Update

```bash
# Update image
kubectl set image deployment/ai-gatekeeper \
  ai-gatekeeper=ai-gatekeeper:v2.0.0 -n ai-gatekeeper

# Watch rollout
kubectl rollout status deployment/ai-gatekeeper -n ai-gatekeeper
```

### Rollback

```bash
# Rollback to previous version
kubectl rollout undo deployment/ai-gatekeeper -n ai-gatekeeper

# Rollback to specific revision
kubectl rollout undo deployment/ai-gatekeeper --to-revision=3 -n ai-gatekeeper
```

## Performance Tuning

### Database Optimization

```bash
# Increase connection pool
DB_POOL_SIZE=30
DB_MAX_OVERFLOW=20
DB_POOL_RECYCLE=1800  # 30 minutes
```

### Worker Configuration

```bash
# For production, use Gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 \
  --timeout 120 \
  --max-requests 1000 \
  --max-requests-jitter 50 \
  app:app
```

## Support

For issues and questions:
- GitHub Issues: https://github.com/your-org/ai-gatekeeper/issues
- Documentation: See README.md and inline code documentation
