package helpers

import (
	"math"
	"github.com/berkmancenter/adf"
	"gonum.org/v1/gonum/stat"
)

/*
	will run the Augmented-Dickey Fuller Test
	on a given set of data ordered by ascending time.
	Lag is normally set to 1, and pvalue can be
	somewhere in the range of .05 (95% interval) to .2 (80% interval).
	In order for this to even be considered for MR, test statistic needs to be negative than the
	pre-determined critical value at that particular p-value threshold
*/
func ExecADFTest(series []float64, lag int) (bool, float64) {
	adfTest := adf.New(series, 0, lag) // generates a new test, make this negative sense ADF test statistic is negative
	adfTest.Run() // runs the ADF test on the set of data
	return adfTest.IsStationary(), adfTest.Statistic // returns if the time series is stationary & the test statistic
}

/*
	will calculate the Hurst exponent on 
	a given set of floating point data.
*/
func CalcHurstExponent(series []float64) float64 {
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
	return slope
}

/*
	will calculate the half life of mean reversion
	of a certian set of floating point data.
*/
func CalcMeanReversionHalfLife(series []float64) (float64, error) {

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

// helper function for finding range of a data set
func rangeOf(series []float64) float64 {
	min, max := series[0], series[0]
	for _, v := range series {
		min = math.Min(min, v)
		max = math.Max(max, v)
	}
	return max - min
}