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
    # Calculate the cumulative deviation from the mean
    cumulative_deviation = np.cumsum(data - np.mean(data))
    # Caclulate the range of the cumulative deviation
    R = np.max(cumulative_deviation) - np.min(cumulative_deviation)
    # Caclulate the standard deviation of the data
    S = np.std(data, ddof=1)
    if S == 0:
        return 0.5  # Random walk
    # Rescaled range
    rescaled_range = R / S
    # Caclculate the Hurst Exponent using the log of the rescaled range
    n = len(data)
    hurst_exponent = np.log(rescaled_range) / np.log(n)
    return hurst_exponent


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
    # Create lagged series (y_t) and current series (y_{t - 1})
    y_t = data[1:]
    y_t_minus_1 = data[:-1]
    # Reshape for sklearn
    y_t_minus_1 = y_t_minus_1.reshape(-1, 1)
    y_t = y_t.reshape(-1, 1)
    # Perform linear regression: y_t = alpha + beta * y_t_minus_1
    model = LinearRegression()
    model.fit(y_t_minus_1, y_t)
    # Get the slope (beta) of the regression
    beta = model.coef_[0][0]
    # Calculate the half-life
    if beta >= 1:
        # If beta >= 1, the series is not mean reverting
        return None
    else:
        half_life = -np.log(2) / np.log(beta)
        return half_life


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
    adf_result = adfuller(residual, maxlag=lag)
    # Extract relevant results
    adf_statistic = adf_result[0]
    p_value = adf_result[1]
    critical_values = adf_result[4]
    is_cointegrated = p_value < 0.05
    return {
        'adf_statistic': adf_statistic,
        'p_value': p_value,
        'critical_values': critical_values,
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
    eigenvalues = result.eig
    trace_statistics = result.lr1
    critical_values = result.cvt
    cointegration_rank = np.sum(result.lr1 > result.cvt[:, 1])
    # Return the results as a dictionary
    return {
        'eigenvalues': eigenvalues,
        'trace_statistics': trace_statistics,
        'critical_values': critical_values,
        'cointegration_rank': cointegration_rank
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
    # Convert the data to a numpy array
    data = np.array(data)
    # Calculate the simple moving average (SMA)
    middle_band = np.convolve(data, np.ones(window), mode='valid') / window
    # Calculate the rolling standard deviation
    rolling_std = np.sqrt(
        np.convolve(
            (data - np.convolve(data, np.ones(window), 'valid') / window)**2,
            np.ones(window), 'valid') / window
        )
    # Calculate the upper and lower bands
    upper_band = middle_band + (num_std * rolling_std)
    lower_band = middle_band - (num_std * rolling_std)
    # Pad the bands with NaNs to align with the original data
    pad_length = len(data) - len(middle_band)
    middle_band = np.pad(
        middle_band, (pad_length, 0), mode='constant', constant_values=np.nan
    )
    upper_band = np.pad(
        upper_band, (pad_length, 0), mode='constant', constant_values=np.nan
    )
    lower_band = np.pad(
        lower_band, (pad_length, 0), mode='constant', constant_values=np.nan
    )
    # Return the Bollinger Bands as a dictionary
    return {
        'middle_band': middle_band,
        'upper_band': upper_band,
        'lower_band': lower_band
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
    # Create and fit the linear regression model
    model = LinearRegression()
    model.fit(X, Y)
    # Extract the coefficients and intercept
    coefficients = model.coef_.tolist()
    intercept = model.intercept_
    return [intercept] + coefficients


def gather_close_data() -> None:
    pass


def gather_open_data() -> None:
    pass


def gather_high_data() -> None:
    pass


def gather_low_data() -> None:
    pass
