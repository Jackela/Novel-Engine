# Terraform Outputs for Novel Engine Infrastructure

# VPC Outputs
output "vpc_id" {
  description = "ID of the VPC"
  value       = module.vpc.vpc_id
}

output "vpc_cidr_block" {
  description = "CIDR block of the VPC"
  value       = module.vpc.vpc_cidr_block
}

output "private_subnets" {
  description = "List of IDs of private subnets"
  value       = module.vpc.private_subnets
}

output "public_subnets" {
  description = "List of IDs of public subnets"
  value       = module.vpc.public_subnets
}

output "database_subnets" {
  description = "List of IDs of database subnets"
  value       = module.vpc.database_subnets
}

# EKS Outputs
output "cluster_name" {
  description = "Name of the EKS cluster"
  value       = module.eks.cluster_name
}

output "cluster_endpoint" {
  description = "Endpoint for EKS control plane"
  value       = module.eks.cluster_endpoint
  sensitive   = true
}

output "cluster_security_group_id" {
  description = "Security group ID attached to the EKS cluster"
  value       = module.eks.cluster_security_group_id
}

output "cluster_iam_role_arn" {
  description = "IAM role ARN associated with EKS cluster"
  value       = module.eks.cluster_iam_role_arn
}

output "cluster_certificate_authority_data" {
  description = "Base64 encoded certificate data required to communicate with the cluster"
  value       = module.eks.cluster_certificate_authority_data
  sensitive   = true
}

output "cluster_oidc_issuer_url" {
  description = "The URL on the EKS cluster OIDC Issuer"
  value       = module.eks.cluster_oidc_issuer_url
}

output "node_groups" {
  description = "EKS node groups"
  value       = module.eks.node_groups
  sensitive   = true
}

# RDS Outputs (if enabled)
output "rds_endpoint" {
  description = "RDS instance endpoint"
  value       = var.enable_rds ? module.rds[0].db_instance_endpoint : null
  sensitive   = true
}

output "rds_port" {
  description = "RDS instance port"
  value       = var.enable_rds ? module.rds[0].db_instance_port : null
}

output "rds_instance_id" {
  description = "RDS instance ID"
  value       = var.enable_rds ? module.rds[0].db_instance_id : null
}

# S3 Outputs
output "s3_bucket_id" {
  description = "Name of the S3 bucket"
  value       = aws_s3_bucket.novel_engine_data.id
}

output "s3_bucket_arn" {
  description = "ARN of the S3 bucket"
  value       = aws_s3_bucket.novel_engine_data.arn
}

output "s3_bucket_domain_name" {
  description = "Domain name of the S3 bucket"
  value       = aws_s3_bucket.novel_engine_data.bucket_domain_name
}

# IAM Outputs
output "app_iam_role_arn" {
  description = "ARN of the IAM role for the application"
  value       = aws_iam_role.novel_engine_app.arn
}

# CloudWatch Outputs
output "cloudwatch_log_group_name" {
  description = "Name of the CloudWatch log group"
  value       = aws_cloudwatch_log_group.novel_engine.name
}

output "cloudwatch_log_group_arn" {
  description = "ARN of the CloudWatch log group"
  value       = aws_cloudwatch_log_group.novel_engine.arn
}

# Monitoring Outputs
output "prometheus_endpoint" {
  description = "Prometheus endpoint"
  value       = var.enable_prometheus ? module.monitoring.prometheus_endpoint : null
}

output "grafana_endpoint" {
  description = "Grafana endpoint"
  value       = var.enable_grafana ? module.monitoring.grafana_endpoint : null
}

output "alertmanager_endpoint" {
  description = "Alertmanager endpoint"
  value       = var.enable_alertmanager ? module.monitoring.alertmanager_endpoint : null
}

# Configuration Outputs for kubectl
output "kubectl_config" {
  description = "kubectl config for connecting to the cluster"
  value = {
    cluster_name     = module.eks.cluster_name
    cluster_endpoint = module.eks.cluster_endpoint
    cluster_ca_data  = module.eks.cluster_certificate_authority_data
    region          = var.aws_region
  }
  sensitive = true
}

# Application URLs
output "application_url" {
  description = "URL to access the Novel Engine application"
  value       = var.domain_name != "" ? "https://${var.domain_name}" : "Use port-forward to access the application"
}

output "api_url" {
  description = "URL to access the Novel Engine API"
  value       = var.domain_name != "" ? "https://api.${var.domain_name}" : "Use port-forward to access the API"
}

# Deployment Information
output "deployment_info" {
  description = "Information for deploying the application"
  value = {
    cluster_name = module.eks.cluster_name
    namespace    = "novel-engine"
    region       = var.aws_region
    environment  = var.environment
    image_tag    = var.app_image_tag
  }
}

# Connection Commands
output "connection_commands" {
  description = "Commands to connect to the infrastructure"
  value = {
    kubectl_config = "aws eks update-kubeconfig --region ${var.aws_region} --name ${module.eks.cluster_name}"
    port_forward   = "kubectl port-forward -n novel-engine svc/novel-engine 8000:8000"
    logs          = "kubectl logs -n novel-engine -l app=novel-engine -f"
  }
}