# Kubernetes Deployment Manifests

This directory contains Kubernetes manifests for deploying AI Gatekeeper to production.

## Quick Start

```bash
# 1. Create namespace
kubectl apply -f namespace.yaml

# 2. Configure secrets (IMPORTANT: Update secrets.yaml first!)
kubectl apply -f secrets.yaml

# 3. Deploy infrastructure
kubectl apply -f pvc.yaml
kubectl apply -f postgres-statefulset.yaml
kubectl apply -f redis-deployment.yaml

# 4. Deploy application
kubectl apply -f service.yaml
kubectl apply -f deployment.yaml
kubectl apply -f hpa.yaml

# 5. Configure ingress (Update domain in ingress.yaml first!)
kubectl apply -f ingress.yaml

# 6. Verify
kubectl get pods -n ai-gatekeeper
kubectl get svc -n ai-gatekeeper
```

## Files Overview

| File | Description | Required |
|------|-------------|----------|
| `namespace.yaml` | Creates ai-gatekeeper namespace | ✅ Yes |
| `secrets.yaml` | Secrets and ConfigMap | ✅ Yes - **Update first!** |
| `deployment.yaml` | Main application deployment | ✅ Yes |
| `service.yaml` | ClusterIP services | ✅ Yes |
| `postgres-statefulset.yaml` | PostgreSQL database | ✅ Yes |
| `redis-deployment.yaml` | Redis cache | ✅ Yes |
| `pvc.yaml` | Persistent volume claims | ✅ Yes |
| `hpa.yaml` | Horizontal Pod Autoscaler | ⚠️ Optional |
| `ingress.yaml` | Ingress with TLS | ⚠️ Optional |

## Configuration Steps

### 1. Update Secrets

**IMPORTANT:** Before deploying, update `secrets.yaml`:

```yaml
stringData:
  openai-api-key: "sk-YOUR_ACTUAL_OPENAI_KEY"
  jwt-secret-key: "YOUR_SECURE_JWT_SECRET_MIN_32_CHARS"
  secret-key: "YOUR_FLASK_SECRET_MIN_24_CHARS"
  admin-api-key: "YOUR_ADMIN_KEY_MIN_32_CHARS"
  database-url: "postgresql://postgres:YOUR_PASSWORD@postgres-service:5432/ai_gatekeeper"
```

Or create from environment:

```bash
kubectl create secret generic ai-gatekeeper-secrets \
  --from-literal=openai-api-key=$OPENAI_API_KEY \
  --from-literal=jwt-secret-key=$JWT_SECRET_KEY \
  --from-literal=secret-key=$SECRET_KEY \
  --from-literal=admin-api-key=$ADMIN_API_KEY \
  --from-literal=database-url=$DATABASE_URL \
  -n ai-gatekeeper
```

### 2. Update Ingress

In `ingress.yaml`, replace:

```yaml
- host: ai-gatekeeper.yourdomain.com
```

With your actual domain.

### 3. Update Image

In `deployment.yaml`, update the image reference:

```yaml
image: your-registry/ai-gatekeeper:v1.0.0
```

## Deployment Order

**Must be deployed in this order:**

1. Namespace
2. Secrets and ConfigMap
3. PVC (for ChromaDB)
4. PostgreSQL StatefulSet
5. Redis Deployment
6. Services
7. Application Deployment
8. HPA (optional)
9. Ingress (optional)

## Verification

```bash
# Check all resources
kubectl get all -n ai-gatekeeper

# Check pod status
kubectl get pods -n ai-gatekeeper

# View logs
kubectl logs -f deployment/ai-gatekeeper -n ai-gatekeeper

# Check health
kubectl exec -it deployment/ai-gatekeeper -n ai-gatekeeper -- \
  curl http://localhost:5000/health

# Port forward for local testing
kubectl port-forward svc/ai-gatekeeper-service 5000:80 -n ai-gatekeeper
```

## Scaling

### Manual Scaling

```bash
kubectl scale deployment ai-gatekeeper --replicas=5 -n ai-gatekeeper
```

### Auto-scaling (HPA)

The HPA automatically scales 3-10 replicas based on:
- CPU utilization > 70%
- Memory utilization > 80%

```bash
# Watch autoscaling
kubectl get hpa -n ai-gatekeeper -w

# Describe HPA
kubectl describe hpa ai-gatekeeper-hpa -n ai-gatekeeper
```

## Troubleshooting

### Pods Not Starting

```bash
# Check events
kubectl describe pod <pod-name> -n ai-gatekeeper

# Check logs
kubectl logs <pod-name> -n ai-gatekeeper

# Common issues:
# - Missing secrets
# - Wrong image reference
# - Insufficient resources
```

### Database Connection Failed

```bash
# Check PostgreSQL pod
kubectl get pod postgres-0 -n ai-gatekeeper

# Check PostgreSQL logs
kubectl logs postgres-0 -n ai-gatekeeper

# Test connection from app pod
kubectl exec -it deployment/ai-gatekeeper -n ai-gatekeeper -- \
  psql $DATABASE_URL -c "SELECT 1"
```

### Health Check Failing

```bash
# Check health endpoint
kubectl exec -it deployment/ai-gatekeeper -n ai-gatekeeper -- \
  curl -v http://localhost:5000/api/monitoring/health

# Check application logs
kubectl logs -f deployment/ai-gatekeeper -n ai-gatekeeper | grep health
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

# Check rollout history
kubectl rollout history deployment/ai-gatekeeper -n ai-gatekeeper
```

## Resource Requirements

### Minimum (Development)
- **App**: 512Mi RAM, 500m CPU per pod
- **PostgreSQL**: 256Mi RAM, 250m CPU
- **Redis**: 128Mi RAM, 100m CPU
- **Total**: ~1Gi RAM, ~1 CPU (with 3 app replicas)

### Recommended (Production)
- **App**: 1Gi RAM, 1 CPU per pod (3-10 replicas)
- **PostgreSQL**: 1Gi RAM, 1 CPU
- **Redis**: 256Mi RAM, 500m CPU
- **Total**: 3-10Gi RAM, 3-10 CPUs

## Security

- ✅ Runs as non-root user (UID 1000)
- ✅ Security context configured
- ✅ Secrets stored in Kubernetes Secrets
- ✅ Network policies recommended (not included)
- ✅ TLS configured via Ingress

**Recommended additions:**
- Network policies to restrict traffic
- Pod security policies
- Image scanning
- Secret encryption at rest
- RBAC for service accounts

## Monitoring

The deployment includes Prometheus annotations:

```yaml
annotations:
  prometheus.io/scrape: "true"
  prometheus.io/port: "5000"
  prometheus.io/path: "/api/monitoring/metrics"
```

Metrics available at:
- `/api/monitoring/health` - Health status
- `/api/monitoring/metrics` - Metrics (JSON)
- `/api/monitoring/metrics?format=prometheus` - Prometheus format
- `/api/monitoring/db-pool-status` - Database pool status

## Clean Up

```bash
# Delete all resources
kubectl delete namespace ai-gatekeeper

# Or delete individually
kubectl delete -f ingress.yaml
kubectl delete -f hpa.yaml
kubectl delete -f deployment.yaml
kubectl delete -f service.yaml
kubectl delete -f redis-deployment.yaml
kubectl delete -f postgres-statefulset.yaml
kubectl delete -f pvc.yaml
kubectl delete -f secrets.yaml
kubectl delete -f namespace.yaml
```

**Warning:** This will delete all data including the database!

## Additional Resources

- Main documentation: [../DEPLOYMENT.md](../DEPLOYMENT.md)
- Application README: [../README.md](../README.md)
- Fixes applied: [../FIXES_APPLIED.md](../FIXES_APPLIED.md)
