import pandas as pd
import numpy as np
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[2]))
from app.strategy.ade_strategy import ADEStrategy
from app.features.engineer import FeatureEngineer

class SwarmManagerStrategy:
    """
    A meta-strategy that manages a "swarm" of specialized AI agent personas.
    It allocates capital between agents based on the current market regime.
    """
    def __init__(self, models_config):
        """
        :param models_config: A dictionary defining the personas, e.g.,
          {
            'Agent_Grendel': {'model_path': 'models/ade_grendel_v1.bin'},
            'Agent_Beowulf': {'model_path': 'models/ade_beowulf_v1.bin'}
          }
        """
        self.agents = {}
        self.feature_engineer = FeatureEngineer()

        print("Initializing Swarm Manager and its agents...")
        for agent_name, config in models_config.items():
            # Pass the threshold for the classifier
            threshold = 0.55 if 'Beowulf' in agent_name else 0.0001
            self.agents[agent_name] = ADEStrategy(model_path=config['model_path'], threshold=threshold)
        print("All agents initialized.")

    def generate_signals(self, data):
        """
        Generates a target portfolio by weighting the signals from underlying agents.

        :param data: The latest dictionary of market dataframes.
        :return: A dictionary representing the target portfolio weights, e.g., {'BTCUSDT': 0.8}.
        """
        # --- 1. Get signals from each agent ---
        agent_signals = {}
        for agent_name, agent_strategy in self.agents.items():
            agent_signals[agent_name] = agent_strategy.generate_signals(data)

        # --- 2. Analyze Market Regime ---
        symbol = list(data.keys())[0]
        # Run features on the most recent data to get regime signals
        market_df_with_features = self.feature_engineer._generate_technical_indicators(data[symbol])
        last_row = market_df_with_features.iloc[-1]

        is_high_volatility = last_row.get('volatility_regime', 0) == 1

        # --- 3. Determine Agent Weights based on Regime ---
        agent_weights = {}
        if is_high_volatility:
            # print("Swarm Manager: High volatility -> Favoring Grendel.")
            agent_weights['Agent_Grendel'] = 0.8
            agent_weights['Agent_Beowulf'] = 0.2
        else:
            # print("Swarm Manager: Low volatility -> Favoring Beowulf.")
            agent_weights['Agent_Grendel'] = 0.3
            agent_weights['Agent_Beowulf'] = 0.7

        # --- 4. Combine Signals into a Final Target Portfolio ---
        final_target_portfolio = {}
        all_symbols = set(agent_signals['Agent_Grendel'].keys()) | set(agent_signals['Agent_Beowulf'].keys())

        for sym in all_symbols:
            grendel_weight = agent_signals.get('Agent_Grendel', {}).get(sym, 0.0)
            beowulf_weight = agent_signals.get('Agent_Beowulf', {}).get(sym, 0.0)

            manager_grendel_weight = agent_weights.get('Agent_Grendel', 0.5)
            manager_beowulf_weight = agent_weights.get('Agent_Beowulf', 0.5)

            final_weight = (grendel_weight * manager_grendel_weight) + (beowulf_weight * manager_beowulf_weight)
            final_target_portfolio[sym] = np.clip(final_weight, 0, 1)

        return final_target_portfolio

if __name__ == '__main__':
    # This is for demonstration and cannot be run directly without a proper
    # data setup and refactored agent strategies.
    print("SwarmManagerStrategy class defined.")
    # Example Usage (conceptual):
    # swarm_manager = SwarmManagerStrategy(data, models_config)
    # target_portfolio = swarm_manager.generate_signals(latest_data)
    # print("Target Portfolio:", target_portfolio)
