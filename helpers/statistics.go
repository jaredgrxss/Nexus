package helpers

import (
	"errors"
	"math"
	"time"
	"github.com/berkmancenter/adf"
	"gonum.org/v1/gonum/mat"
	"gonum.org/v1/gonum/stat"
	"github.com/alpacahq/alpaca-trade-api-go/v3/marketdata"
)

/*
	will run the Augmented-Dickey Fuller Test
	on a given set of data ordered by ascending time.
	Lag is normally set to 1, and pvalue can be
	somewhere in the range of .05 (95% interval) to .2 (80% interval).
	In order for this to even be considered for MR, test statistic needs to be negative than the
	pre-determined critical value at that particular p-value threshold
*/
func ExecADFTest(series []float64, lag int) (IsStationary bool, testStatistic float64) {
	adfTest := adf.New(series, 0, lag) // generates a new test, make this negative sense ADF test statistic is negative
	adfTest.Run() // runs the ADF test on the set of data
	return adfTest.IsStationary(), adfTest.Statistic // returns if the time series is stationary & the test statistic
}

/*
	will calculate the Hurst exponent on 
	a given set of floating point data.
*/
func CalcHurstExponent(series []float64) (HurstExponent float64, Error error) {
	if len(series) < 2 {
		return 0, errors.New("the length of the series must be at least 2")
	}
	var logRS, logN []float64
	// loop through subset sizes
	for n := 2; n <= len(series) / 2; n++ {
		var rsValues []float64 
		for i := 0; i + n <= len(series); i += n {
			subset := series[i:i+n]
			// mean and std
			mean := stat.Mean(subset, nil)
			stdDev := stat.StdDev(subset, nil)
			// center data 
			deviations := make([]float64, len(subset))
			for j, v := range subset {
				deviations[j] = v - mean
			}
			// sum data
			cumulativeSum := make([]float64, len(deviations))
			cumulativeSum[0] = deviations[0]
			for j := 1; j < len(deviations); j++ {
				cumulativeSum[j] = cumulativeSum[j - 1] + deviations[j]
			}
			// range
			r := rangeOf(cumulativeSum)
			if stdDev > 0 {
				rsValues = append(rsValues, r / stdDev)
			}
		}
		if len(rsValues) > 0 {
			logRS = append(logRS, math.Log(stat.Mean(rsValues, nil)))
			logN = append(logN, math.Log(float64(n)))
		}
	}
	// linear regress data and return the calculate slope
	slope, _ := stat.LinearRegression(logN, logRS, nil, false)
	return slope, nil
}

/*
	will calculate the half life of mean reversion
	of a certian set of floating point data.
*/
func CalcMeanReversionHalfLife(series []float64) (halfLife float64, Error error) {
	if len(series) < 2 {
		return 0, errors.New("the length of the series must be at least 2")
	}
	// prepare the lagged time series
	x := series[:len(series)-1] // X(t - 1)
	y := series[1:] // X(t)
	changes := make([]float64, len(y))
	for i := 0; i < len(y); i++ {
		changes[i] = y[i] - x[i]
	}

	// perform a linear regression y = alpha + beta * x
	_, beta := stat.LinearRegression(x, changes, nil, false)

	// ensure theta is within a reasonable range
	if beta >= 0 {
		return 0, errors.New("series does not exhibit mean reversion (theta >= 0)")
	}
	// use the log of the linear regressed equation to find half life
	theta := -beta
	halfLife = math.Log(2) / theta
	return halfLife, nil
}

/*
	The cointegrated augmented dickey-fuller test
	is used in statitistics to determine if a combination 
	of two individual series is cointegrated, making them 
	stationary when looked at together. This test is only 
	suitable for 2 series, if you want to look to more, 
	use the Johansen test.

	Technical details:
		The main idea is that we can run a linear regression on 
		the two price series to find our hedging portfolio and 
		then run an ADF test on this new portfolio to determine if
		it will be stationary, ETF pairs are a good ground for
		this type of trading 
	
	Miscellaneous:
		Order matters in this test, i.e if switch the independent and dependent 
		variables, you have the possibility of getting (or not getting) a cointegrated 
		series. This is due to the fact that your hedge ratio (beta) will differ. It is
		best to try both of the pairs you are looking at as the independent and dependent
		variables
		
*/
func ExecCointegratedADFTest(seriesX, seriesY []float64, lag int) (isCointegrated bool, testStatistic float64, ratio float64, residuals []float64) {
	// first run, linear regression on the two data sets
	alpha, beta := SimpleLinearRegression(seriesX, seriesY)
	// calculate the residuals off of this regression
	residuals = make([]float64, len(seriesX))
	for i := 0; i < len(seriesX); i++ {
		residuals[i] = seriesY[i] - (alpha + beta*seriesX[i])
	}
	// run a ADF test on the residuals 
	isCointegrated, testStatistic = ExecADFTest(residuals, lag)
	return isCointegrated, testStatistic, beta, residuals
}

/*
	The johansen test is used in statistics to determine 
	if a combination of two individual series is cointegrated, 
	making them stationary when looked at together. This test 
	is suitable for multiple series (n >= 2).
*/
func ExecJohansenTest(series [][]float64, lag int) (isCointegrated bool, testStatistic float64, Error error) {
    if len(series) == 0 || len(series[0]) == 0 {
		return false, 0, errors.New("time series cannot be empty")
	}
	nRows, nCols := len(series), len(series[0])
	if lag <= 0 || lag >= nRows {
		return false, 0, errors.New("lag must be greater than 0 and less than the number of rows")
	}

	// Create lagged and differenced series 
	lagged := make([][]float64, nRows - lag)
	differenced := make([][]float64, nRows - 1)

	for i := lag; i < nRows; i++ {
		laggedRow := make([]float64, nCols)
		copy(laggedRow, series[i - lag])
		lagged[i - lag] = laggedRow
	}

	for i := 1; i < nRows; i++ {
		diffRow := make([]float64, nCols)
		for j := 0; j < nCols; j++ {
			diffRow[j] = series[i][j] - series[i - 1][j]
		}
		differenced[i - 1] = diffRow
	}

	// convert differenced and lagged series to matrices
	laggedMat := mat.NewDense(len(lagged), nCols, flatten2DArray(lagged))
	differencedMat := mat.NewDense(len(differenced), nCols, flatten2DArray(differenced))

	// compute residuals using oridinary least squares regression
	var qr mat.QR 
	qr.Factorize(laggedMat)
	var residuals mat.Dense
	err := qr.SolveTo(&residuals, false, differencedMat)
	if err != nil {
		return false, 0, err
	}

	// compute the covariance matrix of the residuals
	covResiduals := computeCovarianceMatrix(&residuals)

	// perform eigenvalue decomposition of the covariance matrix
	var eig mat.EigenSym 
	if !eig.Factorize(covResiduals, true) {
		return false, 0, errors.New("eigenvalue decomposition failed")
	}

	eigenvalues := eig.Values(nil)

	// calculate the trace statistic
	traceStat := 0.0
	for _, eig := range eigenvalues {
		if eig > 0 {
			traceStat += math.Log(1 - eig)
		}
	}
	traceStat = -traceStat

	// compare trace statistic to critical values
	criticalValue := 15.41 // 95% confidence interval
	isCointegrated = traceStat > criticalValue
	return isCointegrated, traceStat, nil
}

/*
	given a certian set of time series data
	calculate the bollinger bands for this data set.
	using a window of 20 is a good starting point.
	or based on the mean reversion half life of the data set.
*/
func CaclulateBollingerBands(series []float64, window int) (upperBand, lowerBand []float64, Error error) {
	if len(series)	< window {
		return nil, nil, errors.New("the length of the series must be at least the window size")
	}
	upperBand = make([]float64, len(series))
	lowerBand = make([]float64, len(series))
	for i := window; i < len(series); i++ {
		subset := series[i - window:i]
		mean := stat.Mean(subset, nil)
		stdDev := stat.StdDev(subset, nil)
		upperBand[i] = mean + 2 * stdDev
		lowerBand[i] = mean - 2 * stdDev
	}
	return upperBand, lowerBand, nil
}

/*
	given a certian set of time series data
	calculate the mean of this data set.
*/
func CalcMean(series []float64) float64 {
	return stat.Mean(series, nil)
}

/*
	given a certian set of time series data
	calculate the variance of this data set.
*/
func CalcVariance(series []float64) float64 {
	return stat.Variance(series, nil)
}

/*
	given a certian set of time series data
	calculate the standard deviation of this data set.
*/
func CalcStandardDeviation(series []float64) float64 {
	return stat.StdDev(series, nil)
}

/*
	run a regression between one indepedent variable 
	and one dependent variable
*/
func SimpleLinearRegression(x, y []float64) (alpha float64, beta float64) {
	return stat.LinearRegression(x, y, nil, false)
}

/*
	will run a multiple linear regression on multiple 
	independent time series against a singular dependent time 
	series, useful for various strategies, will return alpha and beta
*/
func MultipleLinearRegression(seriesY []float64, seriesX ...[]float64) (float64, float64) {
	return 0.0, 0.0
}

/* 
	helper to normalize series for bar data to ensure thorough matching of data between time stamps for two time series
*/
func NormalizeBarData(seriesX, seriesY []marketdata.Bar) (seriesA, seriesB []marketdata.Bar) {
	// quick lookup of timestamps
	seriesYMap := make(map[time.Time]marketdata.Bar)
	for _, bar := range seriesY {
		seriesYMap[bar.Timestamp] = bar
	}

	// loop through seriesX and match with seriesY
	for _, bar := range seriesX {
		if val, exist := seriesYMap[bar.Timestamp]; exist {
			seriesA = append(seriesA, bar)
			seriesB = append(seriesB, val)
		}
	}
	return seriesA, seriesB
}

/*
	helper to gather close data from a series of bars
*/
func GatherCloseData(series []marketdata.Bar) (closeData []float64) {
	for _, bar := range series {
		closeData = append(closeData, bar.Close)
	}
	return closeData
}

/*
	helper to gather open data from a series of bars
*/
func GatherOpenData(series []marketdata.Bar) (openData []float64) {
	for _, bar := range series {
		openData = append(openData, bar.Open)
	}
	return openData
}

/*
	helper to gather open data from a series of bars
*/
func GatherHighData(series []marketdata.Bar) (highData []float64) {
	for _, bar := range series {
		highData = append(highData, bar.High)
	}
	return highData
}

/*
	helper to gather open data from a series of bars
*/
func GatherLowData(series []marketdata.Bar) (lowData []float64) {
	for _, bar := range series {
		lowData = append(lowData, bar.Low)
	}
	return lowData
}

// helper function for finding range of a data set
func rangeOf(series []float64) (dataRange float64) {
	min, max := series[0], series[0]
	for _, v := range series {
		min = math.Min(min, v)
		max = math.Max(max, v)
	}
	return max - min
}

// helper function for flattening a 2D array
func flatten2DArray(data [][]float64) (flattenedArray []float64) {
	flat := make([]float64, 0)
	for _, row := range data {
		flat = append(flat, row...)
	}
	return flat
}

// helper function for computing the covariance matrix
func computeCovarianceMatrix(residuals *mat.Dense) *mat.SymDense {
	nRows, nCols := residuals.Dims()
	covMat := mat.NewSymDense(nCols, nil)
	// calculate covaraicne for each pair of variables
	for i := 0; i < nCols; i++ {
		for j := i; j < nCols; j++ {
			cov := 0.0
			for r := 0; r < nRows; r++ {
				cov += residuals.At(r, i) * residuals.At(r, j)
			}
			covMat.SetSym(i, j, cov / float64(nRows - 1))
			covMat.SetSym(j, i, cov / float64(nRows - 1))
		}
	}
	return covMat
}