import pandas as pd
import numpy as np
from pathlib import Path
import sys
import yaml
import time
import random
import json
sys.path.append(str(Path(__file__).resolve().parents[2]))
from app.services.llm import LLMService

class MultiAgentBacktestEngine:
    """
    A backtest engine that simulates multiple competing or collaborative agents,
    modeling their combined market impact and tracking individual and collective performance.
    """
    def __init__(self, data_dict, agents, initial_capital=100000.0, rebalance_freq='D'):
        self.data_dict = data_dict
        self.agents = agents # dict of {'agent_name': strategy_instance}
        self.initial_capital = initial_capital
        self.rebalance_freq = rebalance_freq

        # --- State Tracking (now per agent and collective) ---
        self.collective_portfolio = {'cash': self.initial_capital}
        self.agent_portfolios = {name: {'cash': self.initial_capital} for name in agents.keys()}

        self.collective_positions = {}
        self.agent_positions = {name: {} for name in agents.keys()}

        self.collective_history = []
        self.agent_histories = {name: [] for name in agents.keys()}

        self.master_df = pd.concat(data_dict, names=['symbol', 'timestamp']).sort_index()

    def run(self, chaos_params=None, scenario_path=None):
        print(f"--- Running Multi-Agent Backtest ---")
        print(f"Agents: {list(self.agents.keys())}")

        events = self._load_scenario(scenario_path)
        all_timestamps = self.master_df.index.get_level_values('timestamp').unique()
        rebalance_dates = pd.to_datetime(all_timestamps).to_series().resample(self.rebalance_freq).first().dropna().values

        for timestamp in all_timestamps:
            # --- (Chaos and Event logic can be integrated here as before) ---
            active_event = self._get_active_event(timestamp, events)
            slippage_mult = active_event['effects']['slippage_multiplier'] if active_event else 1.0

            # --- Record history for each agent and the collective portfolio ---
            self._record_portfolio_history(timestamp)

            # --- Rebalancing Logic for each agent ---
            if timestamp in rebalance_dates:
                # --- NEW: Model Market Impact ---
                # Aggregate all intended trades at this timestamp to model impact
                aggregated_trades = self._aggregate_trades(timestamp)

                for agent_name, strategy in self.agents.items():
                    current_data_slice = {sym: df.loc[df.index <= timestamp] for sym, df in self.data_dict.items()}
                    target_portfolio = strategy.generate_signals(current_data_slice)
                    self._rebalance_agent_portfolio(timestamp, agent_name, target_portfolio, slippage_mult, aggregated_trades)

        # --- Generate final reports ---
        self.collective_results = pd.DataFrame(self.collective_history).set_index('timestamp')
        self.agent_results = {name: pd.DataFrame(hist).set_index('timestamp') for name, hist in self.agent_histories.items()}

        return self.collective_results, self.agent_results

    def _record_portfolio_history(self, timestamp):
        # Update and record for collective
        collective_value = self._calculate_portfolio_value(self.collective_portfolio, self.collective_positions, timestamp)
        self.collective_history.append({'timestamp': timestamp, 'portfolio_value': collective_value})

        # Update and record for each agent
        for name in self.agents.keys():
            agent_value = self._calculate_portfolio_value(self.agent_portfolios[name], self.agent_positions[name], timestamp)
            self.agent_histories[name].append({'timestamp': timestamp, 'portfolio_value': agent_value})

    def _calculate_portfolio_value(self, portfolio, positions, timestamp):
        value = portfolio['cash']
        for symbol, units in positions.items():
            if (symbol, timestamp) in self.master_df.index:
                value += units * self.master_df.loc[(symbol, timestamp), 'close']
        return value

    def _aggregate_trades(self, timestamp):
        """
        Looks at all agents' desired trades to calculate total market impact.
        Returns a dict like {'BTCUSDT': {'buy': 2.5, 'sell': 0.5}}
        """
        # This is a simplified placeholder. A real implementation would be more complex.
        # For now, we'll just count how many agents want to buy/sell a symbol.
        impact = {}
        for agent_name, strategy in self.agents.items():
            current_data_slice = {sym: df.loc[df.index <= timestamp] for sym, df in self.data_dict.items()}
            target_portfolio = strategy.generate_signals(current_data_slice)

            for symbol, target_weight in target_portfolio.items():
                # Simplified logic: just count the number of agents on each side
                if symbol not in impact: impact[symbol] = {'buy': 0, 'sell': 0}

                current_units = self.agent_positions[agent_name].get(symbol, 0)
                portfolio_value = self._calculate_portfolio_value(self.agent_portfolios[agent_name], self.agent_positions[agent_name], timestamp)
                target_units = (portfolio_value * target_weight) / self.master_df.loc[(symbol, timestamp), 'close']

                if target_units > current_units:
                    impact[symbol]['buy'] += 1
                elif target_units < current_units:
                    impact[symbol]['sell'] += 1
        return impact

    def _rebalance_agent_portfolio(self, timestamp, agent_name, target_portfolio, slippage_multiplier, aggregated_trades):
        portfolio_value = self._calculate_portfolio_value(self.agent_portfolios[agent_name], self.agent_positions[agent_name], timestamp)

        # Sell assets that are overweight or no longer in target
        for symbol, current_units in list(self.agent_positions[agent_name].items()):
            target_weight = target_portfolio.get(symbol, 0)
            target_units = (portfolio_value * target_weight) / self.master_df.loc[(symbol, timestamp), 'close']
            if current_units > target_units:
                units_to_sell = current_units - target_units
                market_impact_factor = 1.0 + (aggregated_trades.get(symbol, {}).get('sell', 0) * 0.5) # Each agent adds 50% more slippage
                self._execute_sell(timestamp, agent_name, symbol, units_to_sell, slippage_multiplier, market_impact_factor)

        # Buy assets that are underweight
        for symbol, target_weight in target_portfolio.items():
            current_units = self.agent_positions[agent_name].get(symbol, 0)
            target_units = (portfolio_value * target_weight) / self.master_df.loc[(symbol, timestamp), 'close']
            if target_units > current_units:
                units_to_buy = target_units - current_units
                market_impact_factor = 1.0 + (aggregated_trades.get(symbol, {}).get('buy', 0) * 0.5)
                self._execute_buy(timestamp, agent_name, symbol, units_to_buy, slippage_multiplier, market_impact_factor)

    def _execute_buy(self, timestamp, agent_name, symbol, units, slippage_multiplier, market_impact_factor):
        price = self.master_df.loc[(symbol, timestamp), 'close']

        # Apply slippage, now including market impact
        base_slippage = 0.001
        effective_slippage = base_slippage * slippage_multiplier * market_impact_factor
        buy_price = price * (1 + effective_slippage)
        cost = units * buy_price

        # Update agent portfolio
        self.agent_portfolios[agent_name]['cash'] -= cost
        self.agent_positions[agent_name][symbol] = self.agent_positions[agent_name].get(symbol, 0) + units

        # Update collective portfolio
        self.collective_portfolio['cash'] -= cost
        self.collective_positions[symbol] = self.collective_positions.get(symbol, 0) + units

    def _execute_sell(self, timestamp, agent_name, symbol, units, slippage_multiplier, market_impact_factor):
        price = self.master_df.loc[(symbol, timestamp), 'close']

        base_slippage = 0.001
        effective_slippage = base_slippage * slippage_multiplier * market_impact_factor
        sell_price = price * (1 - effective_slippage)
        proceeds = units * sell_price

        # Update agent portfolio
        self.agent_portfolios[agent_name]['cash'] += proceeds
        self.agent_positions[agent_name][symbol] -= units
        if self.agent_positions[agent_name][symbol] < 1e-6: # Clean up small dust
            del self.agent_positions[agent_name][symbol]

        # Update collective portfolio
        self.collective_portfolio['cash'] += proceeds
        self.collective_positions[symbol] -= units
        if self.collective_positions[symbol] < 1e-6:
            del self.collective_positions[symbol]

    def _load_scenario(self, scenario_path):
        if not scenario_path or not Path(scenario_path).exists():
            return []
        with open(scenario_path, 'r') as f:
            events = yaml.safe_load(f)
        # Convert timestamps to datetime objects
        for event in events:
            event['timestamp'] = pd.to_datetime(event['timestamp'])
        return events

    def _get_active_event(self, timestamp, events):
        for event in events:
            if event['timestamp'] <= timestamp < (event['timestamp'] + pd.Timedelta(minutes=event['duration_minutes'])):
                return event
        return None

    def _calculate_metrics(self, results_df, initial_capital):
        if results_df.empty:
            return {'Sharpe Ratio': 0, 'Max Drawdown (%)': -100}

        returns = results_df['portfolio_value'].pct_change().dropna()
        sharpe = (returns.mean() / returns.std()) * np.sqrt(365) if returns.std() != 0 else 0

        rolling_max = results_df['portfolio_value'].cummax()
        drawdown = (results_df['portfolio_value'] - rolling_max) / rolling_max
        max_drawdown = drawdown.min() * 100

        return {'Sharpe Ratio': sharpe, 'Max Drawdown (%)': max_drawdown}

    def generate_multi_agent_report(self, collective_results, agent_results, report_filename):
        print("--- Generating Multi-Agent Report ---")

        report = {
            "collective_performance": self._calculate_metrics(collective_results, self.initial_capital),
            "agent_performance": {}
        }

        for agent_name, results_df in agent_results.items():
            report["agent_performance"][agent_name] = self._calculate_metrics(results_df, self.initial_capital)

        report_path = Path('reports') / report_filename
        report_path.parent.mkdir(parents=True, exist_ok=True)
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=4)

        print(f"Multi-agent report saved to {report_path}")
        print(json.dumps(report, indent=4))
        return report
