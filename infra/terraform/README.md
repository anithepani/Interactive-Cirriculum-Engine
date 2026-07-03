# Terraform (Phase 5)

Reproducible cloud infrastructure. Target: a multi-tenant cloud with row-level
data isolation + auth from day one (locked decision #5).

## Planned resources

- `versions.tf` — provider pinning (aws / gcp)
- `backend.tf` — remote state (S3 + DynamoDB lock)
- `network.tf` — VPC, subnets, NAT
- `postgres.tf` — managed Postgres 16 with pgvector extension, RLS
- `redis.tf` — managed Redis 7
- `object-storage.tf` — S3 / GCS buckets (tenant-scoped prefixes)
- `gpu-node.tf` — GPU instance for ASR/OCR/open-LLMs (§6.3)
- `api.tf` — autoscaling group / ECS / Cloud Run
- `secrets.tf` — secret manager (OpenAI key, OAuth secrets, JWT secret)
- `monitoring.tf` — Grafana / Prometheus / Sentry hooks

## Apply

```bash
cd infra/terraform
terraform init
terraform plan -var-file=staging.tfvars
terraform apply -var-file=staging.tfvars
```

Owner: **Zubair**
