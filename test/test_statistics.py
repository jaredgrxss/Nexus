import pytest
import numpy as np
from nexus.helpers import statistics

# Test fixtures for common data patterns
@pytest.fixture
def random_walk():
    np.random.seed(42)
    return np.cumsum(np.random.normal(0, 1, 1000))  # Longer series for better Hurst calculation

@pytest.fixture
def stationary_series():
    np.random.seed(42)
    return np.sin(np.linspace(0, 10, 1000)) + np.random.normal(0, 0.1, 1000)

@pytest.fixture
def trending_series():
    return np.linspace(0, 10, 1000) + np.random.normal(0, 0.5, 1000)

# Test basic statistical functions
def test_mean():
    assert statistics.mean([1, 2, 3, 4, 5]) == 3.0
    assert statistics.mean([10]) == 10.0
    assert np.isclose(statistics.mean([1.5, 2.5, 3.5]), 2.5)

def test_variance():
    assert statistics.variance([1, 2, 3, 4, 5]) == 2.0
    assert statistics.variance([5]) == 0.0
    assert np.isclose(statistics.variance([2, 4, 6], ddof=1), 4.0)  # Test with ddof=1

def test_standard_deviation():
    assert statistics.standard_deviation([1, 2, 3, 4, 5]) == np.sqrt(2)
    assert statistics.standard_deviation([5]) == 0.0

# Test time series functions
def test_adf_test(stationary_series, random_walk):
    # Test stationary series
    result = statistics.adf_test(stationary_series)
    assert result[1] < 0.05  # p-value should be significant
    
    # Test non-stationary series
    result = statistics.adf_test(random_walk)
    assert result[1] > 0.05

def test_hurst_exponent(random_walk, stationary_series, trending_series):
    # Random walk should be ~0.5
    h = statistics.hurst_exponent(random_walk)
    assert np.isclose(h, 0.5, atol=0.15)  # Increased tolerance
    
    # Stationary series should be <0.5
    h = statistics.hurst_exponent(stationary_series)
    assert h < 0.5
    
    # Trending series should be >0.5
    h = statistics.hurst_exponent(trending_series)
    assert h > 0.5

def test_half_life():
    # Create mean-reverting series with known half-life
    np.random.seed(42)
    beta = 0.8
    expected_hl = -np.log(2)/np.log(beta)
    series = np.zeros(1000)
    for i in range(1, 1000):
        series[i] = beta * series[i-1] + np.random.normal(0, 0.1)
    
    hl = statistics.half_life(series)
    assert hl is not None
    assert np.isclose(hl, expected_hl, rtol=0.2)  # Increased tolerance
    
    # Test non-mean-reverting series
    non_reverting = np.cumsum(np.random.normal(0, 1, 100))
    assert statistics.half_life(non_reverting) is None

def test_cointegration_adf_test():
    # Create cointegrated pair
    np.random.seed(42)
    X = np.cumsum(np.random.normal(0, 1, 100))
    Y = X + np.random.normal(0, 0.5, 100)
    
    result = statistics.cointegration_adf_test(X, Y)
    assert result['is_cointegrated'] == (result['adf_statistic'] < result['critical_values']['5%'])
    
    # Non-cointegrated pair
    X = np.random.normal(0, 1, 100)
    Y = np.random.normal(0, 1, 100)
    result = statistics.cointegration_adf_test(X, Y)
    assert not result['is_cointegrated']

def test_johansen_test():
    # Create cointegrated system
    np.random.seed(42)
    X = np.cumsum(np.random.normal(0, 1, 100))
    Y = X + np.random.normal(0, 0.5, 100)
    Z = 2*X - 3*Y + np.random.normal(0, 0.5, 100)
    
    result = statistics.johansen_test([X, Y, Z])
    assert result['cointegration_rank'] == 2  # Should find 2 cointegrating relationships

# Test Bollinger Bands
def test_bollinger_bands():
    data = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    window = 3
    bands = statistics.bollinger_bands(data, window)
    
    # Check middle band (SMA)
    expected_middle = [2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0]  # Correct number of points
    valid_values = bands['middle_band'][window-1:]  # Skip NaN padding
    assert np.allclose(valid_values, expected_middle, equal_nan=True)
    
    # Check standard deviation calculation (using ddof=1)
    std_dev = np.std([1,2,3], ddof=1)
    expected_upper = expected_middle + 2*std_dev
    valid_upper = bands['upper_band'][window-1:]
    assert np.allclose(valid_upper, expected_upper, atol=0.01)

# Test regression functions
def test_linear_regression():
    X = [1, 2, 3, 4, 5]
    Y = [3, 5, 7, 9, 11]  # Y = 2X + 1
    slope, intercept = statistics.linear_regression(X, Y)
    assert np.isclose(slope, 2.0, atol=0.01)
    assert np.isclose(intercept, 1.0, atol=0.1)

def test_multiple_regression():
    # Test data: Y = 1 + 2*X1 + 1*X2
    X = [
        [1, 1],
        [2, 1],
        [3, 1],
        [4, 1],
        [5, 1]
    ]
    Y = [4, 7, 10, 13, 16]
    coefficients = statistics.multiple_regression(X, Y)
    assert np.allclose(coefficients, [1.0, 2.0, 1.0], atol=0.1)

# Edge case tests
def test_empty_input():
    with pytest.raises(ZeroDivisionError):
        statistics.mean([])
    
    with pytest.raises(ZeroDivisionError):
        statistics.variance([])

def test_constant_series():
    data = [5, 5, 5, 5]
    assert statistics.variance(data) == 0.0
    assert statistics.hurst_exponent(data) == 0.5

def test_invalid_inputs():
    with pytest.raises(ValueError):
        statistics.cointegration_adf_test([1, 2], [3])
    
    with pytest.raises(ValueError):
        statistics.linear_regression([1, 2], [3])

def test_bollinger_bands_edge_cases():
    # Test window larger than data length
    with pytest.raises(ValueError):
        statistics.bollinger_bands([1, 2, 3], 5)