package helpers

import (
	"github.com/berkmancenter/adf"
)

/*
	will run the Augmented-Dickey Fuller Test
	on a given set of data ordered by ascending time.
	Lag is normally set to 1, and pvalue can be 
	somewhere in the range of .05 (95% interval) to .2 (80% interval).
	In order for this to even be considered for MR, test statistic needs to be negative.
*/
func ExecADFTest(series []float64, pvalue float64, lag int) (bool, float64) {
	adfTest := adf.New(series, pvalue, lag) // generates a new test 
	adfTest.Run() // runs the ADF test on the set of data
	return adfTest.IsStationary(), adfTest.Statistic // returns if the time series is stationary & the test statistic
}

/*
	will calculate the Hurst exponent on 
	a given set of floating point data.
*/
func CalcHurstExponent() {

}

/*
	will calculate the half life of mean reversion
	of a certian set of floating point data.
*/
func CalcMeanReversionHalfLife() {

}

/*
	given a certian set of time series data
	calculate the mean of this data set.
*/
func CalcMean() {

}

/*
	given a certian set of time series data
	calculate the variance of this data set.
*/
func CalcVariance() {

}

/*
	given a certian set of time series data
	calculate the standard deviation of this data set.
*/
func CalcStandardDeviation() {

}