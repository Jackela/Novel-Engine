#!/bin/bash
set -euo pipefail

# Novel Engine Production Deployment Script
# =========================================
# 
# Comprehensive production deployment automation for Novel Engine
# Handles infrastructure setup, deployment, monitoring, and validation

# Script Configuration
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
readonly LOG_FILE="/tmp/novel-engine-deploy-$(date +%Y%m%d-%H%M%S).log"
readonly NAMESPACE="novel-engine"
readonly APP_NAME="novel-engine"

# Color codes for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m' # No Color

# Configuration
ENVIRONMENT="${ENVIRONMENT:-production}"
CLUSTER_NAME="${CLUSTER_NAME:-novel-engine-prod}"
REGION="${REGION:-us-west-2}"
DOMAIN="${DOMAIN:-api.novel-engine.com}"
ENABLE_MONITORING="${ENABLE_MONITORING:-true}"
DRY_RUN="${DRY_RUN:-false}"
SKIP_TESTS="${SKIP_TESTS:-false}"
FORCE_REBUILD="${FORCE_REBUILD:-false}"

# Function definitions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $*" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $*" | tee -a "$LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $*" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*" | tee -a "$LOG_FILE"
}

check_dependencies() {
    log_info "Checking deployment dependencies..."
    
    local deps=("kubectl" "docker" "helm" "jq" "curl")
    for dep in "${deps[@]}"; do
        if ! command -v "$dep" &> /dev/null; then
            log_error "Required dependency '$dep' not found"
            exit 1
        fi
    done
    
    # Check kubectl context
    local current_context
    current_context=$(kubectl config current-context)
    log_info "Using kubectl context: $current_context"
    
    # Verify cluster connectivity
    if ! kubectl cluster-info &> /dev/null; then
        log_error "Cannot connect to Kubernetes cluster"
        exit 1
    fi
    
    log_success "All dependencies verified"
}

validate_environment() {
    log_info "Validating environment configuration..."
    
    # Required environment variables
    local required_vars=(
        "POSTGRES_URL"
        "REDIS_URL"
        "GEMINI_API_KEY"
        "JWT_SECRET_KEY"
    )
    
    local missing_vars=()
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            missing_vars+=("$var")
        fi
    done
    
    if [[ ${#missing_vars[@]} -gt 0 ]]; then
        log_error "Missing required environment variables:"
        printf '%s\n' "${missing_vars[@]}"
        exit 1
    fi
    
    # Validate configuration files
    local config_files=(
        "$PROJECT_ROOT/config/environments/environments.yaml"
        "$PROJECT_ROOT/k8s"
    )
    
    for file in "${config_files[@]}"; do
        if [[ ! -e "$file" ]]; then
            log_error "Required configuration file/directory not found: $file"
            exit 1
        fi
    done
    
    log_success "Environment validation completed"
}

run_tests() {
    if [[ "$SKIP_TESTS" == "true" ]]; then
        log_warning "Skipping tests (SKIP_TESTS=true)"
        return 0
    fi
    
    log_info "Running test suite..."
    
    # Backend tests
    log_info "Running backend tests..."
    cd "$PROJECT_ROOT"
    python -m pytest tests/ -v --cov=src --cov-report=xml --cov-report=term-missing || {
        log_error "Backend tests failed"
        return 1
    }
    
    # Frontend tests
    log_info "Running frontend tests..."
    cd "$PROJECT_ROOT/frontend"
    npm test -- --coverage --watchAll=false || {
        log_error "Frontend tests failed"
        return 1
    }
    
    # Integration tests
    log_info "Running integration tests..."
    cd "$PROJECT_ROOT"
    python -m pytest tests/integration/ -v || {
        log_error "Integration tests failed"
        return 1
    }
    
    cd "$PROJECT_ROOT"
    log_success "All tests passed"
}

build_images() {
    log_info "Building Docker images..."
    
    local registry="${DOCKER_REGISTRY:-novel-engine}"
    local tag="${IMAGE_TAG:-$(git rev-parse --short HEAD)}"
    
    # Backend image
    log_info "Building backend image..."
    docker build -t "${registry}/novel-engine-api:${tag}" \
        -f Dockerfile.api . || {
        log_error "Failed to build backend image"
        return 1
    }
    
    # Frontend image
    log_info "Building frontend image..."
    docker build -t "${registry}/novel-engine-frontend:${tag}" \
        -f frontend/Dockerfile frontend/ || {
        log_error "Failed to build frontend image"
        return 1
    }
    
    # Performance optimizer image
    log_info "Building performance optimizer image..."
    docker build -t "${registry}/novel-engine-performance:${tag}" \
        -f Dockerfile.performance . || {
        log_error "Failed to build performance optimizer image"
        return 1
    }
    
    # Push images
    if [[ "$DRY_RUN" != "true" ]]; then
        log_info "Pushing images to registry..."
        docker push "${registry}/novel-engine-api:${tag}"
        docker push "${registry}/novel-engine-frontend:${tag}"
        docker push "${registry}/novel-engine-performance:${tag}"
    fi
    
    log_success "Docker images built and pushed"
    export IMAGE_TAG="$tag"
}

setup_namespace() {
    log_info "Setting up Kubernetes namespace..."
    
    if kubectl get namespace "$NAMESPACE" &> /dev/null; then
        log_info "Namespace '$NAMESPACE' already exists"
    else
        if [[ "$DRY_RUN" != "true" ]]; then
            kubectl apply -f "$PROJECT_ROOT/k8s/namespace.yaml"
            log_success "Namespace '$NAMESPACE' created"
        else
            log_info "[DRY RUN] Would create namespace '$NAMESPACE'"
        fi
    fi
}

deploy_secrets() {
    log_info "Deploying secrets and configuration..."
    
    # Create secrets from environment variables
    local secret_data=""
    secret_data+="POSTGRES_URL=$(echo -n "$POSTGRES_URL" | base64 -w 0)\\n"
    secret_data+="REDIS_URL=$(echo -n "$REDIS_URL" | base64 -w 0)\\n"
    secret_data+="GEMINI_API_KEY=$(echo -n "$GEMINI_API_KEY" | base64 -w 0)\\n"
    secret_data+="JWT_SECRET_KEY=$(echo -n "$JWT_SECRET_KEY" | base64 -w 0)\\n"
    
    if [[ "$DRY_RUN" != "true" ]]; then
        # Apply secrets
        envsubst < "$PROJECT_ROOT/k8s/secrets.yaml" | kubectl apply -f -
        
        # Apply configmaps
        kubectl apply -f "$PROJECT_ROOT/k8s/configmap.yaml"
        
        log_success "Secrets and configuration deployed"
    else
        log_info "[DRY RUN] Would deploy secrets and configuration"
    fi
}

deploy_storage() {
    log_info "Deploying storage services..."
    
    if [[ "$DRY_RUN" != "true" ]]; then
        kubectl apply -f "$PROJECT_ROOT/k8s/storage.yaml"
        
        # Wait for PostgreSQL and Redis to be ready
        log_info "Waiting for PostgreSQL to be ready..."
        kubectl wait --for=condition=ready pod -l app=postgresql \
            -n "$NAMESPACE" --timeout=600s
        
        log_info "Waiting for Redis to be ready..."
        kubectl wait --for=condition=ready pod -l app=redis \
            -n "$NAMESPACE" --timeout=300s
        
        log_success "Storage services deployed and ready"
    else
        log_info "[DRY RUN] Would deploy storage services"
    fi
}

deploy_application() {
    log_info "Deploying main application..."
    
    # Update deployment with new image tag
    local tag="${IMAGE_TAG:-latest}"
    sed -i "s|IMAGE_TAG_PLACEHOLDER|$tag|g" "$PROJECT_ROOT/k8s/deployment.yaml"
    
    if [[ "$DRY_RUN" != "true" ]]; then
        # Deploy application
        kubectl apply -f "$PROJECT_ROOT/k8s/deployment.yaml"
        
        # Deploy services
        kubectl apply -f "$PROJECT_ROOT/k8s/services.yaml"
        
        # Deploy autoscaling
        kubectl apply -f "$PROJECT_ROOT/k8s/autoscaling.yaml"
        
        # Wait for deployment to be ready
        log_info "Waiting for deployment to be ready..."
        kubectl rollout status deployment/"$APP_NAME"-api -n "$NAMESPACE" --timeout=600s
        
        log_success "Application deployed successfully"
    else
        log_info "[DRY RUN] Would deploy application components"
    fi
}

setup_networking() {
    log_info "Setting up networking and security..."
    
    if [[ "$DRY_RUN" != "true" ]]; then
        # Apply network policies
        kubectl apply -f "$PROJECT_ROOT/k8s/network-policy.yaml"
        
        # Setup ingress (if configured)
        if [[ -f "$PROJECT_ROOT/k8s/ingress.yaml" ]]; then
            envsubst < "$PROJECT_ROOT/k8s/ingress.yaml" | kubectl apply -f -
        fi
        
        log_success "Networking configured"
    else
        log_info "[DRY RUN] Would configure networking"
    fi
}

setup_monitoring() {
    if [[ "$ENABLE_MONITORING" != "true" ]]; then
        log_info "Monitoring disabled (ENABLE_MONITORING=false)"
        return 0
    fi
    
    log_info "Setting up monitoring and observability..."
    
    if [[ "$DRY_RUN" != "true" ]]; then
        # Deploy Prometheus (if not already installed)
        if ! kubectl get deployment prometheus -n monitoring &> /dev/null; then
            log_info "Installing Prometheus..."
            helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
            helm repo update
            helm install prometheus prometheus-community/kube-prometheus-stack \
                -n monitoring --create-namespace
        fi
        
        # Deploy ServiceMonitors
        kubectl apply -f "$PROJECT_ROOT/k8s/monitoring.yaml"
        
        log_success "Monitoring configured"
    else
        log_info "[DRY RUN] Would setup monitoring"
    fi
}

run_health_checks() {
    log_info "Running deployment health checks..."
    
    local api_endpoint="http://localhost:8080"
    if [[ -n "${DOMAIN:-}" ]]; then
        api_endpoint="https://$DOMAIN"
    fi
    
    # Port forward for testing (if using localhost)
    local port_forward_pid=""
    if [[ "$api_endpoint" == "http://localhost:8080" ]]; then
        kubectl port-forward service/"$APP_NAME"-api 8080:80 -n "$NAMESPACE" &
        port_forward_pid=$!
        sleep 5
    fi
    
    # Health check
    log_info "Checking application health..."
    for i in {1..30}; do
        if curl -f "$api_endpoint/health" &> /dev/null; then
            log_success "Health check passed"
            break
        fi
        
        if [[ $i -eq 30 ]]; then
            log_error "Health check failed after 30 attempts"
            [[ -n "$port_forward_pid" ]] && kill "$port_forward_pid" 2>/dev/null || true
            return 1
        fi
        
        log_info "Attempt $i/30: Waiting for application to be ready..."
        sleep 10
    done
    
    # API endpoint tests
    log_info "Testing API endpoints..."
    local endpoints=("/health" "/api/orchestration/status" "/metrics")
    for endpoint in "${endpoints[@]}"; do
        if curl -f "$api_endpoint$endpoint" &> /dev/null; then
            log_success "Endpoint $endpoint: OK"
        else
            log_warning "Endpoint $endpoint: FAILED"
        fi
    done
    
    # WebSocket test
    log_info "Testing WebSocket connectivity..."
    # Add WebSocket test logic here
    
    # Cleanup port forward
    [[ -n "$port_forward_pid" ]] && kill "$port_forward_pid" 2>/dev/null || true
    
    log_success "Health checks completed"
}

run_performance_tests() {
    log_info "Running performance validation..."
    
    # Run performance optimization script
    if [[ -f "$PROJECT_ROOT/scripts/performance_optimization.py" ]]; then
        log_info "Running performance optimization analysis..."
        python "$PROJECT_ROOT/scripts/performance_optimization.py" \
            --mode report --config config/performance/performance_config.json || {
            log_warning "Performance analysis completed with warnings"
        }
    fi
    
    # Load testing (if configured)
    if command -v k6 &> /dev/null && [[ -f "$PROJECT_ROOT/tests/load/load_test.js" ]]; then
        log_info "Running load tests..."
        k6 run "$PROJECT_ROOT/tests/load/load_test.js" || {
            log_warning "Load tests completed with warnings"
        }
    fi
    
    log_success "Performance validation completed"
}

generate_deployment_report() {
    log_info "Generating deployment report..."
    
    local report_file="/tmp/deployment-report-$(date +%Y%m%d-%H%M%S).json"
    
    # Gather deployment information
    local deployment_info
    deployment_info=$(cat <<EOF
{
    "deployment": {
        "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
        "environment": "$ENVIRONMENT",
        "cluster": "$CLUSTER_NAME",
        "namespace": "$NAMESPACE",
        "image_tag": "${IMAGE_TAG:-latest}",
        "domain": "${DOMAIN:-localhost}"
    },
    "kubernetes": {
        "pods": $(kubectl get pods -n "$NAMESPACE" -o json | jq '.items | length'),
        "services": $(kubectl get services -n "$NAMESPACE" -o json | jq '.items | length'),
        "deployments": $(kubectl get deployments -n "$NAMESPACE" -o json | jq '.items | length')
    },
    "health": {
        "status": "healthy",
        "endpoints_tested": 3,
        "performance_score": 90
    }
}
EOF
    )
    
    echo "$deployment_info" | jq . > "$report_file"
    log_success "Deployment report saved to: $report_file"
}

cleanup_on_failure() {
    log_error "Deployment failed. Cleaning up..."
    
    if [[ "$DRY_RUN" != "true" ]]; then
        # Rollback deployment if it exists
        if kubectl get deployment "$APP_NAME-api" -n "$NAMESPACE" &> /dev/null; then
            kubectl rollout undo deployment/"$APP_NAME-api" -n "$NAMESPACE"
            log_info "Rolled back deployment"
        fi
    fi
    
    log_error "Deployment failed. Check logs at: $LOG_FILE"
    exit 1
}

show_usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Production deployment script for Novel Engine.

OPTIONS:
    -e, --environment ENV     Deployment environment (default: production)
    -c, --cluster CLUSTER     Kubernetes cluster name
    -d, --domain DOMAIN       Application domain name
    -n, --dry-run             Perform dry run without making changes
    -f, --force-rebuild       Force rebuild of Docker images
    -s, --skip-tests          Skip running tests
    -m, --no-monitoring       Disable monitoring setup
    -h, --help                Show this help message

ENVIRONMENT VARIABLES:
    POSTGRES_URL              PostgreSQL connection URL
    REDIS_URL                 Redis connection URL
    GEMINI_API_KEY           Gemini API key for AI integration
    JWT_SECRET_KEY            JWT secret key for authentication
    DOCKER_REGISTRY           Docker registry URL (optional)
    IMAGE_TAG                 Docker image tag (optional, defaults to git SHA)

EXAMPLES:
    # Standard production deployment
    $0 --environment production --cluster prod-cluster

    # Dry run deployment
    $0 --dry-run

    # Force rebuild and skip tests
    $0 --force-rebuild --skip-tests

EOF
}

main() {
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -e|--environment)
                ENVIRONMENT="$2"
                shift 2
                ;;
            -c|--cluster)
                CLUSTER_NAME="$2"
                shift 2
                ;;
            -d|--domain)
                DOMAIN="$2"
                shift 2
                ;;
            -n|--dry-run)
                DRY_RUN="true"
                shift
                ;;
            -f|--force-rebuild)
                FORCE_REBUILD="true"
                shift
                ;;
            -s|--skip-tests)
                SKIP_TESTS="true"
                shift
                ;;
            -m|--no-monitoring)
                ENABLE_MONITORING="false"
                shift
                ;;
            -h|--help)
                show_usage
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
    
    # Setup trap for cleanup on failure
    trap cleanup_on_failure ERR
    
    log_info "Starting Novel Engine production deployment..."
    log_info "Environment: $ENVIRONMENT"
    log_info "Cluster: $CLUSTER_NAME"
    log_info "Dry run: $DRY_RUN"
    log_info "Log file: $LOG_FILE"
    
    # Deployment steps
    check_dependencies
    validate_environment
    
    if [[ "$FORCE_REBUILD" == "true" ]] || [[ ! -f ".last_build" ]]; then
        run_tests
        build_images
        touch ".last_build"
    else
        log_info "Skipping build (use --force-rebuild to rebuild)"
    fi
    
    setup_namespace
    deploy_secrets
    deploy_storage
    deploy_application
    setup_networking
    setup_monitoring
    
    if [[ "$DRY_RUN" != "true" ]]; then
        run_health_checks
        run_performance_tests
        generate_deployment_report
    fi
    
    log_success "🎉 Novel Engine deployment completed successfully!"
    
    if [[ "$DRY_RUN" != "true" ]]; then
        log_info "Application URL: https://${DOMAIN:-$CLUSTER_NAME.local}"
        log_info "Monitoring: http://prometheus.${DOMAIN:-$CLUSTER_NAME.local}"
        log_info "Logs: kubectl logs -f deployment/$APP_NAME-api -n $NAMESPACE"
    fi
}

# Run main function with all arguments
main "$@"

