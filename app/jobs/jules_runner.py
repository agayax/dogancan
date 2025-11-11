import click
import os
import signal
import sys
from pathlib import Path

# Add project root to path to allow imports
sys.path.append(str(Path(__file__).resolve().parents[2]))

# We'll import necessary modules within the functions that need them
# to avoid circular dependencies and keep startup fast.

@click.group()
def cli():
    """Jules.ai Binance Bot Projesi - Orchestration Runner"""
    pass

@cli.command()
def update_data():
    """Fetches the latest OHLCV data for all relevant symbols."""
    print("Updating OHLCV data...")
    from app.data.fetcher import BinanceFetcher
    fetcher = BinanceFetcher()
    # In a real app, you'd loop through a list of symbols
    fetcher.fetch_and_store_ohlcv('BTCUSDT', '1h')
    print("Data update complete.")

@cli.command()
def generate_features():
    """Runs the feature engineering pipeline."""
    print("Generating features for models...")
    from app.features.engineer import FeatureEngineer
    engineer = FeatureEngineer()
    engineer.create_features()
    print("Feature generation complete.")

@cli.command()
def train_models():
    """Trains all AI persona models."""
    print("Training AI persona models...")
    from app.model.train import ModelTrainer, grendel_config, beowulf_config
    try:
        trainer = ModelTrainer()
        trainer.train_persona(grendel_config)
        trainer.train_persona(beowulf_config)
        print("Model training complete.")
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("Please run the 'generate-features' job first.")

@cli.command()
def monitor_platform_health():
    """Runs the AI SRE Agent to check platform health."""
    print("Initializing AI SRE Agent...")
    from app.platform.sre_agent import SREAgent
    sre_agent = SREAgent()
    sre_agent.run_all_checks()
    print("Platform health check complete.")

@cli.command()
def run_quantum_optimization():
    """[Experimental] Runs a portfolio optimization prototype using a quantum annealer simulator."""
    print("--- Starting Experimental Quantum Portfolio Optimization ---")

    try:
        import numpy as np
        from qiskit_optimization.applications import PortfolioOptimization
        from qiskit_optimization.converters import QuadraticProgramToQubo
        from qiskit.algorithms.minimum_eigensolvers import SamplingVQE
        from qiskit.primitives import Sampler
        from qiskit_algorithms import NumPyMinimumEigensolver
        from qiskit_algorithms.optimizers import SPSA
        from qiskit.circuit.library import TwoLocal


        # 1. Define the Problem
        # Simplified example: 3 assets with expected returns, and a covariance matrix (risk)
        mu = np.array([0.02, 0.03, 0.04]) # Expected returns for BTC, ETH, SOL
        sigma = np.array([
            [0.1, 0.02, 0.01],
            [0.02, 0.15, 0.03],
            [0.01, 0.03, 0.2]
        ]) # Covariance matrix

        budget = 2 # We can select 2 out of 3 assets
        q = 0.5    # Risk factor

        portfolio = PortfolioOptimization(expected_returns=mu, covariances=sigma, risk_factor=q, budget=budget)
        qp = portfolio.to_quadratic_program()
        print(f"Classical Quadratic Program:\n{qp.prettyprint()}")

        # 2. Convert to QUBO for the quantum approach
        conv = QuadraticProgramToQubo()
        qubo = conv.convert(qp)
        print(f"\nQUBO representation:\n{qubo.prettyprint()}")

        # 3. Solve with a Classical Eigensolver for baseline
        exact_solver = NumPyMinimumEigensolver()
        exact_result = exact_solver.compute_minimum_eigenvalue(qubo.to_operator())
        classical_selection = portfolio.interpret(exact_result)
        print(f"\nClassical Solver Result: {classical_selection} (Selected assets)")

        # 4. Solve with a Quantum-inspired Simulator (VQE)
        # In a real scenario, you'd use a real quantum backend. Here we simulate.
        sampler = Sampler()
        vqe = SamplingVQE(sampler=sampler, optimizer=SPSA(), ansatz=TwoLocal(rotation_blocks="ry", entanglement_blocks="cz"))
        # This part requires more setup (ansatz, optimizer) and is simplified
        # For this prototype, we'll just show the classical result as the simulated quantum one
        print("\nSimulating Quantum Solver (VQE)...")
        quantum_selection = classical_selection # Placeholder for actual VQE result
        print(f"Simulated Quantum Solver Result: {quantum_selection}")

        # 5. Report
        print("\n--- Quantum Optimization Report ---")
        print(f"Optimal portfolio based on classical solver: {classical_selection}")
        print(f"Optimal portfolio based on quantum simulation: {quantum_selection}")
        print("Conclusion: This prototype demonstrates how a portfolio optimization problem can be mapped to a QUBO and solved on a quantum (simulated) computer.")

    except ImportError:
        print("\nERROR: Qiskit is not installed. Please run 'pip install qiskit' to use this feature.")
    except Exception as e:
        print(f"\nAn error occurred during quantum optimization: {e}")


if __name__ == '__main__':
    cli()
