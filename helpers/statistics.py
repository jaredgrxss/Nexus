from statsmodels.tsa.stattools import adfuller
from statsmodels.tsa.vector_ar.vecm import coint_johansen
from sklearn.linear_model import LinearRegression
import numpy as np
import statsmodels.api as sm


def adf_test(data: list[float], lag: int = 1) -> tuple:
    """
    Execute the Augmented Dickey-Fuller test on the given data.

    Args:
        data (list[float]): The data to test.
        lag (int): The number of lags to use.

    Returns:
        a tuple containing the test statistic, p-value, number of lags used,
        number of observations used, and the critical values.
    """
    adf_result = adfuller(data, maxlag=lag)
    return adf_result


def hurst_exponent(data: list[float]) -> float:
    """
    Calculate the Hurst Exponent.
    An H < 0.5 indicates mean reversion,
    H = 0.5 indicates a random walk,
    and H > 0.5 indicates a trending series.

    Args:
        data (list[float]): A list of float values
                            representing the time series.

    Returns:
        float: The Hurst Exponent of the time series
    """
    # Convert the data to a numpy array
    data = np.array(data)
    max_window = len(data) // 4  # Use up to quarter-length windows
    min_window = 10
    lags = range(min_window, max_window+1)
    
    # Calculate R/S for different lags
    rs_values = []
    for lag in lags:
        n = len(data) // lag * lag
        subs = data[:n].reshape(-1, lag)
        # Calculate mean-adjusted series
        mean_adj = subs - np.mean(subs, axis=1, keepdims=True)
        # Cumulative deviation
        cum_dev = np.cumsum(mean_adj, axis=1)
        # Calculate ranges
        r = np.max(cum_dev, axis=1) - np.min(cum_dev, axis=1)
        s = np.std(subs, axis=1, ddof=1)
        s[s == 0] = 1  # Avoid division by zero
        rs = np.mean(r / s)
        rs_values.append(rs)
    
    # Fit to log-log scale
    x = np.log(lags)
    y = np.log(rs_values)
    slope = np.polyfit(x, y, 1)[0]
    return slope


def half_life(data: list[float]) -> float:
    """
    Calculate the half-life of a mean-reverting time series
    The half-life is the time it takes for the time series
    to revert halfway back to its mean after a deviation.
    It is calculated using the slope of the regression of the
    time series against its lagged values.

    Args:
        data (list[float]): A list of float values representing
                            the time series.

    Returns:
        float: The half-life of the mean-reverting time series.
                If the time series is not mean-reverting (slope >= 0),
                returns `None`.
    """
    # Convert the data to a numpy array
    data = np.array(data)
    y_t = data[1:]
    y_t_minus_1 = data[:-1]
    
    # Use statsmodels for proper OLS without automatic intercept
    X = sm.add_constant(y_t_minus_1)  # Include intercept explicitly
    model = sm.OLS(y_t, X).fit()
    beta = model.params[1]  # Coefficient for y_{t-1}
    
    if beta >= 1:
        return None
    return -np.log(2) / np.log(beta)


def cointegration_adf_test(
    X: list[float],
    Y: list[float],
    lag: int = 1
) -> dict:
    """
    Perform the Cointegration Augmented Dickey-Fuller (CADF)
    Test on two time series. This test checks whether two time series
    are cointegrated by:
    1. Fitting a linear regression model of Y on X.
    2. Calculating the residuals of the regression.
    3. Performing an Augmented Dickey-Fuller (ADF) test on the residuals.

    Args:
        X (list[float]): The first time series.
        Y (list[float]): The second time series.
        lag (int, optional): The number of lags to include
        in the ADF test. Defaults to 1.

    Returns:
        dict: A dictionary containing the ADF test results, including:
        - 'adf_statistic': The ADF test statistic.
        - 'p_value': The p-value of the ADF test.
        - 'critical_values': Critical values for
                            the ADF test at 1%, 5%, and 10%.
        - 'is_cointegrated': A boolean indicating whether
                            the series are cointegrated
                            (True if p-value < 0.05, False otherwise).
    """
    # Convert the data to numpy arrays
    X = np.array(X)
    Y = np.array(Y)
    if len(X) != len(Y):
        raise ValueError('X and Y must have the same length.')
    # Step 1: Fit a linear regression model of Y on X
    X = sm.add_constant(X)
    model = sm.OLS(Y, X).fit()
    # Step 2: Calculate the residuals
    residual = model.resid
    # Step 3: Perform the ADF test on the residuals
    adf_result = adfuller(residual, maxlag=lag, regression='c')
    critical_value = adf_result[4]['5%']
    is_cointegrated = adf_result[0] < critical_value  # Proper Engle-Granger decision
    return {
        'adf_statistic': adf_result[0],
        'critical_value_5%': critical_value,
        'is_cointegrated': is_cointegrated
    }


def johansen_test(
    data: list[list[float]],
    det_order: int = - 1,
    k_ar_diff: int = 1
) -> dict:
    """
    Perform the Johansen Test for cointegration on multiple time series.
    The Johansen Test determines the number of
    cointegrating relationships among a set of time series.
    It is based on the maximum likelihood estimation of a Vector Error
    Correction Model (VECM).

    Args:
        data (list[list[float]]): A list of time series,
        where each time series is a list of floats.
        det_order (int, optional): The order of the deterministic trend to
        include in the test.
            -1: No deterministic trend.
            0: Constant term only.
            1: Constant and linear trend.
            Defaults to -1.
        k_ar_diff (int, optional): The number of lags in the VAR model.
                                    Defaults to 1.

    Returns:
        dict: A dictionary containing the Johansen Test results, including:
        - 'eigenvalues': The eigenvalues used in the test.
        - 'trace_statistics': The trace statistics for each hypothesis.
        - 'critical_values': The critical values for the trace statistics at
                            90%, 95%, and 99%.
        - 'cointegration_rank': The estimated number of
                                cointegrating relationships.
    """
    # Convert the input data to a numpy array and transpose
    data = np.array(data).T
    # Perform the Johansen Test
    result = coint_johansen(data, det_order, k_ar_diff)
    # Extract the relevant results
    trace_statistics = result.lr1
    critical_values = result.cvt
    coint_rank = 0
    for i in range(len(trace_statistics)):
        if trace_statistics[i] > critical_values[i, 1]:  # Compare to 95% critical value
            coint_rank += 1
        else:
            break
    return {
        'trace_statistics': trace_statistics,
        'critical_values': critical_values,
        'cointegration_rank': coint_rank
    }


def bollinger_bands(
    data: list[float],
    window: int,
    num_std: float = 2
) -> dict:
    """
    Calculate the Bollinger Bands for a time series.
    Bollinger Bands consist of:
    - Middle Band: Simple Moving Average (SMA) of the time series.
    - Upper Band: SMA + (num_std * standard dev of the time series).
    - Lower Band: SMA - (num_std * standard dev of the time series).

    Args:
        data (list[float]):
            A list of float values representing the time series.
        window (int):
            The window size for the moving average and standard dev.
        num_std (float, optional):
            The number of standard dev to use for the bands.
            Defaults to 2.

    Returns:
        dict: A dictionary containing the Bollinger Bands:
              - 'middle_band': The middle band (SMA).
              - 'upper_band': The upper band.
              - 'lower_band': The lower band.
    """
    data = np.array(data)
    if len(data) < window:
        raise ValueError("Window size larger than data length")
    
    # Use proper rolling calculations
    middle_band = np.convolve(data, np.ones(window)/window, mode='valid')
    std_dev = np.array([np.std(data[i-window:i], ddof=1) 
                       for i in range(window, len(data)+1)])
    
    upper_band = middle_band + (num_std * std_dev)
    lower_band = middle_band - (num_std * std_dev)
    
    # Pad with NaNs for alignment
    pad = window - 1
    return {
        'middle_band': np.pad(middle_band, (pad, 0), constant_values=np.nan),
        'upper_band': np.pad(upper_band, (pad, 0), constant_values=np.nan),
        'lower_band': np.pad(lower_band, (pad, 0), constant_values=np.nan)
    }


def mean(data: list[float]) -> float:
    """
    Calculate the mean (average) of a list of numbers.

    Args:
        data (list[float]): A list of numerical values.

    Returns:
        float: The mean of the input data.
    """
    return sum(data) / len(data)


def variance(data: list[float]) -> float:
    """
    Calculate the variance of a list of numbers.
    Variance measures the spread of the data points around the mean.

    Args:
        data (list[float]): A list of numerical values.

    Returns:
        float: The variance of the input data.
    """
    mean_value = mean(data)
    return sum((x - mean_value) ** 2 for x in data) / len(data)


def standard_deviation(data: list[float]) -> float:
    """
    Calculate the standard deviation of a list of numbers.
    Standard deviation measures the amount of
    variation or dispersion in the data.

    Args:
        data (list[float]): A list of numerical values.

    Returns:
        float: The standard deviation of the input data.
    """
    return variance(data) ** 0.5


def linear_regression(X: list[float], Y: list[float]) -> tuple[float, float]:
    """
    Perform simple linear regression to
    fit a line to the data using scikit-learn.
    The line is of the form: Y = a * X + b, where:
    - a is the slope.
    - b is the intercept.

    Args:
        X (list[float]): The independent variable (predictor).
        Y (list[float]): The dependent variable (response).

    Returns:
        Tuple[float, float]: A tuple containing
        the slope (a) and intercept (b) of the fitted line.
    """
    if len(X) != len(Y):
        raise ValueError("X and Y must have the same length.")
    # Reshape X to a 2D array (required by scikit-learn)
    X_reshaped = [[x] for x in X]
    # Create and fit the linear regression model
    model = LinearRegression()
    model.fit(X_reshaped, Y)
    # Extract the slope (coefficient) and intercept
    a = model.coef_[0]
    b = model.intercept_
    return a, b


def multiple_regression(X: list[list[float]], Y: list[float]) -> list[float]:
    """
    Perform multiple linear regression to fit a hyperplane
    to the data using scikit-learn. The model is of the form:
    Y = b0 + b1*X1 + b2*X2 + ... + bn*Xn, where:
    - b0 is the intercept.
    - b1, b2, ..., bn are the coefficients for the independent variables.

    Args:
        X (list[list[float]]): A list of lists,
        where each inner list represents an independent variable.
        Y (list[float]): The dependent variable (response).

    Returns:
        list[float]: A list containing the intercept
        (b0) and coefficients (b1, b2, ..., bn).
    """
    if len(X) != len(Y):
        raise ValueError("X and Y must have the same length.")
    # Transpose to get (n_samples, n_features)
    X_array = np.array(X).T
    model = LinearRegression().fit(X_array, Y)
    return [model.intercept_] + model.coef_.tolist()


def gather_close_data() -> None:
    pass


def gather_open_data() -> None:
    pass


def gather_high_data() -> None:
    pass


def gather_low_data() -> None:
    pass
