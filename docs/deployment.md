# Deployment Guide

This guide covers deploying Scanipy's containerized Semgrep analysis to Amazon EKS (Elastic Kubernetes Service).

## Prerequisites

- AWS account with appropriate permissions
- EKS cluster (or create one with `eksctl`)
- kubectl configured for your cluster
- Docker for building images
- AWS CLI configured

## Step 1: Build and Push Container Images

### Build Worker Image

```bash
# Build worker container
docker build -f tools/semgrep/worker/Dockerfile -t scanipy-semgrep-worker:latest .

# Tag for ECR
docker tag scanipy-semgrep-worker:latest <account-id>.dkr.ecr.<region>.amazonaws.com/scanipy-semgrep-worker:latest

# Push to ECR
aws ecr get-login-password --region <region> | docker login --username AWS --password-stdin <account-id>.dkr.ecr.<region>.amazonaws.com
docker push <account-id>.dkr.ecr.<region>.amazonaws.com/scanipy-semgrep-worker:latest
```

### Build API Image

```bash
# Build API service
docker build -f services/api/Dockerfile -t scanipy-api:latest .

# Tag and push to ECR
docker tag scanipy-api:latest <account-id>.dkr.ecr.<region>.amazonaws.com/scanipy-api:latest
docker push <account-id>.dkr.ecr.<region>.amazonaws.com/scanipy-api:latest
```

## Step 2: Set Up Infrastructure

### Create S3 Bucket

```bash
aws s3 mb s3://scanipy-results --region <region>
```

### Create RDS PostgreSQL Database

```bash
aws rds create-db-instance \
  --db-instance-identifier scanipy-db \
  --db-instance-class db.t3.micro \
  --engine postgres \
  --master-username scanipy \
  --master-user-password <password> \
  --allocated-storage 20
```

### Create ECR Repositories

```bash
aws ecr create-repository --repository-name scanipy-semgrep-worker
aws ecr create-repository --repository-name scanipy-api
```

## Step 3: Configure Kubernetes

### Create Namespace

```bash
kubectl create namespace scanipy
```

### Update ConfigMap

Edit `k8s/configmap.yaml` with your values:

```yaml
data:
  s3_bucket: "scanipy-results"
  aws_region: "us-east-1"
  api_url: "http://scanipy-api.scanipy.svc.cluster.local:8000"
  k8s_namespace: "scanipy"
  worker_image: "<account-id>.dkr.ecr.<region>.amazonaws.com/scanipy-semgrep-worker:latest"
```

### Create Secrets

```bash
kubectl create secret generic scanipy-secrets \
  --from-literal=database_url="postgresql://user:password@rds-endpoint:5432/scanipy" \
  --namespace=scanipy
```

### Apply Kubernetes Manifests

```bash
# Apply RBAC
kubectl apply -f k8s/rbac.yaml

# Apply ConfigMap
kubectl apply -f k8s/configmap.yaml

# Apply API service
kubectl apply -f k8s/api-service.yaml
```

## Step 4: Set Up IAM Roles for Service Accounts (IRSA)

### Create IAM Policy for S3 Access

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject"
      ],
      "Resource": "arn:aws:s3:::scanipy-results/*"
    }
  ]
}
```

### Attach Policy to Service Account

```bash
eksctl create iamserviceaccount \
  --name scanipy-worker \
  --namespace scanipy \
  --cluster <cluster-name> \
  --attach-policy-arn <policy-arn> \
  --approve
```

## Step 5: Expose API Service

### Option 1: LoadBalancer Service

Update `k8s/api-service.yaml` to use LoadBalancer:

```yaml
spec:
  type: LoadBalancer
```

### Option 2: Ingress

Create an Ingress resource for the API service.

## Step 6: Verify Deployment

```bash
# Check API service
kubectl get pods -n scanipy
kubectl get svc -n scanipy

# Test API health
curl http://<api-endpoint>/health
```

## Step 7: Use Container Mode

```bash
scanipy --query "extractall" --run-semgrep \
  --container-mode \
  --api-url http://<api-endpoint> \
  --s3-bucket scanipy-results
```

## Monitoring

### View Jobs

```bash
kubectl get jobs -n scanipy
kubectl logs -n scanipy job/<job-name>
```

### View API Logs

```bash
kubectl logs -n scanipy deployment/scanipy-api
```

## Troubleshooting

### Jobs Not Starting

- Check RBAC permissions: `kubectl describe rolebinding scanipy-api-binding -n scanipy`
- Verify service account: `kubectl get sa scanipy-api -n scanipy`
- Check API logs for errors

### S3 Upload Failures

- Verify IAM role is attached to service account
- Check S3 bucket permissions
- Verify AWS credentials in worker pods

### Database Connection Issues

- Verify RDS security group allows connections from EKS
- Check database URL in secrets
- Test connection from API pod

## Scaling

### Horizontal Pod Autoscaling (HPA)

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: scanipy-api-hpa
  namespace: scanipy
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: scanipy-api
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

## Cost Optimization

- Use Spot Instances for worker nodes
- Set appropriate resource limits
- Configure Job TTL to clean up completed jobs
- Use S3 lifecycle policies for old results
