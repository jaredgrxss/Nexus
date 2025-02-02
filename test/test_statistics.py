import pytest
import numpy as np
from nexus.helpers import statistics


# Test fixtures for common data patterns
@pytest.fixture
def random_walk():
    np.random.seed(42)
    # Zero-mean increments, longer series
    return np.cumsum(np.random.normal(0, 1, 10_000))


@pytest.fixture
def stationary_series():
    # Strongly mean-reverting AR(1) process
    np.random.seed(42)
    # White noise (strongest mean reversion)
    return np.random.normal(0, 1, 5000)  # Pure noise: H ≈ 0


@pytest.fixture
def trending_series():
    np.random.seed(42)
    # Cumulative sum with persistent noise (H > 0.5)
    return np.cumsum(np.random.normal(0.5, 1, 5000))  # Drift + noise


# Test basic statistical functions
def test_mean():
    assert statistics.mean([1, 2, 3, 4, 5]) == 3.0
    assert statistics.mean([10]) == 10.0
    assert np.isclose(statistics.mean([1.5, 2.5, 3.5]), 2.5)


def test_variance():
    assert statistics.variance([1, 2, 3, 4, 5]) == 2.0
    assert statistics.variance([5]) == 0.0


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


def test_half_life():
    # 1. Test mean-reverting series with proper noise
    np.random.seed(42)
    n_points = 1000
    series = np.zeros(n_points)
    mean_reversion = 0.7  # True beta
    noise_std = 1.0  # Increased noise for better regression estimation

    for i in range(1, n_points):
        series[i] = mean_reversion * series[i-1] + np.random.normal(0, noise_std)

    hl = statistics.half_life(series)
    assert hl is not None

    theoretical_hl = -np.log(2) / np.log(mean_reversion)
    assert np.isclose(hl, theoretical_hl, rtol=0.15)

    # 2. Test random walk (non-mean-reverting) with longer series
    np.random.seed(42)
    non_reverting = np.cumsum(np.random.normal(0, 1, 1000))  # Longer series
    hl = statistics.half_life(non_reverting)

    # Expect very large half-life (practically infinite)
    assert hl is None or hl > 200


def test_cointegration_adf_test():
    # Create more obviously cointegrated pair
    np.random.seed(42)
    X = np.cumsum(np.random.normal(0, 1, 200))
    Y = 2*X + np.random.normal(0, 0.5, 200)  # Stronger relationship

    result = statistics.cointegration_adf_test(X, Y)
    assert result['is_cointegrated']

    # Create clearly non-cointegrated pair
    np.random.seed(42)
    X = np.cumsum(np.random.normal(0, 1, 200))
    Y = np.cumsum(np.random.normal(0, 1, 200))
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
    std_dev = np.std([1, 2, 3], ddof=1)
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
    np.random.seed(42)  # Fixed seed for reproducibility

    # Generate non-collinear features
    X1 = np.arange(1, 101)
    X2 = X1 * 2 + np.random.normal(0, 0.5, 100)  # Add noise to break collinearity

    X = np.column_stack((X1, X2))
    Y = 2*X1 + 3*X2 + 1 + np.random.normal(0, 0.1, 100)

    coefficients = statistics.multiple_regression(X.tolist(), Y.tolist())

    # Check coefficients with tighter tolerance
    assert np.isclose(coefficients[0], 1, atol=0.1), f"Intercept: {coefficients[0]}"
    assert np.isclose(coefficients[1], 2, atol=0.1), f"X1 coefficient: {coefficients[1]}"
    assert np.isclose(coefficients[2], 3, atol=0.1), f"X2 coefficient: {coefficients[2]}"


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
