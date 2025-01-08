// Core data structure for tracking metrics
const AIMetrics = {
    ventureInvestment: {
        source: "CB Insights API", // or similar VC data provider
        frequency: "quarterly",
        metrics: {
            totalInvestment: 0,
            dealCount: 0,
            topDeals: []
        }
    },
    cloudWorkloads: {
        azure: {
            source: "Azure Monitor API",
            metrics: {
                gpuUtilization: 0,
                aiServiceUsage: 0
            }
        },
        gcp: {
            source: "Google Cloud Monitoring API",
            metrics: {
                gpuUtilization: 0,
                aiServiceUsage: 0
            }
        },
        aws: {
            source: "AWS CloudWatch API",
            metrics: {
                gpuUtilization: 0,
                aiServiceUsage: 0
            }
        }
    },
    nvidiaMetrics: {
        source: "SEC Filings + Financial Reports",
        frequency: "quarterly",
        metrics: {
            totalOrders: 0,
            mag7Percentage: 0,
            breakdown: {
                meta: 0,
                apple: 0,
                amazon: 0,
                microsoft: 0,
                alphabet: 0,
                nvidia: 0,
                tesla: 0
            }
        }
    }
}; 