package helpers

import (
	"github.com/berkmancenter/adf"
)

/*
	will the Augmented-Dickey Fuller Test
	on a given set of data order by ascending time
	lag is normally set to 1, and pvalue can be 
	somewhere in the range of .05 (95% interval) to .2 (80% interval)
*/
func ExecADFTest(series []float64, pvalue float64, lag int) bool {
	adfTest := adf.New(series, pvalue, lag) // generates a new test 
	adfTest.Run() // runs the ADF test on the set of data
	return adfTest.IsStationary() // returns if the time series is stationary given the pvalue threshold
}

/*
	will calculate the Hurst exponent on 
	a given set of floating point data
*/
func CalcHurstExponent() {

}

/*
	will calculate the half life of mean reversion
	of a certian set of floating point data
*/
func CalcMeanReversionHalfLife() {

}