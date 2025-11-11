document.addEventListener('DOMContentLoaded', () => {
    // --- Chart Setup ---
    const chartContainer = document.getElementById('chart-container');
    const chart = LightweightCharts.createChart(chartContainer, {
        width: chartContainer.clientWidth,
        height: chartContainer.clientHeight,
        layout: {
            backgroundColor: '#1e1e1e',
            textColor: '#e0e0e0',
        },
        grid: {
            vertLines: { color: '#2a2e39' },
            horzLines: { color: '#2a2e39' },
        },
        timeScale: {
            borderColor: '#2a2e39',
        },
    });
    const candlestickSeries = chart.addCandlestickSeries();

    // --- Agent Signal Markers ---
    let grendelMarkers = [];
    let beowulfMarkers = [];

    // --- Chat UI Elements ---
    const chatMessages = document.getElementById('chat-messages');
    const chatInput = document.getElementById('chat-input');
    const chatSendBtn = document.getElementById('chat-send-btn');

    // --- WebSocket Connection ---
    const chatSocket = new WebSocket(`ws://${window.location.host}/ws/chat`);

    chatSocket.onopen = () => {
        console.log("WebSocket connection established.");
        // You can fetch initial data here if needed
    };

    chatSocket.onmessage = (event) => {
        const data = JSON.parse(event.data);

        if (data.type === 'chat_response') {
            addChatMessage(data.sender, data.text, data.persona);
        } else if (data.type === 'signal') {
            handleSignalMessage(data);
        } else if (data.type === 'ohlcv_update') {
            candlestickSeries.update(data.kline);
        }
    };

    chatSocket.onclose = () => {
        console.log("WebSocket connection closed.");
        addChatMessage('System', 'Connection to server lost.', 'system');
    };

    // --- UI Event Handlers ---

    // Minimalism Mode Toggle
    const minimalismBtn = document.getElementById('minimalism-toggle-btn');
    const leftPanel = document.querySelector('.left-panel'); // Target the whole left panel for simplicity

    minimalismBtn.addEventListener('click', () => {
        leftPanel.classList.toggle('hidden');
        // Resize the chart to fit the new container size
        setTimeout(() => {
            chart.resize(chartContainer.clientWidth, chartContainer.clientHeight);
        }, 50); // A small delay to allow CSS transition to start
    });

    const sendChatMessage = () => {
        const message = chatInput.value;
        if (message.trim() !== '') {
            chatSocket.send(JSON.stringify({ type: 'chat_message', text: message }));
            addChatMessage('You', message, 'user');
            chatInput.value = '';
        }
    };

    chatSendBtn.addEventListener('click', sendChatMessage);
    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            sendChatMessage();
        }
    });

    // --- Helper Functions ---
    function addChatMessage(sender, text, persona = 'bot') {
        const messageEl = document.createElement('div');
        messageEl.classList.add('message', persona);

        // Add persona class for styling
        if (persona === 'Agent_Grendel') {
            messageEl.classList.add('agent-grendel');
        } else if (persona === 'Agent_Beowulf') {
            messageEl.classList.add('agent-beowulf');
        }

        messageEl.innerHTML = `<strong>[${sender}]:</strong> ${text}`;
        chatMessages.appendChild(messageEl);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function handleSignalMessage(data) {
        const { timestamp, agent, signal, price } = data;
        const marker = {
            time: timestamp,
            position: signal === 'buy' ? 'belowBar' : 'aboveBar',
            color: agent === 'Agent_Grendel' ? '#e91e63' : '#2196f3', // Grendel: Pink, Beowulf: Blue
            shape: signal === 'buy' ? 'arrowUp' : 'arrowDown',
            text: agent.split('_')[1][0] // 'G' or 'B'
        };

        if (agent === 'Agent_Grendel') {
            grendelMarkers.push(marker);
            candlestickSeries.setMarkers(grendelMarkers.concat(beowulfMarkers));
        } else if (agent === 'Agent_Beowulf') {
            beowulfMarkers.push(marker);
            candlestickSeries.setMarkers(grendelMarkers.concat(beowulfMarkers));
        }
    }

    // Load initial data
    fetch('/api/ohlcv/BTCUSDT/1h')
        .then(response => response.json())
        .then(data => {
            candlestickSeries.setData(data);
        });
});
