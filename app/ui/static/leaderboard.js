document.addEventListener('DOMContentLoaded', () => {
    const leaderboardBody = document.getElementById('leaderboard-body');

    /**
     * Fetches leaderboard data and renders it into the table.
     */
    async function fetchAndRenderLeaderboard() {
        try {
            const response = await fetch('/api/leaderboard/');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();

            if (!data || data.length === 0) {
                leaderboardBody.innerHTML = '<tr><td colspan="7">No public paper trading sessions found.</td></tr>';
                return;
            }

            // Clear any existing rows
            leaderboardBody.innerHTML = '';

            // Populate the table
            data.forEach(entry => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${entry.rank}</td>
                    <td>${entry.username}</td>
                    <td>${entry.preset_name}</td>
                    <td>${entry.sharpe_ratio.toFixed(2)}</td>
                    <td>${entry.max_drawdown.toFixed(2)}%</td>
                    <td>${entry.pnl_percentage.toFixed(2)}%</td>
                    <td>${entry.resilience_score.toFixed(2)}</td>
                `;
                leaderboardBody.appendChild(row);
            });

        } catch (error) {
            console.error('Failed to fetch or render leaderboard:', error);
            leaderboardBody.innerHTML = `<tr><td colspan="7">Error loading leaderboard data.</td></tr>`;
        }
    }

    // --- Initial Load ---
    fetchAndRenderLeaderboard();
});
