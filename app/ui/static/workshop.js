document.addEventListener('DOMContentLoaded', () => {
    const createPresetForm = document.getElementById('create-preset-form');
    const publicPresetsList = document.getElementById('public-presets-list');

    // Assume JWT token is stored in localStorage after login
    const TOKEN = localStorage.getItem('access_token');

    // --- Functions ---

    /**
     * Renders a list of presets to the DOM.
     * @param {Array} presets - An array of preset objects.
     */
    function renderPresets(presets) {
        publicPresetsList.innerHTML = ''; // Clear existing list
        if (!presets || presets.length === 0) {
            publicPresetsList.innerHTML = '<p>No public presets found.</p>';
            return;
        }

        presets.forEach(preset => {
            const card = document.createElement('div');
            card.className = 'preset-card';
            card.innerHTML = `
                <h4>${preset.name}</h4>
                <p>${preset.description || 'No description.'}</p>
                <code>${JSON.stringify(preset.config)}</code>
                <button class="fork-btn" data-preset-id="${preset.id}">Fork</button>
            `;
            publicPresetsList.appendChild(card);
        });
    }

    /**
     * Fetches public presets and renders them.
     */
    async function fetchAndRenderPublicPresets() {
        try {
            const response = await fetch('/api/presets/public');
            if (!response.ok) throw new Error('Failed to fetch presets');
            const presets = await response.json();
            renderPresets(presets);
        } catch (error) {
            console.error('Error fetching public presets:', error);
            publicPresetsList.innerHTML = '<p>Error loading presets.</p>';
        }
    }

    // --- Event Listeners ---

    // Handle new preset creation
    createPresetForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        if (!TOKEN) {
            alert('You must be logged in to create a preset.');
            return;
        }

        const newPreset = {
            name: document.getElementById('preset-name').value,
            description: document.getElementById('preset-description').value,
            config: JSON.parse(document.getElementById('preset-config').value),
            is_public: document.getElementById('preset-is-public').checked,
        };

        try {
            const response = await fetch('/api/presets/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${TOKEN}`,
                },
                body: JSON.stringify(newPreset),
            });

            if (!response.ok) throw new Error('Failed to create preset');
            alert('Preset created successfully!');
            createPresetForm.reset();
            fetchAndRenderPublicPresets(); // Refresh the list
        } catch (error) {
            console.error('Error creating preset:', error);
            alert('Error: Could not create preset.');
        }
    });

    // Handle forking a preset (using event delegation)
    publicPresetsList.addEventListener('click', async (e) => {
        if (e.target && e.target.classList.contains('fork-btn')) {
            if (!TOKEN) {
                alert('You must be logged in to fork a preset.');
                return;
            }
            const presetId = e.target.getAttribute('data-preset-id');

            try {
                const response = await fetch(`/api/presets/${presetId}/fork`, {
                    method: 'POST',
                    headers: { 'Authorization': `Bearer ${TOKEN}` },
                });

                if (!response.ok) throw new Error('Failed to fork preset');
                alert('Preset forked successfully! It is now available in your private presets.');
            } catch (error) {
                console.error('Error forking preset:', error);
                alert('Error: Could not fork preset.');
            }
        }
    });

    // --- Initial Load ---
    fetchAndRenderPublicPresets();
});
