package helpers

import (
	"log"
	"os"
	"time"
	"github.com/alpacahq/alpaca-trade-api-go/v3/alpaca"
	// "github.com/alpacahq/alpaca-trade-api-go/v3/marketdata"
)

// reusuable client to handle market operations
var tradeClient *alpaca.Client

// create a new trading client that will be used throughout the specific service
func createOrReturnTradeClient() {
	if tradeClient == nil {
		tradeClient = alpaca.NewClient(alpaca.ClientOpts{
			APIKey: os.Getenv("BROKER_PAPER_API_KEY"),
			APISecret: os.Getenv("BROKER_PAPER_SECRET_KEY"),
			BaseURL: os.Getenv("PAPER_URL"),
		})
	}
}

// check if market has opened for the day or not
func IsMarketOpen() (bool, error) {
	// make sure we have an active broker connection
	createOrReturnTradeClient()
	clock, err := tradeClient.GetClock()
	if err != nil {
		return false, err
	}
	if clock.IsOpen {
		return true, nil
	}
	timeToMarketOpen := int(clock.NextOpen.Sub(clock.Timestamp).Minutes())
	log.Printf("%d minutes until next market open\n", timeToMarketOpen)
	return false, nil 
}

// gather how many minutes till market close
func MinutesTillMarketClose() (time.Duration, error) {
	// make sure we have an active broker connection
	createOrReturnTradeClient()
	clock, err := tradeClient.GetClock()
	if err != nil {
		return -1, err
	}
	return clock.NextClose.Sub(clock.Timestamp), nil
}

/* 
	will execute a market order to be filled 
	at best possible price available immediately
*/
func ExecMarketOrder() {

}

/* 
	will execute a market order to be filled 
	if and only if price is <= specified price
*/
func ExecLimitOrder() {

}

/*
	will gather historical bar data 
	for a given inputed time frame
*/
func GetHistoricalBarData() {

}

/*
	will gather historical quote data 
	for a given inputed time frame
*/
func GetHistoricalQuoteData() {

}

/*
	will gather historical trade data 
	for a given inputed time frame
*/
func GetHistoricalTradeData() {

}