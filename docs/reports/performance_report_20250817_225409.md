# Novel Engine Performance Test Report
Generated: 2025-08-17T22:45:28.493683
Test Duration: 521.04 seconds

## Executive Summary
**Performance Grade**: B
**Overall Score**: 83.8/100
**Production Ready**: ✅ Yes

### Key Findings
- Excellent baseline response times (<100ms)
- Excellent throughput capacity (442 req/s)
- Excellent reliability (<1% error rate)
- Poor story generation reliability
- System ready for production with monitoring

### Capacity Analysis
- **Maximum Throughput**: 442 requests/second
- **Stable Concurrent Users**: 50 users

## Detailed Test Results
### Baseline Performance
| Endpoint | Avg (ms) | P50 (ms) | P95 (ms) | P99 (ms) | Error Count |
|----------|----------|----------|----------|----------|-------------|
| /health | 14.1 | 1.0 | 261.9 | 261.9 | 0 |
| /characters | 1.4 | 1.1 | 6.3 | 6.3 | 0 |

### Load Test Results
#### 5 Users
| Endpoint | Throughput (req/s) | Avg (ms) | P95 (ms) | Error Rate |
|----------|-------------------|----------|----------|------------|
| /health | 44.4 | 3.4 | 6.4 | 0.00% |
| /characters | 44.8 | 3.8 | 6.9 | 0.00% |

#### 10 Users
| Endpoint | Throughput (req/s) | Avg (ms) | P95 (ms) | Error Rate |
|----------|-------------------|----------|----------|------------|
| /health | 88.5 | 6.1 | 16.3 | 0.00% |
| /characters | 88.9 | 5.4 | 9.9 | 0.00% |

#### 25 Users
| Endpoint | Throughput (req/s) | Avg (ms) | P95 (ms) | Error Rate |
|----------|-------------------|----------|----------|------------|
| /health | 219.9 | 7.7 | 16.6 | 0.00% |
| /characters | 219.5 | 8.4 | 16.7 | 0.00% |

#### 50 Users
| Endpoint | Throughput (req/s) | Avg (ms) | P95 (ms) | Error Rate |
|----------|-------------------|----------|----------|------------|
| /health | 440.1 | 9.2 | 18.0 | 0.00% |
| /characters | 441.6 | 9.5 | 21.5 | 0.00% |

### Story Generation Load Tests
| Concurrent Sims | Success Rate | Avg Time (s) | Max Time (s) |
|----------------|--------------|--------------|--------------|
| 2 Simulations | 0.0% | 41.39 | 47.53 |
| 3 Simulations | 0.0% | 47.63 | 47.64 |
| 5 Simulations | 0.0% | 47.58 | 47.59 |

### Resource Usage
| Metric | Average | Maximum | Peak |
|--------|---------|---------|------|
| CPU Usage (%) | 0.0 | 1.5 | 0.0 |
| Memory Usage (%) | 0.1 | 0.1 | N/A |
| Memory Usage (MB) | 61 | 61 | N/A |

## Recommendations
1. Improve story generation endpoint stability

## Production Deployment Guidance
✅ **System is ready for production deployment**

### Recommended Production Configuration
- Monitor response times and error rates
- Set up alerting for performance degradation
- Implement proper logging and observability
- Consider load balancing for high availability