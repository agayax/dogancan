document.addEventListener('DOMContentLoaded', () => {
    const marketplaceList = document.getElementById('marketplace-list');

    // Assume JWT token is stored in localStorage after login
    const TOKEN = localStorage.getItem('access_token');

    /**
     * Renders a list of marketplace strategies to the DOM.
     * @param {Array} strategies - An array of strategy preset objects.
     */
    function renderStrategies(strategies) {
        marketplaceList.innerHTML = ''; // Clear existing list
        if (!strategies || strategies.length === 0) {
            marketplaceList.innerHTML = '<p>No strategies are currently available in the marketplace.</p>';
            return;
        }

        strategies.forEach(strategy => {
            const card = document.createElement('div');
            card.className = 'strategy-card';
            // Note: We are NOT displaying the strategy.config to the user.
            card.innerHTML = `
                <h4>${strategy.name}</h4>
                <p>${strategy.description || 'No description available.'}</p>
                <button class="lease-btn" data-preset-id="${strategy.id}">Lease Strategy</button>
            `;
            marketplaceList.appendChild(card);
        });
    }

    /**
     * Fetches marketplace strategies and renders them.
     */
    async function fetchAndRenderMarketplace() {
        try {
            const response = await fetch('/api/marketplace/');
            if (!response.ok) throw new Error('Failed to fetch marketplace strategies');
            const strategies = await response.json();
            renderStrategies(strategies);
        } catch (error) {
            console.error('Error fetching marketplace:', error);
            marketplaceList.innerHTML = '<p>Error loading marketplace strategies.</p>';
        }
    }

    // --- Event Listeners ---

    // Handle leasing a strategy (using event delegation)
    marketplaceList.addEventListener('click', async (e) => {
        if (e.target && e.target.classList.contains('lease-btn')) {
            if (!TOKEN) {
                alert('You must be logged in to lease a strategy.');
                return;
            }

            const presetId = e.target.getAttribute('data-preset-id');
            const strategyName = e.target.parentElement.querySelector('h4').textContent;

            if (confirm(`Are you sure you want to lease and run the strategy "${strategyName}" on your account?`)) {
                try {
                    const response = await fetch(`/api/marketplace/lease/${presetId}`, {
                        method: 'POST',
                        headers: { 'Authorization': `Bearer ${TOKEN}` },
                    });

                    if (!response.ok) {
                        const errorData = await response.json();
                        throw new Error(errorData.detail || 'Failed to lease strategy');
                    }

                    const result = await response.json();
                    alert(`Success! ${result.message}`);

                } catch (error) {
                    console.error('Error leasing strategy:', error);
                    alert(`Error: Could not lease strategy. ${error.message}`);
                }
            }
        }
    });

    // --- Initial Load ---
    fetchAndRenderMarketplace();
});
