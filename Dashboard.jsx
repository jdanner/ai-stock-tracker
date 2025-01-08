import React, { useEffect, useState } from 'react';
import { Line } from 'react-chartjs-2';
import { fetchQuarterlyData } from './api';

function Dashboard() {
    const [data, setData] = useState(null);
    const [timeRange, setTimeRange] = useState({
        start: '2023-01-01',
        end: new Date().toISOString()
    });

    useEffect(() => {
        const loadData = async () => {
            const metrics = await fetchQuarterlyData(timeRange);
            setData(metrics);
        };
        loadData();
    }, [timeRange]);

    return (
        <div className="dashboard">
            <h1>AI Market Monitor</h1>
            
            <section className="venture-metrics">
                <h2>Venture Investment in AI</h2>
                <Line 
                    data={formatVentureData(data?.ventureInvestment)}
                    options={chartOptions}
                />
            </section>

            <section className="cloud-metrics">
                <h2>Cloud AI Workloads</h2>
                <Line 
                    data={formatCloudData(data?.cloudWorkloads)}
                    options={chartOptions}
                />
            </section>

            <section className="nvidia-metrics">
                <h2>NVIDIA Orders</h2>
                <Line 
                    data={formatNvidiaData(data?.nvidiaMetrics)}
                    options={chartOptions}
                />
                <div className="mag7-breakdown">
                    <h3>Magnificent 7 Breakdown</h3>
                    <PieChart data={formatMag7Data(data?.nvidiaMetrics)} />
                </div>
            </section>
        </div>
    );
} 