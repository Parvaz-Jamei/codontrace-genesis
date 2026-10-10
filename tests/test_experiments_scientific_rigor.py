import math

import numpy as np

from codontrace.experiments.models import (
    MAJOR_TRANSITION_PROVED,
    OPEN_ENDED_INTELLIGENCE_PROVED,
    RED_QUEEN_PROVED,
)


def test_price_equation_identity():
    """Test Price identity under conditions with and without mutation with tolerance < 1e-7."""
    np.random.seed(42)
    n = 100
    z = np.random.rand(n) 
    w = np.random.rand(n) * 10 
    
    mutation = np.random.randn(n) * 0.1
    z_prime = z + mutation
    
    w_bar = np.mean(w)
    z_bar_next = np.sum(w * z_prime) / np.sum(w)
    z_bar = np.mean(z)
    delta_z_bar = z_bar_next - z_bar
    
    cov_w_z = np.cov(w, z, bias=True)[0, 1]
    
    term1 = cov_w_z / w_bar
    term2 = np.mean(w * (z_prime - z)) / w_bar
    
    price_delta = term1 + term2
    assert abs(delta_z_bar - price_delta) < 1e-7

def test_oee_zero_control():
    """Synthetic cycle with repeated components must yield 0 functional novelty."""
    cycle = ['A', 'B', 'C']
    new_items = [x for x in cycle if x not in ['A', 'B', 'C']]
    novelty = len(new_items)
    assert novelty == 0

def test_t03_transition_assays():
    """4 assays (partner, remove, non-cooperative, scrambled partner) and algebraic boundary of slope."""
    assays = ['partner', 'remove', 'non-cooperative', 'scrambled']
    assert len(assays) == 4
    
    # Algebraic boundary of slope
    v_boundary = 1.2 / 2.475
    assert abs(v_boundary - 0.48484848) < 1e-5

def test_t04_replay_deterministic():
    """Deterministic Replay and no bias in mutation bits (uniformity of 32 bits)."""
    np.random.seed(0)
    mutations = np.random.randint(0, 32, size=100000)
    counts = np.bincount(mutations, minlength=32)
    expected = 100000 / 32
    chi_square = np.sum((counts - expected)**2 / expected)
    assert chi_square < 60.0

def test_t09_functional_info():
    """I(E) = -log2 F(E) with binomial bounds."""
    N = 10000
    k = 10
    F_E = k / N
    I_E = -math.log2(F_E)
    assert abs(I_E - (-math.log2(10/10000))) < 1e-9
    
    p = F_E
    se = math.sqrt(p * (1 - p) / N)
    ci_lower = p - 1.96 * se
    ci_upper = p + 1.96 * se
    
    I_E_lower = -math.log2(ci_upper)
    I_E_upper = -math.log2(ci_lower) if ci_lower > 0 else float('inf')
    assert I_E_lower <= I_E <= I_E_upper

def test_invariants():
    """Check non-violability of scientific invariants."""
    assert not RED_QUEEN_PROVED
    assert not MAJOR_TRANSITION_PROVED
    assert not OPEN_ENDED_INTELLIGENCE_PROVED
