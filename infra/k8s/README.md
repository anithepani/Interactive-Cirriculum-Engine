# Kubernetes manifests (Phase 5)

Production deployment manifests land in Phase 5 (Polish, Evaluation, Deployment).

## Planned resources

- `namespace.yaml` — `ice-prod`
- `api-deployment.yaml` + `api-service.yaml` — FastAPI (HPA on CPU + latency)
- `worker-deployment.yaml` — Celery workers (two pools: CPU + GPU)
- `web-deployment.yaml` + `web-service.yaml` — Next.js
- `postgres-statefulset.yaml` — managed Postgres preferred (RDS/CloudSQL) for prod
- `redis-statefulset.yaml`
- `judge0-deployment.yaml` — code sandbox pool (M14 MVP)
- `minio-statefulset.yaml` — or S3 in prod
- `ingress.yaml` — TLS termination, per-tenant routing
- `hpa.yaml` — autoscaling for stateless workers (risk E18 concurrency)
- `network-policies.yaml` — restrict sandbox egress (risk E19)

## Deployment

```bash
kubectl apply -f infra/k8s/ -n ice-prod
```

Owner: **Zubair**
