#!/usr/bin/env bash
set -euo pipefail

mkdir -p docs/benchmarks/charts

repo="${GITHUB_REPOSITORY:-kreuzberg-dev/kreuzberg}"

cat >docs/benchmarks/charts/index.html <<EOF
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Kreuzberg Benchmarks - Pending</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: #f5f7fa;
            color: #2d3748;
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            margin: 0;
        }
        .container {
            text-align: center;
            padding: 3rem;
            background: white;
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            max-width: 600px;
        }
        h1 { color: #1a202c; margin-bottom: 1rem; }
        p { color: #718096; line-height: 1.6; }
        .icon { font-size: 4rem; margin-bottom: 1rem; }
    </style>
</head>
<body>
    <div class="container">
        <div class="icon">📊</div>
        <h1>Benchmark Results Pending</h1>
        <p>Benchmark visualizations will be generated when the benchmark workflow runs.</p>
        <p>Check <a href="https://github.com/${repo}/actions/workflows/benchmarks.yaml">GitHub Actions</a> for benchmark status.</p>
    </div>
</body>
</html>
EOF

echo '[]' >docs/benchmarks/charts/results.json
echo '{"by_extension": {}}' >docs/benchmarks/charts/by-extension.json
